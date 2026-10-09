// The names in solution code, for completing them while writing about the code (wapul's answer
// fields): identifiers, called and defined functions, subscripts like `dp[i][j]`, and short string
// literals. Nothing here feeds the model, so the node sets are separate from the model's
// (IDENTIFIER_TYPES, LITERALS) and may grow without changing `segment`'s output.

import { type Node, type Tree } from 'web-tree-sitter';

import { LITERALS } from './kinds.ts';
import { IDENTIFIER_TYPES } from './languages.ts';

export type NameKind = 'name' | 'function' | 'subscript' | 'string';

export interface Name {
  text: string;
  kind: NameKind;
  /** Lines (from 1) of the normalized code it appears on, in order. */
  lines: number[];
  /** How many times it appears. */
  count: number;
}

/** Name nodes beyond the model's identifiers: members, properties, types, Ruby constants. */
const NAME_TYPES = new Set([
  ...IDENTIFIER_TYPES,
  'field_identifier',
  'property_identifier',
  'shorthand_property_identifier',
  'type_identifier',
  'constant'
]);

/** Indexing with brackets. Swift has none: its `a[i]` is a call whose arguments open with `[`. */
const SUBSCRIPT_TYPES = new Set([
  // c, cpp, javascript, php
  'subscript_expression',
  // java
  'array_access',
  // python
  'subscript',
  // rust, kotlin, go
  'index_expression',
  // csharp
  'element_access_expression',
  // ruby
  'element_reference'
]);

/** Imports and package lines: their names (`std`, `sys`, `java.util`) are not what one writes
 * about. `#define` and type aliases stay, since their names are used in the code. */
const IMPORTS = new Set([
  'preproc_include',
  'using_declaration',
  'import_statement',
  'import_from_statement',
  'import_declaration',
  'package_declaration',
  // kotlin
  'import',
  'package_header',
  // go, scala
  'package_clause',
  // csharp
  'using_directive',
  // php
  'namespace_use_declaration'
]);

/** Longer texts are not worth completing and would crowd the list. */
const MAX_LENGTH = 40;

const CALL = /call|invocation/;

const DEFINITION = /function|method/;

// A name that is the last part of one of these is a member: `v.push_back`, `obj.method`
const MEMBER = /member|field_expression|selector|navigation|attribute/;

function same(a: Node | null, b: Node): boolean {
  return a !== null && a.startIndex === b.startIndex && a.endIndex === b.endIndex;
}

/** A call whose arguments open with `[` indexes (Swift's `a[i]`). */
function indexes(call: Node): boolean {
  return call.lastNamedChild?.text.startsWith('[') ?? false;
}

/** Whether `node` names a function: one being defined, or the one a call calls. */
function isFunction(node: Node): boolean {
  const parent = node.parent;

  if (parent === null) {
    return false;
  }

  if (
    DEFINITION.test(parent.type) &&
    (same(parent.childForFieldName('name'), node) ||
      same(parent.childForFieldName('declarator'), node))
  ) {
    return true;
  }

  // Step out of member access when the name is its last part: `v.push_back(x)`
  let callee = node;
  let call: Node | null = parent;

  while (call !== null && MEMBER.test(call.type) && same(call.lastNamedChild, callee)) {
    callee = call;
    call = call.parent;
  }

  if (call === null || !CALL.test(call.type) || indexes(call)) {
    return false;
  }

  return (
    ['function', 'method', 'name'].some((field) => same(call.childForFieldName(field), callee)) ||
    same(call.firstNamedChild, callee)
  );
}

/** Every name in the tree, in order of first appearance. */
export function collectNames(tree: Tree): Name[] {
  const found = new Map<string, Name>();

  const add = (text: string, kind: NameKind, line: number) => {
    if (text.length > MAX_LENGTH || text.includes('\n') || text === '_') {
      return;
    }

    const name = found.get(text);

    if (name === undefined) {
      found.set(text, { text, kind, lines: [line], count: 1 });

      return;
    }

    name.count += 1;

    if (name.lines.at(-1) !== line) {
      name.lines.push(line);
    }

    // A name called anywhere is a function
    if (kind === 'function') {
      name.kind = kind;
    }
  };

  // Depth first in source order, so lines come out sorted
  const stack: Node[] = [tree.rootNode];

  for (let node = stack.pop(); node !== undefined; node = stack.pop()) {
    const line = node.startPosition.row + 1;

    if (IMPORTS.has(node.type)) {
      continue;
    }

    if (node.isNamed && NAME_TYPES.has(node.type)) {
      add(node.text, isFunction(node) ? 'function' : 'name', line);

      continue;
    }

    if (node.isNamed && LITERALS.has(node.type)) {
      add(node.text, 'string', line);

      continue;
    }

    if (SUBSCRIPT_TYPES.has(node.type) || (CALL.test(node.type) && indexes(node))) {
      add(node.text, 'subscript', line);
    }

    for (let i = node.childCount - 1; i >= 0; i--) {
      const child = node.child(i);

      if (child !== null) {
        stack.push(child);
      }
    }
  }

  return [...found.values()];
}
