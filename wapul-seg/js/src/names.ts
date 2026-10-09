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
  /** For a function defined in the code, the names of its parameters (`solve(n, k)` gives n, k),
   * from the first definition that names them. Functions only called here (`max`, `push_back`)
   * have none. */
  params?: string[];
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

/** Declarations and assignments, which may bind a name to a function value. */
const BINDING = /declarator|declaration|assignment|definition|var_spec/;

/** Nodes between a name and the declaration binding it: Go's `a, b :=`, Kotlin's and Swift's
 * `val`/`let` patterns. */
const BINDING_WRAPPERS = new Set(['expression_list', 'variable_declaration', 'pattern']);

/** Function values: `[&](int u) {...}`, `(a, b) => ...`, `lambda x: ...`, `func(a int) {...}` */
const LAMBDA = /lambda|arrow_function|function_expression|closure|func_literal|anonymous_function/;

/** Under a parameter list, the parts that name no parameter: types, default values, array sizes,
 * Swift's argument labels, and a function pointer's own parameters. */
const NOT_PARAMETER_NAMES = new Set([
  'type',
  'default_value',
  'value',
  'right',
  'size',
  'external_name',
  'parameters'
]);

/** Type nodes (`vector<int>`, `user_type`, `primitive_type`), whose names are not parameters. */
const TYPE = /(^|_)type($|_)/;

// A name that is the last part of one of these is a member: `v.push_back`, `obj.method`
const MEMBER = /member|field_expression|selector|navigation|attribute/;

function same(a: Node | null, b: Node): boolean {
  return a !== null && a.startIndex === b.startIndex && a.endIndex === b.endIndex;
}

/** A call whose arguments open with `[` indexes (Swift's `a[i]`). */
function indexes(call: Node): boolean {
  return call.lastNamedChild?.text.startsWith('[') ?? false;
}

/** The function `node` names where it is defined: the definition, or the function value a
 * variable is given (`auto dfs = [&](int u) {...}`, `const f = (a) => ...`). */
function definedFunction(node: Node): Node | null {
  const parent = node.parent;

  if (parent === null) {
    return null;
  }

  if (
    DEFINITION.test(parent.type) &&
    (same(parent.childForFieldName('name'), node) ||
      same(parent.childForFieldName('declarator'), node))
  ) {
    return parent;
  }

  const binding = BINDING_WRAPPERS.has(parent.type) ? parent.parent : parent;

  if (binding === null || !BINDING.test(binding.type)) {
    return null;
  }

  // The value follows the name, in a field or, in Kotlin and C#, without one
  let value =
    binding.childForFieldName('value') ??
    binding.childForFieldName('right') ??
    binding.namedChildren.find((child) => child.startIndex >= node.endIndex) ??
    null;

  if (value?.type === 'expression_list') {
    value = value.firstNamedChild;
  }

  return value !== null && value.startIndex >= node.endIndex && LAMBDA.test(value.type)
    ? value
    : null;
}

/** Whether `node` is what a call calls: `solve(1)`, `v.push_back(x)`. */
function called(node: Node): boolean {
  // Step out of member access when the name is its last part: `v.push_back(x)`
  let callee = node;
  let call: Node | null = node.parent;

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

/** The names of a function's parameters in order: `(int n, vector<int>& v, int k = 0)` gives
 * n, v, k. */
function parameters(fn: Node): string[] {
  // Kotlin wraps them without a field, a C++ lambda keeps them in its declarator, and Swift does
  // not wrap them
  const list =
    fn.childForFieldName('parameters') ??
    fn.childForFieldName('parameter') ??
    fn.childForFieldName('declarator')?.childForFieldName('parameters') ??
    fn.namedChildren.find((child) => child.type.endsWith('parameters')) ??
    null;

  const names: string[] = [];

  const visit = (node: Node) => {
    if (IDENTIFIER_TYPES.has(node.type)) {
      // Python's receiver is not passed in the parentheses: `self.solve(n)`
      if (node.text !== 'self') {
        names.push(node.text);
      }

      return;
    }

    for (let i = 0; i < node.childCount; i++) {
      const child = node.child(i);

      // Kotlin gives a default value no field: `k: Int = 0`
      if (
        child === null ||
        !child.isNamed ||
        TYPE.test(child.type) ||
        NOT_PARAMETER_NAMES.has(node.fieldNameForChild(i) ?? '') ||
        node.child(i - 1)?.type === '='
      ) {
        continue;
      }

      visit(child);
    }
  };

  for (const part of list === null
    ? fn.namedChildren.filter((child) => child.type === 'parameter')
    : [list]) {
    visit(part);
  }

  return names;
}

/** Every name in the tree, in order of first appearance. */
export function collectNames(tree: Tree): Name[] {
  const found = new Map<string, Name>();

  const add = (text: string, kind: NameKind, line: number, params?: string[]) => {
    if (text.length > MAX_LENGTH || text.includes('\n') || text === '_') {
      return;
    }

    const name = found.get(text);

    if (name === undefined) {
      found.set(text, { text, kind, params, lines: [line], count: 1 });

      return;
    }

    name.count += 1;

    // A prototype names no parameters (`void dfs(int);`); its definition below does
    if (params !== undefined && (name.params === undefined || name.params.length === 0)) {
      name.params = params;
    }

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
      const defined = definedFunction(node);

      add(
        node.text,
        defined !== null || called(node) ? 'function' : 'name',
        line,
        defined === null ? undefined : parameters(defined)
      );

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
