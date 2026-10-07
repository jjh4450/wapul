# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2026 Hipster Timer Project Contributors

"""풀이 기록(Record)과 그룹 도메인 모델"""

import uuid
from enum import StrEnum

from pydantic import NaiveDatetime
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.base import TimestampMixin, UUIDBase, utc_now_naive


class Language(StrEnum):
    """분할 모델(wapul-seg)이 지원하는 언어"""

    CPP = "cpp"
    JAVA = "java"
    PYTHON = "python"
    RUST = "rust"
    C = "c"
    KOTLIN = "kotlin"
    JAVASCRIPT = "javascript"
    GO = "go"
    CSHARP = "csharp"
    SWIFT = "swift"
    RUBY = "ruby"
    SCALA = "scala"
    PHP = "php"


class BlockKind(StrEnum):
    INPUT = "input"
    OUTPUT = "output"
    LOGIC = "logic"


class QuestionKind(StrEnum):
    PROBLEM = "problem"
    LOGIC = "logic"
    BOUNDARY = "boundary"
    INPUT_MEANING = "input_meaning"
    INPUT_CONDITION = "input_condition"
    OUTPUT_MEANING = "output_meaning"
    OUTPUT_FORMAT = "output_format"
    REVISION = "revision"
    VARYING = "varying"


class Record(UUIDBase, TimestampMixin, table=True):
    __tablename__ = "records"

    owner_id: str = Field(index=True)
    owner_name: str
    problem: str  # 문제 제목이나 링크
    key_idea: str  # 코드보다 먼저 쓰는 핵심 아이디어 한 줄
    code: str  # 분할 모델의 normalize를 거친 코드. 문장 위치는 이 문자열 기준이다
    language: Language
    initially_wrong: bool = False
    # 코드의 모든 문장: schemas.study.Unit을 dict로
    units: list[dict] = Field(sa_column=Column(JSON, nullable=False))


class Block(UUIDBase, table=True):
    __tablename__ = "blocks"

    record_id: uuid.UUID = Field(foreign_key="records.id", ondelete="CASCADE", index=True)
    position: int
    kind: BlockKind
    # 이 블럭에 든 문장의 Record.units 번호. 떨어져 있을 수 있다
    units: list[int] = Field(sa_column=Column(JSON, nullable=False))


class Question(UUIDBase, table=True):
    __tablename__ = "questions"

    record_id: uuid.UUID = Field(foreign_key="records.id", ondelete="CASCADE", index=True)
    block_id: uuid.UUID | None = Field(default=None, foreign_key="blocks.id", ondelete="CASCADE")
    position: int
    kind: QuestionKind
    # 생성 시점의 문구를 저장해 문구 은행이 바뀌어도 이미 쓴 기록의 질문은 그대로 남는다
    text: str
    answer: str = ""


class StudyGroup(UUIDBase, TimestampMixin, table=True):
    __tablename__ = "study_groups"

    name: str
    invite_code: str = Field(unique=True, index=True)
    owner_id: str


class GroupMember(SQLModel, table=True):
    __tablename__ = "group_members"

    group_id: uuid.UUID = Field(foreign_key="study_groups.id", ondelete="CASCADE", primary_key=True)
    user_id: str = Field(primary_key=True, index=True)
    display_name: str
    role: str  # "owner" | "member"
    joined_at: NaiveDatetime = Field(default_factory=utc_now_naive)


class GroupRecord(SQLModel, table=True):
    __tablename__ = "group_records"

    group_id: uuid.UUID = Field(foreign_key="study_groups.id", ondelete="CASCADE", primary_key=True)
    record_id: uuid.UUID = Field(foreign_key="records.id", ondelete="CASCADE", primary_key=True)
    shared_at: NaiveDatetime = Field(default_factory=utc_now_naive)
