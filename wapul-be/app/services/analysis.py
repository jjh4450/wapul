# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2026 Hipster Timer Project Contributors

"""질문을 붙일 줄을 고르는 정적 분석 (tree-sitter)

- 조건·비교가 있는 줄: 경계 질문 대상. 넓게 잡아 더 묻는 쪽을 택한다.
- 재귀 호출·반복문이 있는 줄: 구조별 질문 대상.
"""

from dataclasses import dataclass, field
from functools import cache

import tree_sitter_cpp
import tree_sitter_java
import tree_sitter_python
from tree_sitter import Language as TSLanguage, Node, Parser

from app.models.study import Language

_GRAMMARS = {
    Language.CPP: tree_sitter_cpp,
    Language.JAVA: tree_sitter_java,
    Language.PYTHON: tree_sitter_python,
}

_CONDITION_NODES = {
    "if_statement",
    "while_statement",
    "do_statement",
    "switch_statement",
    "switch_expression",
    "match_statement",
    "conditional_expression",  # python, cpp 삼항
    "ternary_expression",  # java 삼항
    "comparison_operator",  # python 비교
}
_COMPARISON_OPS = {"<", ">", "<=", ">=", "==", "!="}
# min/max는 비교를 감춘 호출이라 경계 질문 대상에 넣는다
_COMPARING_CALLS = {"min", "max"}
_LOOP_NODES = {"for_statement", "for_range_loop", "enhanced_for_statement", "while_statement", "do_statement"}
_FUNCTION_NODES = {"function_definition", "method_declaration"}
_CALL_NODES = {"call", "call_expression", "method_invocation"}


@dataclass
class CodeFacts:
    """구조별로 해당하는 줄 번호 집합 (1부터 시작)"""

    condition_lines: set[int] = field(default_factory=set)
    loop_lines: set[int] = field(default_factory=set)
    recursion_lines: set[int] = field(default_factory=set)


@cache
def _parser(language: Language) -> Parser:
    return Parser(TSLanguage(_GRAMMARS[language].language()))


def _last_identifier(node: Node | None) -> str | None:
    """a.b.c, std::f, self.f 같은 이름에서 마지막 식별자만 꺼낸다"""
    if node is None:
        return None
    if node.type.endswith("identifier"):
        return node.text.decode()
    for child in reversed(node.named_children):
        name = _last_identifier(child)
        if name:
            return name
    return None


def _function_name(node: Node) -> str | None:
    name = node.child_by_field_name("name")
    if name is not None:
        return name.text.decode()
    # cpp: 선언자가 포인터/참조로 감싸여 있을 수 있어 function_declarator까지 내려간다
    declarator = node.child_by_field_name("declarator")
    while declarator is not None and declarator.type != "function_declarator":
        declarator = declarator.child_by_field_name("declarator")
    if declarator is None:
        return None
    return _last_identifier(declarator.child_by_field_name("declarator"))


def _callee_name(node: Node) -> str | None:
    if node.type == "method_invocation":
        name = node.child_by_field_name("name")
        return name.text.decode() if name is not None else None
    return _last_identifier(node.child_by_field_name("function"))


def analyze(code: str, language: Language) -> CodeFacts:
    facts = CodeFacts()
    root = _parser(language).parse(code.encode()).root_node

    def visit(node: Node, functions: tuple[str, ...]) -> None:
        line = node.start_point.row + 1
        if node.type in _CONDITION_NODES:
            facts.condition_lines.add(line)
        if node.type == "binary_expression" and any(
            not c.is_named and c.type in _COMPARISON_OPS for c in node.children
        ):
            facts.condition_lines.add(line)
        if node.type in _LOOP_NODES:
            facts.loop_lines.add(line)
        if node.type in _CALL_NODES:
            callee = _callee_name(node)
            if callee in _COMPARING_CALLS:
                facts.condition_lines.add(line)
            if callee and callee in functions:
                facts.recursion_lines.add(line)
        if node.type in _FUNCTION_NODES:
            name = _function_name(node)
            if name:
                functions = (*functions, name)
        for child in node.children:
            visit(child, functions)

    visit(root, ())
    return facts
