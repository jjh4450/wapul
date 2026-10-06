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


class RecordCreate(CustomModel):
    problem: str = Field(min_length=1, max_length=500)
    key_idea: str = Field(min_length=1, max_length=500)
    code: str = Field(min_length=1, max_length=100_000)
    language: Language
    initially_wrong: bool = False


class BlockIn(CustomModel):
    kind: BlockKind
    name: str = Field(min_length=1, max_length=100)
    start_line: int = Field(ge=1)
    end_line: int = Field(ge=1)


class BlocksUpdate(CustomModel):
    blocks: list[BlockIn] = Field(min_length=1)


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
    name: str
    start_line: int
    end_line: int


class QuestionOut(CustomModel):
    id: uuid.UUID
    block_id: uuid.UUID | None
    kind: QuestionKind
    text: str
    answer: str
    examples: list[str]  # 다른 문제에 대한 예제 답 (답 칸의 회색 안내문)


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
    initially_wrong: bool
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
