// Statement units: a copy of wapul-ml's wapul_ml/units.py, the original. Change both together
// and rerun the parity check.
//
// A unit is one simple statement, or the header of a compound one (`for (...)`, `if (...)`,
// `int main()`) whose body is split further. Braces, bare keywords (`else`, `try`, `do`) and
// comments belong to no unit.

import { type Node, type Tree } from 'web-tree-sitter';

import {
  BARE,
  BODY_FIELDS,
  BLOCK_BODIES,
  BODY_PAIRS,
  CASES,
  CLAUSES,
  CONTAINERS,
  EXPRESSION_BRANCHES,
  NESTED,
  RUST_CONTROL,
  SKIPPED,
  UNWRAP
} from './languages.ts';

/** (line, col): line from 1, col from 0 in characters (code points), end exclusive. */
export type Point = [number, number];

export interface Unit {
  start: Point;
  end: Point;
  text: string;
  /** The unit in the code, as web-tree-sitter indices. */
  startIndex: number;
  endIndex: number;
}

function isBody(parent: Node, i: number, child: Node): boolean {
  if (parent.type === 'struct_expression') {
    // Rust `Self { a, b }` is a value, not a body
    return false;
  }

  // Named only: keywords such as Ruby's `else` and `do` share their spelling with nodes
  if (child.isNamed && (CONTAINERS.has(child.type) || CLAUSES.has(child.type))) {
    return true;
  }

  const field = parent.fieldNameForChild(i);

  if (field !== null && BODY_FIELDS.has(field)) {
    return !EXPRESSION_BRANCHES.has(parent.type) || BLOCK_BODIES.has(child.type);
  }

  if (BODY_PAIRS.has(`${parent.type}>${child.type}`)) {
    return true;
  }

  return (
    CASES.has(parent.type) &&
    (child.type.endsWith('statement') || child.type.endsWith('declaration'))
  );
}

/** Split each statement of a container, looking through containers nested in it. */
function splitContainer(container: Node, out: [number, number][]): void {
  for (const stmt of container.namedChildren) {
    if (SKIPPED.has(stmt.type)) {
      continue;
    }

    if (NESTED.has(stmt.type)) {
      splitContainer(stmt, out);
    } else {
      split(stmt, out);
    }
  }
}

function split(node: Node, out: [number, number][]): void {
  const first = node.namedChildren[0];

  if (
    first !== undefined &&
    (UNWRAP.has(node.type) ||
      (node.type === 'expression_statement' && RUST_CONTROL.has(first.type)))
  ) {
    node = first;
  }

  const children = node.children;

  if (!children.some((c, i) => isBody(node, i, c))) {
    out.push([node.startIndex, node.endIndex]);

    return;
  }

  let header: Node[] = [];
  children.forEach((child, i) => {
    if (SKIPPED.has(child.type)) {
      return;
    }

    if (!isBody(node, i, child)) {
      header.push(child);

      return;
    }

    if (header.length > 0) {
      out.push([header[0].startIndex, header[header.length - 1].endIndex]);
      header = [];
    }

    if (CONTAINERS.has(child.type)) {
      splitContainer(child, out);
    } else {
      split(child, out);
    }
  });

  if (header.length > 0) {
    out.push([header[0].startIndex, header[header.length - 1].endIndex]);
  }
}

/** Python's `bytes.rstrip()`: ASCII whitespace only. */
const ASCII_SPACE = new Set([' ', '\t', '\n', '\r', '\v', '\f']);

function rstripEnd(code: string, start: number, end: number): number {
  while (end > start && ASCII_SPACE.has(code[end - 1])) {
    end -= 1;
  }

  return end;
}

export function units(tree: Tree, code: string): Unit[] {
  const spans: [number, number][] = [];

  splitContainer(tree.rootNode, spans);
  spans.sort((a, b) => a[0] - b[0] || a[1] - b[1]);

  const lineStarts = [0];

  for (let i = 0; i < code.length; i++) {
    if (code[i] === '\n') {
      lineStarts.push(i + 1);
    }
  }

  const point = (index: number): Point => {
    // The last line starting at or before the index
    let lo = 0;
    let hi = lineStarts.length;

    while (lo < hi) {
      const mid = (lo + hi) >> 1;

      if (lineStarts[mid] <= index) {
        lo = mid + 1;
      } else {
        hi = mid;
      }
    }

    // Columns count code points, as Python's str does; indices are UTF-16 units
    return [lo, code.slice(lineStarts[lo - 1], index).length];
  };

  const out: Unit[] = [];

  for (const [s, span] of spans) {
    // Preprocessor lines include their newline
    const e = rstripEnd(code, s, span);
    const text = code.slice(s, e);

    if (!BARE.has(text.trim())) {
      out.push({ start: point(s), end: point(e), text, startIndex: s, endIndex: e });
    }
  }

  return out;
}
