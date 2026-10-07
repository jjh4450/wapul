// Per-unit AST facts and the SEGMENT pair rules: a copy of wapul-ml's
// wapul_ml/features/unit_ast.py, the original. Change both together and rerun the parity check.

import { type Node, type Tree } from 'web-tree-sitter';

import {
  BARE_EXPRESSION_LANGUAGES,
  type Category,
  CATEGORY_BY_TYPE,
  CONTAINERS,
  CONTROL,
  DEFS,
  IDENTIFIER_TYPES,
  type Language,
  LOOPS,
  TARGET_LISTS
} from './languages.ts';
import { type Unit } from './units.ts';

export interface UnitAst {
  category: Category;
  nodeType: string;
  /** Header of a compound statement whose body holds other units. */
  isHeader: boolean;
  /** Enclosing loops and branches. */
  depth: number;
  /** Every identifier in the unit. */
  reads: Set<string>;
  /** Identifiers assigned, declared, read into, or incremented. */
  writes: Set<string>;
  /** Owner node indices: for a header, the whole compound statement. */
  span: [number, number];
  /** Start index of the innermost enclosing loop, -1 if none. */
  loop: number;
  /** Start index of the innermost enclosing loop or branch, -1 if none. */
  control: number;
  /** Start index of the enclosing definition, -1 if none. */
  function: number;
  /** Start index of the parent node: siblings share it. */
  parent: number;
}

function outside(node: Node, start: number, end: number): boolean {
  return node.endIndex <= start || node.startIndex >= end;
}

function identifiers(node: Node, start: number, end: number, out: Set<string>): void {
  if (outside(node, start, end)) {
    return;
  }

  if (IDENTIFIER_TYPES.has(node.type)) {
    out.add(node.text);

    return;
  }

  for (const child of node.children) {
    identifiers(child, start, end, out);
  }
}

/** `a`, `a[i]`, `a.b`, `*a` -> "a". */
function targetName(node: Node | null): string | null {
  while (node !== null && !IDENTIFIER_TYPES.has(node.type)) {
    node = node.namedChildren[0] ?? null;
  }

  return node === null ? null : node.text;
}

function childOfType(node: Node, ...types: string[]): Node | null {
  return node.namedChildren.find((c) => types.includes(c.type)) ?? null;
}

const INCREMENT = /^(\+\+|--)|(\+\+|--)$/;

const ASSIGN_OPERATOR = /^[+\-*/%&|^]=$|^<<=$|^>>=$/;

/** The node written by a statement or expression, per language: the first field that exists. */
function writeTarget(node: Node): Node | null {
  switch (node.type) {
    case 'assignment_expression':
    case 'assignment': // python, kotlin, ruby; swift uses `target`
    case 'augmented_assignment':
    case 'augmented_assignment_expression': // javascript, php
    case 'compound_assignment_expr':
    case 'operator_assignment': // ruby `+=`
    case 'assignment_statement': // go
    case 'short_var_declaration': // go `:=`
      return node.childForFieldName('left') ?? node.childForFieldName('target');
    case 'init_declarator':
    case 'variable_declarator':
    case 'var_spec': // go `var n int`
    case 'const_spec':
    case 'declaration_expression': // csharp `out var x`
      return node.childForFieldName('declarator') ?? node.childForFieldName('name');
    case 'update_expression':
    case 'inc_statement': // go
    case 'dec_statement':
      return node.childForFieldName('argument') ?? node.namedChildren[0] ?? null;
    case 'postfix_unary_expression': // csharp, kotlin `i++`
    case 'prefix_unary_expression':
      return INCREMENT.test(node.text) ? (node.namedChildren[0] ?? null) : null;
    case 'unary_expression': // kotlin `i++`; go `&n` in fmt.Fscan(reader, &n)
      if (INCREMENT.test(node.text)) {
        return node.namedChildren[0] ?? null;
      }

      return node.text.startsWith('&') ? node.childForFieldName('operand') : null;
    case 'for_range_loop':
      return node.childForFieldName('declarator');
    case 'let_declaration': // Rust `let x =`
    case 'for_expression': // Rust `for x in`
    case 'val_definition': // scala
    case 'var_definition':
    case 'for': // ruby
      return node.childForFieldName('pattern');
    case 'for_statement': // Python `for x in`; kotlin `for (x in ...)`; swift `for x in`
      return (
        node.childForFieldName('left') ??
        node.childForFieldName('item') ??
        childOfType(node, 'variable_declaration', 'multi_variable_declaration')
      );
    case 'for_in_statement': // javascript `for (const x of ...)`
    case 'foreach_statement': // csharp; php has no field: the last `$v` before the body
      return (
        node.childForFieldName('left') ??
        node.namedChildren.filter((c) => c.type === 'variable_name').at(-1) ??
        null
      );
    case 'range_clause': // go `for i, x := range ...`
      return node.childForFieldName('left');
    case 'property_declaration': // kotlin `val x =` (or `private val x`); swift `let x =`
      return (
        node.childForFieldName('name') ??
        childOfType(node, 'variable_declaration', 'multi_variable_declaration')
      );
    case 'enumerator': // scala `for (x <- ...)`
      return node.namedChildren[0] ?? null;
    case 'infix_expression': {
      // scala `sum += x`
      const operator = node.childForFieldName('operator');

      return operator !== null && ASSIGN_OPERATOR.test(operator.text)
        ? node.childForFieldName('left')
        : null;
    }

    case 'binary_expression': {
      // cin >> a >> b
      const operator = node.childForFieldName('operator');

      return operator !== null && operator.text === '>>' ? node.childForFieldName('right') : null;
    }

    case 'pointer_expression': // scanf("%d", &n)
      return node.text.startsWith('&') ? node.childForFieldName('argument') : null;
    default:
      return null;
  }
}

function writes(node: Node, start: number, end: number, out: Set<string>): void {
  if (outside(node, start, end)) {
    return;
  }

  const target = writeTarget(node);

  if (target !== null) {
    if (TARGET_LISTS.has(target.type)) {
      for (const part of target.namedChildren) {
        const name = targetName(part);

        if (name !== null) {
          out.add(name);
        }
      }
    } else {
      const name = targetName(target);

      if (name !== null) {
        out.add(name);
      }
    }
  }

  for (const child of node.children) {
    writes(child, start, end, out);
  }
}

/** AST facts for each unit of the tree. */
export function analyze(tree: Tree, units: Unit[], language: Language): UnitAst[] {
  const root = tree.rootNode;
  const bare = BARE_EXPRESSION_LANGUAGES.has(language);

  return units.map((unit) => {
    const { startIndex: s, endIndex: e } = unit;
    // The owner is the smallest node covering the unit, raised to a statement that starts
    // where the unit starts (a header's owner is its whole compound statement). Where
    // expressions are statements, the raise stops below the container, which may start at
    // the same index (Ruby's `body_statement` has no brace).
    let node = root.descendantForIndex(s, e) ?? root;

    while (
      !CATEGORY_BY_TYPE.has(node.type) &&
      node.parent !== null &&
      node.parent.startIndex === s &&
      !(bare && CONTAINERS.has(node.parent.type))
    ) {
      node = node.parent;
    }

    const reads = new Set<string>();
    const written = new Set<string>();
    identifiers(node, s, e, reads);
    writes(node, s, e, written);
    let depth = 0;
    let loop = -1;
    let control = -1;
    let fn = -1;

    for (let anc = node.parent; anc !== null; anc = anc.parent) {
      if (CONTROL.has(anc.type)) {
        depth += 1;

        if (control < 0) {
          control = anc.startIndex;
        }

        if (loop < 0 && LOOPS.has(anc.type)) {
          loop = anc.startIndex;
        }
      }

      if (fn < 0 && DEFS.has(anc.type)) {
        fn = anc.startIndex;
      }
    }

    return {
      category: CATEGORY_BY_TYPE.get(node.type) ?? 'other',
      nodeType: node.type,
      isHeader: node.endIndex > e,
      depth,
      reads,
      writes: written,
      span: [node.startIndex, node.endIndex],
      loop,
      control,
      function: fn,
      parent: node.parent === null ? -1 : node.parent.startIndex
    };
  });
}

function intersectionSize(a: Set<string>, b: Set<string>): number {
  let n = 0;

  for (const x of a) {
    if (b.has(x)) {
      n += 1;
    }
  }

  return n;
}

const flag = (v: boolean): number => (v ? 1 : 0);

/** The SEGMENT block rules for unit x before unit y: 11 values. */
export function segmentFeatures(x: UnitAst, y: UnitAst): number[] {
  const shared = intersectionSize(x.reads, y.reads);
  const union = x.reads.size + y.reads.size - shared;

  return [
    // data-flow chain
    flag(intersectionSize(x.writes, y.reads) > 0),
    flag(intersectionSize(y.writes, x.reads) > 0),
    flag(intersectionSize(x.writes, y.writes) > 0),
    shared / (union || 1),
    // control block
    flag(x.isHeader && x.span[0] <= y.span[0] && y.span[1] <= x.span[1]),
    flag(x.control === y.control),
    flag(x.loop === y.loop),
    flag(x.function === y.function),
    flag(x.parent === y.parent),
    // same syntactic category
    flag(x.category === y.category),
    flag(x.nodeType === y.nodeType)
  ];
}
