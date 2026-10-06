# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2026 Hipster Timer Project Contributors

"""코드를 입력/출력/로직 블럭으로 나누는 분할기

실제 분할은 줄 단위 분류 모델(wapul-seg)이 맡는다. 모델이 붙기 전까지는 빈 줄 기준 규칙 분할기를 쓴다.
모델로 바꿀 때는 Segmenter를 구현한 클래스를 get_segmenter()에서 돌려주면 된다.
"""

import re
from dataclasses import dataclass
from typing import Protocol

from app.models.study import BlockKind, Language


@dataclass(frozen=True)
class BlockDraft:
    kind: BlockKind
    name: str
    start_line: int  # 1부터 시작, 양 끝 포함
    end_line: int


class Segmenter(Protocol):
    def segment(self, code: str, language: Language) -> list[BlockDraft]: ...


_INPUT = re.compile(
    r"\binput\s*\(|sys\.stdin|\bcin\b|\bscanf\s*\(|\bgetline\s*\(|\bScanner\b|\bBufferedReader\b|readLine"
)
_OUTPUT = re.compile(r"\bprint\s*\(|sys\.stdout|\bcout\b|\bprintf\s*\(|\bputs\s*\(|System\.out|\bBufferedWriter\b")
# include/import/using 같은 머리말 줄은 어느 블럭에도 넣지 않는다
_PREAMBLE = re.compile(
    r"^\s*(#include|#define|import\s|from\s+\S+\s+import\s|using\s|package\s|//|#(?!include|define))"
)
_HAS_WORD = re.compile(r"\w")


class RuleSegmenter:
    """빈 줄로 나눈 덩어리마다 입출력 호출 여부로 종류를 정하는 임시 분할기"""

    def segment(self, code: str, language: Language) -> list[BlockDraft]:
        chunks: list[list[int]] = []
        current: list[int] = []
        for number, line in enumerate(code.splitlines(), start=1):
            if line.strip():
                current.append(number)
            elif current:
                chunks.append(current)
                current = []
        if current:
            chunks.append(current)

        lines = code.splitlines()
        ranges: list[tuple[int, int]] = []
        for chunk in chunks:
            body = [n for n in chunk if not _PREAMBLE.match(lines[n - 1])]
            if not body:
                continue
            # 닫는 괄호뿐인 덩어리는 앞 블럭에 붙인다
            if ranges and not any(_HAS_WORD.search(lines[n - 1]) for n in body):
                ranges[-1] = (ranges[-1][0], body[-1])
                continue
            ranges.append((body[0], body[-1]))

        drafts: list[BlockDraft] = []
        logic_count = 0
        for start, end in ranges:
            text = "\n".join(lines[start - 1 : end])
            if _INPUT.search(text):
                kind, name = BlockKind.INPUT, "입력 받기"
            elif _OUTPUT.search(text):
                kind, name = BlockKind.OUTPUT, "결과 출력"
            else:
                logic_count += 1
                kind, name = BlockKind.LOGIC, f"로직 {logic_count}"
            drafts.append(BlockDraft(kind=kind, name=name, start_line=start, end_line=end))
        return drafts


def get_segmenter() -> Segmenter:
    return RuleSegmenter()
