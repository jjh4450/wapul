// String features for the statement-kind classifier: a copy of wapul-ml's
// wapul_ml/features/kind_features.py (`unit_features`, `with_ngrams`), the original. Change
// both together and rerun the parity check.
//
// Tokens are prefixed by where they come from: `t:` the unit's tokens and token bigrams;
// `p1:`..`p3:` / `n1:`..`n3:` the neighbours' tokens; `b:` for a header, its body's tokens;
// `c:` the innermost enclosing loop or branch header, `f:` the enclosing function header.
// Identifier tokens also give `prefix#gram` for their character 3- and 4-grams.

import { type Node, type Tree } from 'web-tree-sitter';

import { type UnitAst } from './ast.ts';
import { type Language } from './languages.ts';
import { type Unit } from './units.ts';

/** A unit's features by name; a repeated name keeps its last value, as a Python dict does. */
export type Features = Map<string, number>;

// Python's `[A-Za-z_]\w*|\d+|\S` with its Unicode `\w` (letters, digits, underscore) and `\d`
// (decimal digits).
const TOKEN = /[A-Za-z_][\p{L}\p{N}_]*|\p{Nd}+|\S/gu;

const MAX_TOKENS = 64; // a long body says enough in its first tokens

const K = 3; // neighbours on each side

export function tokens(text: string): string[] {
  const out: string[] = [];

  for (const match of text.matchAll(TOKEN)) {
    if (out.length === MAX_TOKENS) {
      break;
    }

    const t = match[0];
    out.push(/^\p{Nd}+$/u.test(t) ? 'NUM' : t);
  }

  return out;
}

// String and character literals, outermost, across the supported grammars. Their contents
// differ from problem to problem, so tokens see `""` in their place (kind_features.py LITERALS).
export const LITERALS = new Set([
  'string_literal',
  'raw_string_literal',
  'char_literal',
  'character_literal',
  'multiline_string_literal',
  'string',
  'template_string',
  'interpreted_string_literal',
  'rune_literal',
  'interpolated_string_expression',
  'verbatim_string_literal',
  'line_string_literal',
  'multi_line_string_literal',
  'heredoc_body',
  'encapsed_string',
  'heredoc',
  'nowdoc'
]);

/** Index ranges of the outermost literals, in order. */
export function literalSpans(tree: Tree): [number, number][] {
  const out: [number, number][] = [];
  const stack: Node[] = [tree.rootNode];

  for (let node = stack.pop(); node !== undefined; node = stack.pop()) {
    // Named only: some grammars spell a type keyword like a literal (C#'s `string`)
    if (node.isNamed && LITERALS.has(node.type)) {
      out.push([node.startIndex, node.endIndex]);
    } else {
      for (const child of node.children) {
        stack.push(child);
      }
    }
  }

  return out.sort((a, b) => a[0] - b[0]);
}

/** `code.slice(start, end)` with each literal (or the part of it inside) replaced by `""`. */
function masked(code: string, start: number, end: number, literals: [number, number][]): string {
  let out = '';
  let at = start;

  for (const [s, e] of literals) {
    if (e <= start || s >= end) {
      continue;
    }

    out += code.slice(at, Math.max(s, start)) + '""';
    at = Math.min(e, end);
  }

  return out + code.slice(at, end);
}

export function unitFeatures(
  code: string,
  language: Language,
  units: Unit[],
  asts: UnitAst[],
  literals: [number, number][]
): Features[] {
  const headerAt = new Map<number, number>();
  asts.forEach((a, j) => {
    if (a.isHeader) {
      headerAt.set(a.span[0], j);
    }
  });
  const toks = units.map((u) => tokens(masked(code, u.startIndex, u.endIndex, literals)));
  const n = units.length;

  return units.map((u, j) => {
    const a = asts[j];
    const f: Features = new Map();
    f.set(`lang=${language}`, 1);
    f.set(`cat=${a.category}`, 1);
    f.set(`node=${a.nodeType}`, 1);
    f.set('header', a.isHeader ? 1 : 0);
    f.set('depth', Math.min(a.depth, 5) / 5);
    f.set('pos', j / Math.max(n - 1, 1));

    for (const t of new Set(toks[j])) {
      f.set(`t:${t}`, 1);
    }

    for (let i = 1; i < toks[j].length; i++) {
      f.set(`t:${toks[j][i - 1]} ${toks[j][i]}`, 1);
    }

    for (let k = 1; k <= K; k++) {
      for (const [side, i] of [
        ['p', j - k],
        ['n', j + k]
      ] as const) {
        if (i >= 0 && i < n) {
          for (const t of new Set(toks[i])) {
            f.set(`${side}${k}:${t}`, 1);
          }
        } else {
          f.set(`${side}${k}:EDGE`, 1);
        }
      }
    }

    if (a.isHeader) {
      for (const t of new Set(tokens(masked(code, u.endIndex, a.span[1], literals)))) {
        f.set(`b:${t}`, 1);
      }
    }

    for (const [prefix, at] of [
      ['c', a.control],
      ['f', a.function]
    ] as const) {
      const h = headerAt.get(at);

      if (at >= 0 && h !== undefined && h !== j) {
        for (const t of new Set(toks[h])) {
          f.set(`${prefix}:${t}`, 1);
        }
      }
    }

    const sameFn: number[] = [];

    for (let i = 0; i < n; i++) {
      if ((asts[i].function === a.function && !asts[i].isHeader) || i === j) {
        sameFn.push(i);
      }
    }

    f.set('fn_first', j === sameFn[0] ? 1 : 0);
    f.set('fn_last', j === sameFn[sameFn.length - 1] ? 1 : 0);
    f.set('in_function', a.function >= 0 ? 1 : 0);

    return f;
  });
}

const IDENT = /^[A-Za-z_][\p{L}\p{N}_]*$/u;

const NGRAMS = [3, 4];

export function charNgrams(token: string): Set<string> {
  const t = [...token.toLowerCase()];
  const out = new Set<string>();

  for (const n of NGRAMS) {
    for (let i = 0; i + n <= t.length; i++) {
      out.add(t.slice(i, i + n).join(''));
    }
  }

  return out;
}

/** Each identifier feature `prefix:tok` also gives `prefix#gram` for its character 3- and
 * 4-grams, so input/output idioms of an unseen language share pieces with known ones. */
export function withNgrams(feats: Features[]): Features[] {
  return feats.map((f) => {
    const g: Features = new Map(f);

    for (const name of f.keys()) {
      const sep = name.indexOf(':');

      if (sep < 0) {
        continue;
      }

      const prefix = name.slice(0, sep);
      const tok = name.slice(sep + 1);

      if (IDENT.test(tok)) {
        for (const c of charNgrams(tok)) {
          g.set(`${prefix}#${c}`, 1);
        }
      }
    }

    return g;
  });
}

/** The features of all units in the form the WASM `kinds` takes: one feature per line,
 * `name` for value 1 or `name<tab>value`, units separated by a blank line. */
export function featureText(feats: Features[]): string {
  return feats
    .map((f) =>
      [...f].map(([name, value]) => (value === 1 ? name : `${name}\t${value}`)).join('\n')
    )
    .join('\n\n');
}
