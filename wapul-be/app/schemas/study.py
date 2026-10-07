# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2026 Hipster Timer Project Contributors

"""기록·그룹 API 요청/응답 모델"""

import uuid
from datetime import datetime

from pydantic import Field

from app.core.base_model import CustomModel
from app.models.study import BlockKind, Language, QuestionKind


class Unit(CustomModel):
    """문장 하나 (wapul-seg의 segment 결과). 위치는 [줄, 칸]: 줄은 1부터, 칸은 0부터 세는 글자 수, end는
    포함하지 않는다. 표시는 저장만 하고, 브라우저가 블럭을 고칠 때 질문을 다시 만드는 데 쓴다."""

    # tuple이 아니라 list로 둔다: openapi-fetch의 응답 타입이 튜플을 배열로 펴서 프론트 타입이 어긋난다
    start: list[int] = Field(min_length=2, max_length=2)
    end: list[int] = Field(min_length=2, max_length=2)
    condition: bool  # 분기 머리, 비교 연산, 삼항식
    loop: bool  # 반복문 머리
    recursion: bool  # 감싼 함수를 다시 부름


class BlockIn(CustomModel):
    kind: BlockKind
    units: list[int] = Field(min_length=1)  # 기록의 units 번호


class QuestionIn(CustomModel):
    """질문은 브라우저가 블럭을 보고 만든다. 블럭을 고칠 때는 그대로 남은 질문의 답을 실어 보낸다."""

    kind: QuestionKind
    text: str = Field(min_length=1, max_length=500)
    block: int | None = None  # 함께 보낸 blocks의 번호, 기록 단위 질문이면 없음
    answer: str = Field(max_length=10_000)  # 새 질문이면 빈 문자열


class RecordCreate(CustomModel):
    """분할과 질문은 브라우저가 하고(wapul-seg), 그 결과를 코드와 함께 보낸다"""

    problem: str = Field(min_length=1, max_length=500)
    key_idea: str = Field(min_length=1, max_length=500)
    code: str = Field(min_length=1, max_length=100_000)  # normalize(code)
    language: Language
    units: list[Unit] = Field(min_length=1, max_length=20_000)
    blocks: list[BlockIn] = Field(min_length=1)
    questions: list[QuestionIn] = Field(min_length=1)


class BlocksUpdate(CustomModel):
    blocks: list[BlockIn] = Field(min_length=1)
    questions: list[QuestionIn] = Field(min_length=1)


class AnswerIn(CustomModel):
    question_id: uuid.UUID
    answer: str = Field(max_length=10_000)


class AnswersUpdate(CustomModel):
    answers: list[AnswerIn]


class SharesUpdate(CustomModel):
    group_ids: list[uuid.UUID]


class BlockOut(CustomModel):
    id: uuid.UUID
    kind: BlockKind
    units: list[int]


class QuestionOut(CustomModel):
    id: uuid.UUID
    block_id: uuid.UUID | None
    kind: QuestionKind
    text: str
    answer: str


class RecordSummary(CustomModel):
    id: uuid.UUID
    problem: str
    key_idea: str
    language: Language
    owner_name: str
    created_at: datetime
    updated_at: datetime


class RecordOut(RecordSummary):
    code: str
    units: list[Unit]
    is_owner: bool
    group_ids: list[uuid.UUID]  # 작성자에게만 채워진다
    blocks: list[BlockOut]
    questions: list[QuestionOut]


class LayoutOut(CustomModel):
    id: str
    title: str
    markdown: str


class GroupCreate(CustomModel):
    name: str = Field(min_length=1, max_length=100)


class GroupJoin(CustomModel):
    invite_code: str = Field(min_length=1, max_length=32)


class GroupOut(CustomModel):
    id: uuid.UUID
    name: str
    invite_code: str
    role: str
    member_count: int


class MemberOut(CustomModel):
    display_name: str
    role: str


class SharedRecordOut(RecordSummary):
    shared_at: datetime


class GroupDetail(GroupOut):
    members: list[MemberOut]
    records: list[SharedRecordOut]
