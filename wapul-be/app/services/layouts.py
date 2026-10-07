# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2026 Hipster Timer Project Contributors

"""결과물 md 배치안

구성: 어떤 문제인가 → 어떻게 접근했나 → 내 구현. 배치안끼리 다른 것은 순서뿐이고,
사용자가 쓴 문장은 그대로 옮긴다. 답이 빈 질문은 싣지 않는다.
"""

import re
import uuid
from dataclasses import dataclass

from app.models.study import Block, BlockKind, Question, QuestionKind, Record


@dataclass(frozen=True)
class Layout:
    id: str
    title: str
    markdown: str


def _fence(code: str, language: str) -> str:
    # 코드 안의 백틱 줄보다 긴 펜스를 써야 블럭이 중간에 끊기지 않는다
    longest = max((len(m) for m in re.findall(r"`+", code)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}{language}\n{code.rstrip()}\n{fence}"


def _runs(lines: list[int]) -> list[tuple[int, int]]:
    """정렬된 줄 번호를 이어진 구간으로 묶는다"""
    runs: list[tuple[int, int]] = []
    for line in lines:
        if runs and runs[-1][1] + 1 == line:
            runs[-1] = (runs[-1][0], line)
        else:
            runs.append((line, line))
    return runs


def _qa(question: Question) -> str:
    return f"**{question.text}**\n\n{question.answer.strip()}"


class _Parts:
    def __init__(self, record: Record, blocks: list[Block], questions: list[Question]):
        self.record = record
        self.blocks = blocks
        self.lines = record.code.splitlines()
        # 블럭에 이름이 없어 종류와 로직 순번으로 부른다
        self.labels: dict[uuid.UUID, str] = {}
        logic = 0
        for block in blocks:
            if block.kind == BlockKind.LOGIC:
                logic += 1
                self.labels[block.id] = f"로직 {logic}"
            else:
                self.labels[block.id] = "입력" if block.kind == BlockKind.INPUT else "출력"
        answered = [q for q in questions if q.answer.strip()]
        self.by_block: dict[uuid.UUID, list[Question]] = {}
        self.loose: list[Question] = []
        self.problem: list[Question] = []
        self.revision: list[Question] = []
        for q in answered:
            if q.kind == QuestionKind.PROBLEM:
                self.problem.append(q)
            elif q.kind == QuestionKind.REVISION:
                self.revision.append(q)
            elif q.block_id is None:
                self.loose.append(q)
            else:
                self.by_block.setdefault(q.block_id, []).append(q)

    def head(self) -> str:
        r = self.record
        parts = [
            f"# {r.problem}",
            "## 어떤 문제인가",
            r.problem,
            "## 어떻게 접근했나",
            f"**핵심 아이디어**\n\n{r.key_idea}",
        ]
        parts += [_qa(q) for q in self.problem]
        return "\n\n".join(parts)

    def full_code(self) -> str:
        return _fence(self.record.code, self.record.language)

    def block_runs(self, block: Block) -> list[tuple[int, int]]:
        units = self.record.units
        lines = {line for i in block.units for line in range(units[i]["start"][0], units[i]["end"][0] + 1)}
        return _runs(sorted(lines))

    def block_heading(self, block: Block) -> str:
        where = ", ".join(str(a) if a == b else f"{a}~{b}" for a, b in self.block_runs(block))
        return f"### {self.labels[block.id]} ({where}줄)"

    def block_code(self, block: Block) -> str:
        # 블럭의 문장이 떨어져 있으면 사이를 ...로 줄인다
        parts = ["\n".join(self.lines[a - 1 : b]) for a, b in self.block_runs(block)]
        return _fence("\n...\n".join(parts), self.record.language)

    def block_notes(self, block: Block) -> list[str]:
        return [_qa(q) for q in self.by_block.get(block.id, [])]

    def tail(self) -> list[str]:
        parts = [_qa(q) for q in self.loose]
        if self.revision:
            parts.append("### 처음 제출과 달라진 점")
            parts += [_qa(q) for q in self.revision]
        return parts


def build_layouts(record: Record, blocks: list[Block], questions: list[Question]) -> list[Layout]:
    p = _Parts(record, blocks, questions)

    code_first = [p.head(), "## 내 구현", p.full_code()]
    for block in blocks:
        code_first += [p.block_heading(block), *p.block_notes(block)]
    code_first += p.tail()

    interleaved = [p.head(), "## 내 구현"]
    for block in blocks:
        interleaved += [p.block_heading(block), p.block_code(block), *p.block_notes(block)]
    interleaved += p.tail()
    interleaved += ["### 전체 코드", p.full_code()]

    notes_first = [p.head(), "## 내 구현"]
    for block in blocks:
        notes_first += [p.block_heading(block), *p.block_notes(block)]
    notes_first += p.tail()
    notes_first += ["### 전체 코드", p.full_code()]

    return [
        Layout("code-first", "전체 코드 먼저", "\n\n".join(code_first) + "\n"),
        Layout("interleaved", "블럭마다 코드와 설명", "\n\n".join(interleaved) + "\n"),
        Layout("notes-first", "설명 먼저, 코드는 끝에", "\n\n".join(notes_first) + "\n"),
    ]
