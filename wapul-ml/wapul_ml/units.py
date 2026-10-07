"""Split code into statement units, the atoms that labels group into blocks.

A unit is one simple statement, or the header of a compound one (`for (...)`, `if (...)`,
`int main()`) whose body is split further. So a block can start or end inside a loop, and
a line holding two statements (`int n; cin >> n;`) gives two units. Braces, bare keywords
(`else`, `try`, `do`) and comments belong to no unit, so labels and the model never lean
on what a comment says.

Positions are (line, col): line 1-based, col 0-based in characters (not bytes), end exclusive.
"""

from bisect import bisect_right
from dataclasses import dataclass
from functools import cache

import tree_sitter_cpp
import tree_sitter_java
import tree_sitter_python
import tree_sitter_rust
from tree_sitter import Language, Node, Parser

GRAMMARS = {
    "cpp": tree_sitter_cpp,
    "java": tree_sitter_java,
    "python": tree_sitter_python,
    "rust": tree_sitter_rust,
}

# Nodes whose named children are a list of statements
CONTAINERS = {
    "translation_unit",
    "compound_statement",
    "declaration_list",
    "field_declaration_list",
    "program",
    "block",
    "class_body",
    "constructor_body",
    "switch_block",
    "module",
    "match_block",
}
# Parts of a compound statement that hold statements of their own
BODY_FIELDS = {"body", "consequence", "alternative", "definition"}
CLAUSES = {
    "else_clause",
    "elif_clause",
    "except_clause",
    "finally_clause",
    "catch_clause",
    "case_statement",
    "switch_block_statement_group",
    "switch_rule",
    "case_clause",
}
# Case labels hold their statements directly, with no body field
CASES = {"case_statement", "switch_block_statement_group"}
COMMENTS = {"comment", "line_comment", "block_comment"}
# Rust control flow is an expression; as a statement it sits inside an expression_statement
RUST_CONTROL = {"if_expression", "for_expression", "while_expression", "loop_expression", "match_expression"}
# Header text that means nothing on its own
BARE = {"", "{", "}", "else", "try", "do", "finally", "else:", "try:", "finally:"}


@dataclass(frozen=True)
class Unit:
    start: tuple[int, int]
    end: tuple[int, int]
    text: str


@cache
def parser(language: str) -> Parser:
    return Parser(Language(GRAMMARS[language].language()))


def is_body(parent: Node, i: int, child: Node) -> bool:
    if parent.type == "struct_expression":  # Rust `Self { a, b }` is a value, not a body
        return False
    if child.type in CONTAINERS or child.type in CLAUSES:
        return True
    if parent.field_name_for_child(i) in BODY_FIELDS:
        return True
    # Rust: `else if` holds the next if directly, and a match arm may hold a block
    if (parent.type, child.type) in (("else_clause", "if_expression"), ("match_arm", "block")):
        return True
    return parent.type in CASES and (child.type.endswith("statement") or child.type.endswith("declaration"))


def split(node: Node, out: list[tuple[int, int]]) -> None:
    if node.type == "expression_statement" and node.named_children and node.named_children[0].type in RUST_CONTROL:
        node = node.named_children[0]
    children = node.children
    if not any(is_body(node, i, c) for i, c in enumerate(children)):
        out.append((node.start_byte, node.end_byte))
        return
    header: list[Node] = []
    for i, child in enumerate(children):
        if child.type in COMMENTS:
            continue
        if not is_body(node, i, child):
            header.append(child)
            continue
        if header:
            out.append((header[0].start_byte, header[-1].end_byte))
            header = []
        if child.type in CONTAINERS:
            for stmt in child.named_children:
                if stmt.type not in COMMENTS:
                    split(stmt, out)
        else:
            split(child, out)
    if header:
        out.append((header[0].start_byte, header[-1].end_byte))


def units(code: str, language: str) -> list[Unit]:
    data = code.encode()
    root = parser(language).parse(data).root_node
    spans: list[tuple[int, int]] = []
    for stmt in root.named_children:
        if stmt.type not in COMMENTS:
            split(stmt, spans)

    line_starts = [0] + [i + 1 for i, b in enumerate(data) if b == 0x0A]

    def point(offset: int) -> tuple[int, int]:
        line = bisect_right(line_starts, offset) - 1
        return line + 1, len(data[line_starts[line] : offset].decode())

    out = []
    for s, e in sorted(spans):
        # Preprocessor lines include their newline
        e = s + len(data[s:e].rstrip())
        text = data[s:e].decode()
        if text.strip() not in BARE:
            out.append(Unit(point(s), point(e), text))
    return out
