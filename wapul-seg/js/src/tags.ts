// What each unit asks of the learner, found from the tree (docs/ml/design.ko.md: the blocks that
// get boundary questions, for conditions and comparisons, and structure questions, for loops and
// recursion, are chosen by static analysis, not by the model). Not part of the Python model.

import { type Node, type Tree } from 'web-tree-sitter';

import { type UnitAst } from './ast.ts';
import { DEFS } from './languages.ts';
import { type Unit } from './units.ts';

export interface Tags {
  /** A branch, a ternary, or a comparison (`<`, `==`, ...) in the unit. */
  condition: boolean;
  /** The unit is a loop header. */
  loop: boolean;
  /** The unit calls the function that holds it. */
  recursion: boolean;
}

const COMPARISONS = new Set(['<', '>', '<=', '>=', '==', '!=', '===', '!==', '<>', '<=>']);

/** Operator nodes that compare when their operator is one of COMPARISONS. */
const OPERATIONS = new Set([
  'binary_expression',
  'binary',
  'infix_expression',
  'comparison_expression',
  'equality_expression'
]);

/** Nodes that always compare or choose: Python's comparisons and every grammar's ternary. */
const ALWAYS = new Set([
  'comparison_operator',
  'conditional_expression',
  'ternary_expression',
  'conditional'
]);

const CALLS = new Set([
  'call_expression',
  'call',
  'method_invocation',
  'invocation_expression',
  'function_call_expression',
  'member_call_expression',
  'nullsafe_member_call_expression',
  'scoped_call_expression'
]);

/** The last identifier of `a.b.f`, `A::f`, `f<T>`. */
const LAST_NAME = /([A-Za-z_$][\w$]*)\s*(?:<[^<>()]*>)?\s*$/;

function lastName(node: Node | null): string | undefined {
  return node === null ? undefined : (LAST_NAME.exec(node.text)?.[1] ?? undefined);
}

function compares(node: Node): boolean {
  if (ALWAYS.has(node.type)) {
    return true;
  }

  // The operator is an anonymous token, or a named one holding the symbol (Scala)
  return (
    OPERATIONS.has(node.type) &&
    node.children.some(
      (c) =>
        (!c.isNamed && COMPARISONS.has(c.type)) ||
        (c.type === 'operator_identifier' && COMPARISONS.has(c.text))
    )
  );
}

function calleeName(call: Node): string | undefined {
  return lastName(
    call.childForFieldName('function') ??
      call.childForFieldName('name') ??
      call.childForFieldName('method') ??
      call.firstNamedChild
  );
}

/** A definition's name: its `name` field, or the end of its declarator chain (C, C++). */
function definitionName(def: Node): string | undefined {
  const name = def.childForFieldName('name');

  if (name !== null) {
    return lastName(name);
  }

  let declarator = def.childForFieldName('declarator');

  for (let next = declarator; next !== null; next = next.childForFieldName('declarator')) {
    declarator = next;
  }

  return lastName(declarator);
}

/** The definition that starts at `start`, as ast.ts records it. */
function definitionAt(tree: Tree, start: number): Node | undefined {
  // A one-character range: an empty one at a node's start can stop above the node (Scala)
  for (
    let node = tree.rootNode.descendantForIndex(start, start + 1);
    node !== null;
    node = node.parent
  ) {
    if (DEFS.has(node.type) && node.startIndex === start) {
      return node;
    }
  }

  return undefined;
}

/** Whether some node inside `start..end` passes `test`. */
function anyInside(node: Node, start: number, end: number, test: (n: Node) => boolean): boolean {
  if (node.endIndex <= start || node.startIndex >= end) {
    return false;
  }

  if (node.startIndex >= start && node.endIndex <= end && test(node)) {
    return true;
  }

  return node.children.some((c) => anyInside(c, start, end, test));
}

export function unitTags(tree: Tree, units: Unit[], asts: UnitAst[]): Tags[] {
  const names = new Map<number, string | undefined>();

  return units.map((u, j) => {
    const a = asts[j];
    const root = tree.rootNode;
    const s = u.startIndex;
    const e = u.endIndex;
    let recursion = false;

    if (a.function >= 0) {
      if (!names.has(a.function)) {
        const def = definitionAt(tree, a.function);
        names.set(a.function, def === undefined ? undefined : definitionName(def));
      }

      const name = names.get(a.function);
      recursion =
        name !== undefined &&
        anyInside(root, s, e, (n) => CALLS.has(n.type) && calleeName(n) === name);
    }

    return {
      condition: a.category === 'branch' || anyInside(root, s, e, compares),
      loop: a.category === 'loop',
      recursion
    };
  });
}
