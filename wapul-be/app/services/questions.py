# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2026 Hipster Timer Project Contributors

"""질문 문구 은행과 기록별 질문 생성

- 같은 뜻의 문구를 여러 개 두고 하나를 무작위로 고른다. 모든 문구는 목적, 원리, 보장되는 성질을 향한다.
- 예제 답은 다른 문제에 대한 답이다. 내용은 베낄 수 없고 형식만 참고하게 된다.
- 질문 수는 코드 복잡도나 사용 횟수로 줄이지 않는다.
"""

import random
import uuid
from dataclasses import dataclass

from app.models.study import BlockKind, QuestionKind
from app.services.analysis import CodeFacts

PHRASES: dict[QuestionKind, list[str]] = {
    QuestionKind.PROBLEM: [
        "어떤 성질을 발견해서 이 방법을 쓰게 됐나요?",
        "문제의 어떤 성질이 이 방법을 쓸 수 있게 해 주었나요?",
        "이 방법을 고르게 만든 문제의 성질은 무엇이었나요?",
    ],
    QuestionKind.LOGIC: [
        "이 부분이 끝나면 무엇이 보장되고, 그게 왜 성립하나요?",
        "이 부분을 지나고 나면 무엇이 성립하고, 왜 그런가요?",
        "이 부분이 끝난 뒤 항상 참인 것은 무엇이고, 그 이유는 무엇인가요?",
    ],
    QuestionKind.BOUNDARY: [
        "이 설명이 통하지 않는 입력은 뭘까요?",
        "어떤 입력에서 이 설명이 깨질까요?",
        "이 설명이 맞지 않게 되는 입력은 무엇일까요?",
    ],
    QuestionKind.INPUT_MEANING: [
        "입력을 담은 변수와 자료구조는 각각 무엇을 나타내나요?",
        "입력을 받은 각 변수와 자료구조가 뜻하는 것은 무엇인가요?",
    ],
    QuestionKind.INPUT_CONDITION: [
        "입력 조건(범위, 형식, 끝나는 조건) 중 이 코드가 기대는 것은 무엇인가요?",
        "이 코드가 믿고 있는 입력 조건(범위, 형식, 끝나는 조건)은 무엇인가요?",
    ],
    QuestionKind.OUTPUT_MEANING: [
        "출력하는 값은 앞에서 만든 결과의 무엇에 해당하나요?",
        "출력하는 값은 앞에서 구한 결과 중 무엇인가요?",
    ],
    QuestionKind.OUTPUT_FORMAT: [
        "출력 형식이나 정밀도에서 지켜야 했던 조건은 무엇인가요?",
        "출력할 때 형식이나 정밀도에서 맞춰야 했던 것은 무엇인가요?",
    ],
    QuestionKind.REVISION: [
        "처음 제출에서 무엇이 달라졌고, 왜 그게 필요했나요?",
        "처음 제출과 비교해 무엇을 바꿨고, 그 변경이 왜 필요했나요?",
    ],
}

# 기록마다 바뀌는 질문의 세 갈래
VARYING_PERSPECTIVE = [
    "이 블럭의 결과를 다음 블럭은 어떻게 쓰나요?",
    "다음 블럭은 이 블럭이 만든 결과에서 무엇을 가져다 쓰나요?",
]
VARYING_STRUCTURE = {
    "recursion": [
        "재귀가 멈추는 조건과 그 이유는 무엇인가요?",
        "이 재귀가 반드시 끝나는 이유는 무엇인가요?",
    ],
    "loop": [
        "반복이 한 바퀴 돌 때마다 유지되는 성질은 무엇인가요?",
        "이 반복문이 끝났을 때 무엇이 성립하나요?",
    ],
}
VARYING_GENERAL = [
    "만약 입력 크기가 지금 제한의 10배라면 이 풀이는 어떻게 될까요?",
    "만약 같은 값이 여러 번 들어온다면 이 풀이는 어떻게 될까요?",
    "만약 입력이 하나뿐이라면 이 풀이는 어떻게 될까요?",
]

EXAMPLES: dict[QuestionKind, list[str]] = {
    QuestionKind.PROBLEM: [
        "N이 100만이라 O(n²) 정렬은 시간 안에 못 끝난다. 비교 정렬은 O(n log n)보다 빠를 수 없어서 병합 정렬을 썼다.",
        "퀸은 한 줄에 하나만 놓인다. 그래서 줄마다 하나씩 놓아 보고, 이미 막힌 칸이면 더 내려가지 않고 되돌아가는 백트래킹을 썼다.",
        "무게 w까지 담을 때의 최대 가치는 앞의 물건들만 보고 정해지고, 같은 부분 문제가 여러 번 나온다. 그래서 DP로 한 번씩만 계산했다.",
        "가장 일찍 끝나는 회의를 먼저 고르면 남는 시간이 가장 넓다. 이 선택이 최적해를 망치지 않아서 DP 없이 그리디로 충분했다.",
        "N번째 값은 바로 앞 두 값만 있으면 정해진다. 재귀는 같은 값을 여러 번 계산하고 깊이도 깊어서, 두 값만 들고 가는 반복문으로 썼다.",
    ],
    QuestionKind.LOGIC: [
        "이 반복이 끝나면 dp[w]에는 지금까지 본 물건으로 무게 w 이하를 담을 때의 최대 가치가 들어 있다. 물건마다 넣거나 빼는 두 경우뿐이고, 둘 다 이미 최댓값으로 정해진 칸에서 오기 때문이다.",
        "정렬이 끝나면 회의가 끝나는 시간 순서로 놓인다. 그래서 앞에서부터 보면 항상 가장 일찍 끝나는 회의를 먼저 만난다.",
        "이 부분이 끝나면 cur와 prev에는 F(i)와 F(i-1)이 들어 있다. 매번 두 값을 한 칸씩 밀어 다음 값을 만들기 때문이다.",
    ],
    QuestionKind.BOUNDARY: [
        "물건 무게가 배낭 용량보다 큰 경우. 이때는 넣는 경우를 아예 따지면 안 된다.",
        "끝나는 시간이 같은 회의가 여러 개일 때. 시작 시간까지 함께 정렬하지 않으면 길이가 0인 회의를 놓친다.",
        "N이 0이나 1일 때. 반복문이 한 번도 돌지 않아서 초기값이 그대로 답이 된다.",
    ],
    QuestionKind.INPUT_MEANING: [
        "w[i], v[i]는 i번째 물건의 무게와 가치다. K는 배낭에 담을 수 있는 최대 무게다.",
        "meetings는 (끝나는 시간, 시작 시간) 쌍의 목록이다. 바로 정렬 기준으로 쓰려고 끝나는 시간을 앞에 뒀다.",
    ],
    QuestionKind.INPUT_CONDITION: [
        "N이 최대 100만이라 한 줄씩 받으면 느려서 한 번에 읽었다.",
        "입력 끝에 0 0이 오면 끝난다는 조건에 기대고 있다. 이 줄이 없으면 반복이 끝나지 않는다.",
        "무게와 가치가 모두 양수라는 조건에 기대서 음수는 따로 처리하지 않았다.",
    ],
    QuestionKind.OUTPUT_MEANING: [
        "dp[K]는 모든 물건을 본 뒤 무게 K 이하로 얻는 최대 가치라서 그대로 출력한다.",
        "count는 지금까지 고른 회의 수라서 반복이 끝난 뒤의 값이 곧 답이다.",
    ],
    QuestionKind.OUTPUT_FORMAT: [
        "소수점 아래 6자리까지 출력해야 해서 형식을 고정했다.",
        "답이 커서 1,000,000,007로 나눈 나머지를 출력해야 했다.",
        "한 줄에 하나씩 출력해야 해서 결과를 모아 줄바꿈으로 이어 한 번에 출력했다.",
    ],
    QuestionKind.REVISION: [
        "처음엔 끝나는 시간만으로 정렬해서 길이가 0인 회의가 순서에 따라 빠졌다. 시작 시간도 함께 정렬해야 같은 시간에 끝나는 회의를 모두 셀 수 있었다.",
        "처음엔 int로 합을 구해서 넘쳤다. 최댓값이 10^5 × 10^9라 64비트 정수가 필요했다.",
        "처음엔 재귀로 풀어서 깊이 제한에 걸렸다. 반복문으로 바꿔 스택을 쓰지 않게 했다.",
    ],
    QuestionKind.VARYING: [
        "다음 블럭은 정렬된 회의 목록을 앞에서부터 한 번만 훑는다. 정렬 덕분에 지금 고를 수 있는 회의 중 가장 일찍 끝나는 것이 항상 먼저 나온다.",
        "더 놓을 퀸이 없을 때(row == N) 멈춘다. 호출할 때마다 row가 1씩 커지므로 언젠가 반드시 N에 닿는다.",
        "N이 10배면 O(n²) 정렬은 100배 느려져서 시간 제한을 넘는다. O(n log n)이면 10배를 조금 넘게만 늘어난다.",
    ],
}


@dataclass(frozen=True)
class BlockInfo:
    id: uuid.UUID
    kind: BlockKind
    start_line: int
    end_line: int

    def touches(self, lines: set[int]) -> bool:
        return any(self.start_line <= line <= self.end_line for line in lines)


@dataclass(frozen=True)
class QuestionDraft:
    kind: QuestionKind
    text: str
    block_id: uuid.UUID | None = None


_BLOCK_KINDS: dict[BlockKind, list[QuestionKind]] = {
    BlockKind.INPUT: [QuestionKind.INPUT_MEANING, QuestionKind.INPUT_CONDITION],
    BlockKind.OUTPUT: [QuestionKind.OUTPUT_MEANING, QuestionKind.OUTPUT_FORMAT],
    BlockKind.LOGIC: [QuestionKind.LOGIC],
}


def _pick_varying(rng: random.Random, blocks: list[BlockInfo], facts: CodeFacts) -> QuestionDraft:
    """세 갈래 중 이 코드에 붙을 수 있는 갈래에서 하나를 뽑는다"""
    options: list[QuestionDraft] = []

    # 관점 바꾸기: 뒤에 블럭이 이어지는 로직 블럭
    for block in blocks[:-1]:
        if block.kind == BlockKind.LOGIC:
            options.append(QuestionDraft(QuestionKind.VARYING, rng.choice(VARYING_PERSPECTIVE), block.id))

    # 구조별: 코드에 그 구조가 있을 때만
    for structure, lines in (("recursion", facts.recursion_lines), ("loop", facts.loop_lines)):
        for block in blocks:
            if block.touches(lines):
                options.append(QuestionDraft(QuestionKind.VARYING, rng.choice(VARYING_STRUCTURE[structure]), block.id))

    # 일반 질문 줄기: 언제나 붙을 수 있다
    options.append(QuestionDraft(QuestionKind.VARYING, rng.choice(VARYING_GENERAL)))
    return rng.choice(options)


def build_questions(seed: str, blocks: list[BlockInfo], facts: CodeFacts, initially_wrong: bool) -> list[QuestionDraft]:
    """기록에 붙을 질문을 표시 순서대로 만든다. 같은 seed면 같은 문구가 나온다."""
    rng = random.Random(seed)
    varying = _pick_varying(rng, blocks, facts)

    drafts = [QuestionDraft(QuestionKind.PROBLEM, rng.choice(PHRASES[QuestionKind.PROBLEM]))]
    for block in blocks:
        for kind in _BLOCK_KINDS[block.kind]:
            drafts.append(QuestionDraft(kind, rng.choice(PHRASES[kind]), block.id))
        if block.touches(facts.condition_lines):
            drafts.append(QuestionDraft(QuestionKind.BOUNDARY, rng.choice(PHRASES[QuestionKind.BOUNDARY]), block.id))
        if varying.block_id == block.id:
            drafts.append(varying)
    if varying.block_id is None:
        drafts.append(varying)
    if initially_wrong:
        drafts.append(QuestionDraft(QuestionKind.REVISION, rng.choice(PHRASES[QuestionKind.REVISION])))
    return drafts
