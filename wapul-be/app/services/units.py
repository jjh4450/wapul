# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2026 Hipster Timer Project Contributors

"""코드를 문장 단위로 나눈다 (tree-sitter)

문장 하나, 또는 복합문의 머리(`for (...)`, `if (...)`, `int main()`)가 한 단위다. 몸체는 더 나누므로
블럭이 반복문 안에서 시작하거나 끝날 수 있고, 한 줄의 두 문장(`int n; cin >> n;`)은 두 단위가 된다.
괄호, 홀로 선 키워드(`else`, `try`, `do`), 주석은 어느 단위에도 들지 않는다.

위치는 (줄, 열): 줄은 1부터, 열은 0부터 세는 글자 수(바이트가 아님)이고 끝은 포함하지 않는다.
"""

import re
from bisect import bisect_right
from dataclasses import dataclass
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

# 자식들이 문장 목록인 노드
_CONTAINERS = {
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
}
# 복합문에서 자기 문장을 품는 부분
_BODY_FIELDS = {"body", "consequence", "alternative", "definition"}
_CLAUSES = {
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
# case 라벨은 body 필드 없이 문장을 바로 품는다
_CASES = {"case_statement", "switch_block_statement_group"}
_COMMENTS = {"comment", "line_comment", "block_comment"}
# 혼자서는 아무 일도 하지 않는 머리
_BARE = {"", "{", "}", "else", "try", "do", "finally", "else:", "try:", "finally:"}
# 단위 사이에 남는 키워드. 보여 줄 때만 쓰고, 괄호와 주석은 버린다
_CONNECTIVES = {"else", "do", "try", "finally", "else:", "try:", "finally:"}
_COMMENT = re.compile(r"/\*.*?\*/|//[^\n]*|#[^\n]*", re.DOTALL)


@dataclass(frozen=True)
class Unit:
    start: tuple[int, int]
    end: tuple[int, int]
    text: str


@cache
def _parser(language: Language) -> Parser:
    return Parser(TSLanguage(_GRAMMARS[language].language()))


def _is_body(parent: Node, i: int, child: Node) -> bool:
    if child.type in _CONTAINERS or child.type in _CLAUSES:
        return True
    if parent.field_name_for_child(i) in _BODY_FIELDS:
        return True
    return parent.type in _CASES and (child.type.endswith("statement") or child.type.endswith("declaration"))


def _split(node: Node, out: list[tuple[int, int]]) -> None:
    children = node.children
    if not any(_is_body(node, i, c) for i, c in enumerate(children)):
        out.append((node.start_byte, node.end_byte))
        return
    header: list[Node] = []
    for i, child in enumerate(children):
        if child.type in _COMMENTS:
            continue
        if not _is_body(node, i, child):
            header.append(child)
            continue
        if header:
            out.append((header[0].start_byte, header[-1].end_byte))
            header = []
        if child.type in _CONTAINERS:
            for stmt in child.named_children:
                if stmt.type not in _COMMENTS:
                    _split(stmt, out)
        else:
            _split(child, out)
    if header:
        out.append((header[0].start_byte, header[-1].end_byte))


def units(code: str, language: Language) -> list[Unit]:
    data = code.encode()
    root = _parser(language).parse(data).root_node
    spans: list[tuple[int, int]] = []
    for stmt in root.named_children:
        if stmt.type not in _COMMENTS:
            _split(stmt, spans)

    line_starts = [0] + [i + 1 for i, b in enumerate(data) if b == 0x0A]

    def point(offset: int) -> tuple[int, int]:
        line = bisect_right(line_starts, offset) - 1
        return line + 1, len(data[line_starts[line] : offset].decode())

    out = []
    for s, e in sorted(spans):
        # 전처리 줄은 줄바꿈까지 포함한다
        e = s + len(data[s:e].rstrip())
        text = data[s:e].decode()
        if text.strip() not in _BARE:
            out.append(Unit(point(s), point(e), text))
    return out


def _connective(text: str) -> str:
    words = re.findall(r"[A-Za-z_]+:?", _COMMENT.sub(" ", text))
    return " ".join(word for word in words if word in _CONNECTIVES)


def show(code: str, us: list[Unit]) -> str:
    """단위마다 [uN]을 붙여 보여 준다. else·do·try는 번호 없는 줄로 남겨 어느 갈래인지 보이게 한다."""
    lines = code.split("\n")
    starts = [0]
    for line in lines[:-1]:
        starts.append(starts[-1] + len(line) + 1)

    def offset(point: tuple[int, int]) -> int:
        return starts[point[0] - 1] + point[1]

    def lead(row: int) -> str:
        line = lines[row]
        return line[: len(line) - len(line.lstrip())].expandtabs(4)

    out: list[str] = []
    prev_end = 0
    for i, u in enumerate(us, 1):
        gap_rows = code[prev_end : offset(u.start)].split("\n")
        first_row = u.start[0] - len(gap_rows)
        for n, part in enumerate(gap_rows[:-1]):
            if word := _connective(part):
                out.append(f"      {lead(first_row + n)}{word}")
        first, *rest = u.text.split("\n")
        prefix = lines[u.start[0] - 1][: u.start[1]]
        if inline := _connective(gap_rows[-1]):
            out.append(f"[u{i}] {lead(u.start[0] - 1)}{inline} {first}")
        else:
            indent = prefix if not prefix.strip() else " " * u.start[1]
            out.append(f"[u{i}] {indent.expandtabs(4)}{first}")
        out += [f"      {line}" for line in rest]
        prev_end = offset(u.end)
    return "\n".join(out)
