# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2026 Hipster Timer Project Contributors

"""Claude API로 코드를 블럭으로 나누는 분할기

코드를 문장 단위([uN])로 보여 주고, 문장 번호를 입력·출력·해당 없음·로직 블럭 n개로 묶게 한다.
위치는 AST에서 오므로 블럭 경계는 항상 문장 경계에 맞는다. 결과는 줄 단위 BlockDraft로 바꾼다.
API 호출이 실패하면 규칙 분할기로 대신한다.
"""

import logging

from pydantic import BaseModel, ValidationError

from app.core.llm import LLMError, parse
from app.models.study import BlockKind, Language
from app.services.segmenter import BlockDraft, RuleSegmenter
from app.services.units import Unit, show, units

logger = logging.getLogger(__name__)

# 학습 데이터 라벨링에 쓴 프롬프트와 같다. 바꾸면 라벨 기준도 함께 바뀐다.
SYSTEM = """\
너는 알고리즘 문제 풀이 코드를 블럭으로 나누는 라벨러다. 코드는 번호 붙은 문장 [uN]으로 주어진다.
문장마다 input, output, none 중 하나에 넣거나, 로직 블럭 중 하나에 넣는다. 블럭에 이름은 붙이지 않는다.

목적:
이 블럭은 PS 공부 기록 사이트에서 쓰인다. 사용자는 자기 풀이 코드를 넣고, 로직 블럭마다
"이 부분이 끝나면 무엇이 보장되고, 그게 왜 성립하나요?"라는 질문에 답하며 풀이를 설명한다.
조건이나 비교가 있는 블럭에는 "이 설명이 통하지 않는 입력은 뭘까요?"가 더 붙는다.
그래서 로직 블럭은 끝나는 지점에서 새로 보장되는 중간 상태가 하나 있는 단위여야 한다.

순서:
1. 먼저 로직을 번호 붙은 절차로 쓴다(procedure). 한 단계는 끝나면 보장되는 중간 상태가 하나인 일이다.
2. 그다음 단계마다 해당 문장을 배정한다. 단계 하나가 로직 블럭 하나다. procedure와 logic의 개수와 순서가 같아야 한다.

종류 규칙:
1. input: 입력을 읽는 문장, 입력을 담을 변수의 선언, 읽은 값을 그대로 담는 문장(배열·맵·큐에 넣기 포함), 입출력 준비(BufferedReader 생성, ios::sync_with_stdio, cin.tie, cout.tie, sys.stdin 대입 등).
2. output: 풀이의 최종 답을 밖으로 내보내는 문장만이다. 최종 답의 출력(print, cout, System.out, 모아 둔 StringBuilder 출력), 풀이 함수가 최종 답을 돌려주는 return, flush·close,
   그리고 최종 답을 문제가 정한 형식으로 바꾸는 처리(소수점 자릿수, 빈 결과일 때 정해진 문구)가 여기에 든다.
   보조 함수가 중간값을 돌려주는 return(예: find가 루트를 돌려줌)은 output이 아니라 logic이다.
3. logic: 그 밖의 계산. 읽은 값으로 그래프·인접 리스트를 만드는 문장, 초기화처럼 로직의 일부인 문장은 입력 근처에 있어도 logic이다.
   명령·쿼리마다 상태를 보고 다른 계산 결과를 내는 분기는 안의 출력 문장까지 logic이다(예: 큐 명령 처리에서 size·empty·front 분기).
   계산하면서 출력하는 문장(bw.write(q.poll()), print(stack.pop()))과, 반복 중에 답을 모으는 문장(반복문 안의 sb.append(답))도 logic이다.
   모은 답을 마지막에 한 번에 내보내는 문장만 output이다.
4. 반복문·조건문 머리는 그 몸체가 하는 일을 따른다. 몸체가 입력만 읽으면 input, 최종 답을 내보내기만 하면 output, 그 밖에는 logic. 재귀·탐색의 종료 조건문은 안에서 출력하더라도 logic이다.
5. none: #include, import, using, 클래스·함수 머리, 빈 return처럼 어느 일에도 속하지 않는 문장.
   여러 테스트 케이스를 도는 바깥 반복문의 머리도 none이다.
   호출되지 않는 함수의 문장과 쓰이지 않는 변수도 none이다.

로직 블럭 규칙:
1. 잘게 나눈다. 함수나 풀이 전체의 결과 하나로 묶지 말고, 중간 상태가 새로 보장되는 지점마다 끊는다.
   - 시작 상태를 만드는 준비와, 그 상태를 이어 가는 반복은 다른 블럭이다.
     예: BFS는 "시작점이 큐에 들어가고 방문 처리됐다"와 "큐에서 꺼낸 칸의 거리는 시작점에서의 최단 거리다"로 나눈다.
   - 재귀 함수는 기저 조건과 재귀 단계를 나눈다.
   - 따로 말할 보장이 없는 부분은 옆 블럭과 합친다. 같은 보장을 만드는 대칭 연산(오른쪽·아래로 더하기)은 한 블럭이다.
2. 겹친 반복문·조건문은 바깥 구조로만 묶지 않는다. 안쪽 반복문이나 조건문이 따로 말할 보장을 만들면 다른 블럭이다.
   - 반복 순서와 현재 상태 꺼내기 / 종료·경계·기저 처리 / 다음 상태로 전파·점화식 / 시도와 실패 시 되돌리기는 서로 다른 블럭이다.
   - 반복을 끊거나 건너뛰는 조건(break, continue, 반복 안의 return)은 자기 블럭이다.
   - 기저값이 점화식 반복문 안의 조건 분기로 들어 있어도 기저 분기와 점화식은 나눈다.
3. 단순한 선언과 0·빈 값 대입(int ans = 0, vector<int> v)은 그 값을 쓰는 로직 블럭에 넣는다. 그래서 블럭의 문장이 떨어져 있어도 된다.
   말할 수 있는 상태를 만드는 준비(시작점 넣기, 기저값 채우기)는 규칙 1에 따라 자기 블럭이 된다.
4. 블럭마다 guarantee에 그 블럭이 끝나면 보장되는 중간 상태를 한국어 한 문장으로 적는다. 전체 결과만 말하는 문장은 마지막 블럭에만 쓴다.
   procedure와 guarantee는 검토자가 경계를 확인하는 데만 쓴다.
5. 블럭은 절차 순서대로 적는다.

모든 문장 번호는 input, output, none, 로직 블럭들 중 정확히 한 곳에 한 번만 들어가야 한다.
"""


class LogicBlock(BaseModel):
    units: list[int]
    guarantee: str  # 경계를 정하는 데만 쓰고 사용자에게 보여 주지 않는다


class Segmentation(BaseModel):
    procedure: list[str]  # guarantee와 같다
    input: list[int]
    output: list[int]
    logic: list[LogicBlock]
    none: list[int]


def unit_kinds(seg: Segmentation, n: int) -> list[str]:
    """단위마다 input, output, none, logic<블럭 번호>. 모든 단위가 정확히 한 번 들어 있지 않으면 ValueError"""
    groups = [("input", seg.input), ("output", seg.output), ("none", seg.none)]
    groups += [(f"logic{b}", block.units) for b, block in enumerate(seg.logic, 1)]
    owner: dict[int, str] = {}
    for kind, members in groups:
        for u in members:
            if u in owner or not 1 <= u <= n:
                raise ValueError(f"unit {u} is out of range or listed twice")
            owner[u] = kind
    if len(owner) != n:
        raise ValueError(f"units missing: {sorted(set(range(1, n + 1)) - set(owner))}")
    return [owner[u] for u in range(1, n + 1)]


def to_drafts(us: list[Unit], kinds: list[str]) -> list[BlockDraft]:
    """단위 라벨을 줄 단위 블럭으로 바꾼다

    한 줄에 단위가 여럿이면 먼저 나온 단위를 따른다. none 줄은 블럭에 넣지 않는다.
    괄호뿐인 줄처럼 단위가 없는 줄은 앞뒤가 같은 블럭이면 그 블럭에 넣는다.
    떨어져 있는 로직 블럭은 같은 이름("로직 n")의 블럭 여러 개가 된다.
    """
    line_kind: dict[int, str] = {}
    for u, kind in zip(us, kinds, strict=True):
        for line in range(u.start[0], u.end[0] + 1):
            line_kind.setdefault(line, kind)

    # 로직 번호는 코드에서 처음 나오는 순서로 다시 매긴다
    order: dict[str, int] = {}
    for line in sorted(line_kind):
        if line_kind[line].startswith("logic"):
            order.setdefault(line_kind[line], len(order) + 1)

    runs: list[list] = []  # [kind, start, end]
    for line in sorted(line_kind):
        kind = line_kind[line]
        if kind == "none":
            continue
        if (
            runs
            and runs[-1][0] == kind
            and not any(line_kind.get(n) not in (None, kind) for n in range(runs[-1][2] + 1, line))
        ):
            runs[-1][2] = line
        else:
            runs.append([kind, line, line])

    drafts = []
    for kind, start, end in runs:
        if kind == "input":
            drafts.append(BlockDraft(kind=BlockKind.INPUT, name="입력 받기", start_line=start, end_line=end))
        elif kind == "output":
            drafts.append(BlockDraft(kind=BlockKind.OUTPUT, name="결과 출력", start_line=start, end_line=end))
        else:
            name = f"로직 {order[kind]}"
            drafts.append(BlockDraft(kind=BlockKind.LOGIC, name=name, start_line=start, end_line=end))
    return drafts


class LLMSegmenter:
    def __init__(self, client=None) -> None:
        self._client = client  # 테스트에서 가짜 클라이언트를 넣는다

    def segment(self, code: str, language: Language) -> list[BlockDraft]:
        us = units(code, language)
        if not us:
            return RuleSegmenter().segment(code, language)
        try:
            seg = parse(SYSTEM, f"언어: {language}\n\n{show(code, us)}", Segmentation, self._client)
            if any(not block.units for block in seg.logic) or len(seg.procedure) != len(seg.logic):
                raise ValueError("procedure and logic blocks do not line up")
            drafts = to_drafts(us, unit_kinds(seg, len(us)))
        except (LLMError, ValidationError, ValueError) as e:
            logger.warning("LLM segmentation failed, falling back to rules: %s", e)
            return RuleSegmenter().segment(code, language)
        return drafts or RuleSegmenter().segment(code, language)
