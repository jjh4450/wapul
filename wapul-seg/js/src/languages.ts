// Node rules per language. The tables for cpp, java, python and rust copy wapul-ml's
// wapul_ml/units.py and wapul_ml/features/unit_ast.py, the originals, and must keep giving
// the same units and facts (tests/parity.test.ts). The other languages were added here from
// their grammars' node names (docs/ml/deploy.ko.md, "지원 언어"); node names are shared across
// grammars, so a name added for one language must not change another's output.

export const LANGUAGES = [
  'cpp',
  'java',
  'python',
  'rust',
  'c',
  'kotlin',
  'javascript',
  'go',
  'csharp',
  'swift',
  'ruby',
  'scala',
  'php'
] as const;

export type Language = (typeof LANGUAGES)[number];

/** The grammar's `.wasm` under the release's `grammars/` (tools/grammars.ts says where it comes from). */
export function grammarFile(language: Language): string {
  return `grammars/tree-sitter-${language}.wasm`;
}

// --- Statement units (units.py) ---

/** Nodes whose named children are a list of statements. */
export const CONTAINERS = new Set([
  'translation_unit',
  'compound_statement',
  'declaration_list',
  'field_declaration_list',
  'program',
  'block',
  'class_body',
  'constructor_body',
  'switch_block',
  'module',
  'match_block',
  // javascript, csharp
  'statement_block',
  'switch_body',
  // go
  'statement_list',
  // kotlin: a trailing lambda's statements (`repeat(n) { ... }`)
  'lambda_literal',
  // swift
  'statements',
  // ruby
  'body_statement',
  'block_body',
  'then',
  'do',
  'else',
  'ensure',
  'begin',
  // scala
  'template_body',
  'case_block'
]);

/** Containers that sit directly inside another container, holding its statements: Go's
 * `block > statement_list`, Ruby's `block > block_body`. Their statements are the outer
 * container's. */
export const NESTED = new Set(['statement_list', 'block_body', 'ensure']);

/** Parts of a compound statement that hold statements of their own. */
export const BODY_FIELDS = new Set(['body', 'consequence', 'alternative', 'definition', 'block']);

export const CLAUSES = new Set([
  'else_clause',
  'elif_clause',
  'except_clause',
  'finally_clause',
  'catch_clause',
  'case_statement',
  'switch_block_statement_group',
  'switch_rule',
  'case_clause',
  // javascript
  'switch_case',
  'switch_default',
  // go
  'expression_case',
  'default_case',
  'type_case',
  'communication_case',
  // kotlin
  'function_body',
  'when_entry',
  'catch_block',
  'finally_block',
  'annotated_lambda',
  // csharp
  'switch_section',
  // swift
  'switch_entry',
  // ruby
  'elsif',
  'when',
  'in_clause',
  'rescue',
  'do_block',
  // php
  'else_if_clause',
  'default_statement'
]);

/** Case labels hold their statements directly, with no body field. */
export const CASES = new Set([
  'case_statement',
  'switch_block_statement_group',
  'switch_section',
  'default_statement'
]);

/** Children that belong to no unit: comments, and a block's parameter list (Ruby `|x|`,
 * Kotlin `x ->`), heredoc bodies, PHP's open tag. */
export const SKIPPED = new Set([
  'comment',
  'line_comment',
  'block_comment',
  'block_parameters',
  'lambda_parameters',
  'heredoc_body',
  'php_tag'
]);

/** Rust control flow is an expression; as a statement it sits inside an expression_statement. */
export const RUST_CONTROL = new Set([
  'if_expression',
  'for_expression',
  'while_expression',
  'loop_expression',
  'match_expression'
]);

/** Wrappers whose only named child is the real statement (C# top-level statements). */
export const UNWRAP = new Set(['global_statement']);

/** (parent, child) pairs where the child is a body without a body field: Rust `else if` and
 * match arms, Kotlin and Swift `else if`. */
export const BODY_PAIRS = new Set([
  'else_clause>if_expression',
  'match_arm>block',
  'if_expression>if_expression',
  'if_statement>if_statement'
]);

/** Branches whose body fields may hold a plain expression (Scala `if (c) a else b`,
 * `case 1 => f()`): only a block or a nested if is a body there, as in Rust. */
export const EXPRESSION_BRANCHES = new Set(['if_expression', 'case_clause']);

export const BLOCK_BODIES = new Set(['block', 'if_expression']);

/** Header text that means nothing on its own. */
export const BARE = new Set([
  '',
  '{',
  '}',
  'else',
  'try',
  'do',
  'finally',
  'else:',
  'try:',
  'finally:',
  // ruby
  'end',
  'rescue',
  'ensure',
  'begin'
]);

// --- AST facts (unit_ast.py) ---

/** Languages whose statements are bare expressions (no `expression_statement` wrapper), so
 * a unit's owner node is the expression itself. */
export const BARE_EXPRESSION_LANGUAGES: ReadonlySet<Language> = new Set<Language>([
  'kotlin',
  'swift',
  'ruby',
  'scala'
]);

/** Nodes that are a variable or function name: what `reads` and `writes` collect. */
export const IDENTIFIER_TYPES = new Set([
  'identifier',
  // swift
  'simple_identifier',
  // php: `$x` and bare names (functions, constants)
  'variable_name',
  'name',
  // ruby
  'instance_variable'
]);

/** Coarse statement categories shared across languages, in the block features' order. */
export const CATEGORIES = [
  'import',
  'def',
  'loop',
  'branch',
  'return',
  'jump',
  'declaration',
  'expression',
  'other'
] as const;

export type Category = (typeof CATEGORIES)[number];

// Bare expressions used as statements (Kotlin, Swift, Ruby, Scala have no expression_statement
// wrapper) stay "other": their node names (`assignment`, `call_expression`...) also occur inside
// statements of the original four languages, where naming them would change the owner node.
const CATEGORY_TYPES: Record<Exclude<Category, 'other'>, string[]> = {
  import: [
    'preproc_include',
    'using_declaration',
    'import_statement',
    'import_from_statement',
    'import_declaration',
    'package_declaration',
    'preproc_def',
    'alias_declaration',
    'type_definition',
    'use_declaration',
    // c
    'preproc_function_def',
    // kotlin
    'import',
    'package_header',
    'type_alias',
    // go
    'package_clause',
    // csharp
    'using_directive',
    // scala
    'package_clause',
    // php
    'namespace_use_declaration',
    'namespace_definition'
  ],
  def: [
    'function_definition',
    'method_declaration',
    'constructor_declaration',
    'class_definition',
    'class_declaration',
    'class_specifier',
    'struct_specifier',
    'mod_item',
    'function_item',
    'impl_item',
    'struct_item',
    'enum_item',
    'trait_item',
    // javascript
    'function_declaration',
    'generator_function_declaration',
    'method_definition',
    // kotlin
    'object_declaration',
    'companion_object',
    'secondary_constructor',
    'anonymous_initializer',
    // go
    'type_declaration',
    // csharp
    'namespace_declaration',
    'struct_declaration',
    'interface_declaration',
    'enum_declaration',
    'record_declaration',
    'local_function_statement',
    // swift
    'protocol_declaration',
    // ruby (`module` would also catch Python's root node, so it stays "other")
    'method',
    'singleton_method',
    'class',
    // scala
    'object_definition',
    'trait_definition'
  ],
  loop: [
    'for_statement',
    'for_range_loop',
    'while_statement',
    'do_statement',
    'enhanced_for_statement',
    'for_expression',
    'while_expression',
    'loop_expression',
    // javascript
    'for_in_statement',
    // kotlin
    'do_while_statement',
    // csharp
    'foreach_statement',
    // swift
    'repeat_while_statement',
    // ruby
    'while',
    'until',
    'for',
    'while_modifier',
    'until_modifier',
    // scala
    'do_while_expression'
  ],
  branch: [
    'if_statement',
    'else_clause',
    'elif_clause',
    'switch_statement',
    'case_statement',
    'switch_block_statement_group',
    'switch_rule',
    'try_statement',
    'catch_clause',
    'except_clause',
    'if_expression',
    'match_expression',
    'match_arm',
    // javascript
    'switch_case',
    'switch_default',
    // kotlin
    'when_expression',
    'when_entry',
    'try_expression',
    'catch_block',
    'finally_block',
    // go
    'expression_switch_statement',
    'type_switch_statement',
    'select_statement',
    'expression_case',
    'default_case',
    'type_case',
    'communication_case',
    // csharp
    'switch_section',
    'finally_clause',
    // swift
    'switch_entry',
    'guard_statement',
    // ruby
    'if',
    'unless',
    'elsif',
    'case',
    'when',
    'in_clause',
    'begin',
    'rescue',
    'if_modifier',
    'unless_modifier',
    // php
    'else_if_clause',
    'default_statement'
  ],
  return: [
    'return_statement',
    'return_expression',
    // swift: return, break and continue share one node; return is the common one
    'control_transfer_statement',
    // ruby
    'return'
  ],
  jump: [
    'break_statement',
    'continue_statement',
    'break_expression',
    'continue_expression',
    // c
    'goto_statement',
    // kotlin
    'jump_expression',
    // ruby
    'break',
    'next',
    'redo',
    'retry'
  ],
  declaration: [
    'declaration',
    'local_variable_declaration',
    'field_declaration',
    'let_declaration',
    'const_item',
    'static_item',
    // javascript
    'lexical_declaration',
    'variable_declaration',
    'field_definition',
    // kotlin, swift, php
    'property_declaration',
    // go
    'short_var_declaration',
    'var_declaration',
    'const_declaration',
    // csharp
    'local_declaration_statement',
    // scala
    'val_definition',
    'var_definition'
  ],
  expression: [
    'expression_statement',
    // go
    'assignment_statement',
    'inc_statement',
    'dec_statement',
    'defer_statement',
    'go_statement',
    // php
    'echo_statement'
  ]
};

function byType(): Map<string, Category> {
  const out = new Map<string, Category>();

  for (const category of CATEGORIES) {
    if (category !== 'other') {
      for (const type of CATEGORY_TYPES[category]) {
        out.set(type, category);
      }
    }
  }

  return out;
}

export const CATEGORY_BY_TYPE: ReadonlyMap<string, Category> = byType();

export const LOOPS = new Set(CATEGORY_TYPES.loop);

export const DEFS = new Set(CATEGORY_TYPES.def);

export const CONTROL = new Set([...CATEGORY_TYPES.loop, ...CATEGORY_TYPES.branch]);

/** Targets that list several names: Python `a, b = ...`, Rust `let (a, b) = ...`, Go
 * `a, b := ...`, JS `const [a, b] = ...`, Kotlin `val (a, b) = ...`, Ruby `a, b = ...`,
 * C# `(a, b) = ...`, PHP `list($a, $b) = ...`. */
export const TARGET_LISTS = new Set([
  'pattern_list',
  'tuple_pattern',
  'tuple',
  'list_pattern',
  'expression_list',
  'array_pattern',
  'multi_variable_declaration',
  'left_assignment_list',
  'tuple_expression',
  'list_literal'
]);
