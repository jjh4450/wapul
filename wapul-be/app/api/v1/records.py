# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2026 Hipster Timer Project Contributors

"""풀이 기록 API: 작성, 블럭 수정, 답 저장, 배치안, 그룹 공유"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, col, delete, select

from app.core.auth import CurrentUser, get_current_user
from app.db.session import get_db, get_db_transactional
from app.models.base import utc_now_naive
from app.models.study import Block, BlockKind, GroupMember, GroupRecord, Question, Record
from app.schemas.study import (
    AnswersUpdate,
    BlockIn,
    BlockOut,
    BlocksUpdate,
    LayoutOut,
    QuestionIn,
    QuestionOut,
    RecordCreate,
    RecordOut,
    RecordSummary,
    SharesUpdate,
    Unit,
)
from app.services.layouts import build_layouts

router = APIRouter(prefix="/records", tags=["Records"])


def display_name(user: CurrentUser) -> str:
    return user.name or user.email or user.sub


def _member_group_ids(db: Session, user_id: str) -> set[uuid.UUID]:
    return set(db.exec(select(GroupMember.group_id).where(GroupMember.user_id == user_id)).all())


def _shared_group_ids(db: Session, record_id: uuid.UUID) -> set[uuid.UUID]:
    return set(db.exec(select(GroupRecord.group_id).where(GroupRecord.record_id == record_id)).all())


def _get_readable(db: Session, record_id: uuid.UUID, user: CurrentUser) -> Record:
    """작성자이거나, 기록이 공유된 그룹의 멤버만 읽을 수 있다. 그 밖에는 존재 자체를 숨긴다."""
    record = db.get(Record, record_id)
    if record is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found")
    if record.owner_id != user.sub and not (_shared_group_ids(db, record_id) & _member_group_ids(db, user.sub)):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Record not found")
    return record


def _get_own(db: Session, record_id: uuid.UUID, user: CurrentUser) -> Record:
    record = _get_readable(db, record_id, user)
    if record.owner_id != user.sub:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the author can change this record")
    return record


def _blocks(db: Session, record_id: uuid.UUID) -> list[Block]:
    return list(db.exec(select(Block).where(Block.record_id == record_id).order_by(Block.position)).all())


def _questions(db: Session, record_id: uuid.UUID) -> list[Question]:
    return list(db.exec(select(Question).where(Question.record_id == record_id).order_by(Question.position)).all())


def _validate_units(code: str, units: list[Unit]) -> None:
    """문장은 코드 안에 있고, 순서대로 겹치지 않아야 한다"""
    line_lengths = [len(line) for line in code.split("\n")]

    def inside(point: list[int]) -> bool:
        line, col = point
        return 1 <= line <= len(line_lengths) and 0 <= col <= line_lengths[line - 1]

    previous_end = [1, 0]
    for unit in units:
        if not (inside(unit.start) and inside(unit.end)) or not previous_end <= unit.start < unit.end:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Units must be ordered spans inside the code")
        previous_end = unit.end


def _validate_blocks(unit_count: int, blocks: list[BlockIn]) -> list[BlockIn]:
    """문장 번호는 범위 안에 있고, 한 문장은 한 블럭에만 든다"""
    seen: set[int] = set()
    for block in blocks:
        for unit in block.units:
            if not 0 <= unit < unit_count:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unit {unit} is not in 0..{unit_count - 1}")
            if unit in seen:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unit {unit} is in more than one block")
            seen.add(unit)
        if block.title is not None and block.kind != BlockKind.LOGIC:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Only logic blocks have a title")
    return [b.model_copy(update={"units": sorted(b.units)}) for b in blocks]


def _validate_questions(block_count: int, questions: list[QuestionIn]) -> None:
    for question in questions:
        if question.block is not None and not 0 <= question.block < block_count:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, f"Question block {question.block} is not in 0..{block_count - 1}"
            )


def _known(kind: str, ids: list[uuid.UUID | None], existing: set[uuid.UUID]) -> None:
    """보낸 id는 이 기록의 것이고 한 번씩만 온다"""
    sent = [i for i in ids if i is not None]
    if len(sent) != len(set(sent)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{kind} id sent more than once")
    for i in sent:
        if i not in existing:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"{kind} {i} is not in this record")


def _save_blocks(db: Session, record: Record, blocks: list[BlockIn], questions: list[QuestionIn]) -> None:
    """블럭과 질문을 보낸 대로 맞춘다. id가 있는 것은 그 행을 고쳐 id가 그대로 남고, 없는 것은 새로 만들고,
    보내지 않은 것은 지운다. 질문과 남길 답은 브라우저가 정해 보낸다."""
    old_blocks = {b.id: b for b in _blocks(db, record.id)}
    old_questions = {q.id: q for q in _questions(db, record.id)}
    _known("Block", [b.id for b in blocks], set(old_blocks))
    _known("Question", [q.id for q in questions], set(old_questions))

    # 질문이 블럭을 가리키므로, 빠진 질문을 먼저 지우고 빠진 블럭은 남은 질문을 옮긴 뒤 지운다
    kept_questions = {q.id for q in questions}
    for q in old_questions.values():
        if q.id not in kept_questions:
            db.delete(q)
    db.flush()

    saved: list[Block] = []
    for i, b in enumerate(blocks):
        block = old_blocks[b.id] if b.id is not None else Block(record_id=record.id, position=i, kind=b.kind, units=[])
        block.position, block.kind, block.units, block.title = i, b.kind, b.units, b.title
        db.add(block)
        saved.append(block)
    db.flush()

    for i, q in enumerate(questions):
        question = (
            old_questions[q.id]
            if q.id is not None
            else Question(record_id=record.id, position=i, kind=q.kind, text=q.text)
        )
        question.block_id = None if q.block is None else saved[q.block].id
        question.position, question.kind, question.text, question.answer = i, q.kind, q.text, q.answer
        db.add(question)
    db.flush()

    kept_blocks = {b.id for b in blocks}
    for b in old_blocks.values():
        if b.id not in kept_blocks:
            db.delete(b)
    db.flush()


def _to_summary(record: Record) -> RecordSummary:
    return RecordSummary.model_validate(record, from_attributes=True)


def _to_out(db: Session, record: Record, user: CurrentUser) -> RecordOut:
    is_owner = record.owner_id == user.sub
    return RecordOut(
        **_to_summary(record).model_dump(),
        code=record.code,
        units=[Unit.model_validate(u) for u in record.units],
        is_owner=is_owner,
        group_ids=sorted(_shared_group_ids(db, record.id)) if is_owner else [],
        blocks=[BlockOut.model_validate(b, from_attributes=True) for b in _blocks(db, record.id)],
        questions=[
            QuestionOut(
                id=q.id,
                block_id=q.block_id,
                kind=q.kind,
                text=q.text,
                answer=q.answer,
            )
            for q in _questions(db, record.id)
        ],
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_record(
    body: RecordCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_transactional),
) -> RecordOut:
    """브라우저가 나눈 블럭과 만든 질문으로 기록을 만든다"""
    _validate_units(body.code, body.units)
    blocks = _validate_blocks(len(body.units), body.blocks)
    _validate_questions(len(blocks), body.questions)
    record = Record(
        owner_id=user.sub,
        owner_name=display_name(user),
        units=[u.model_dump() for u in body.units],
        **body.model_dump(exclude={"units", "blocks", "questions"}),
    )
    db.add(record)
    db.flush()
    _save_blocks(db, record, blocks, body.questions)
    return _to_out(db, record, user)


@router.get("")
def list_my_records(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[RecordSummary]:
    records = db.exec(select(Record).where(Record.owner_id == user.sub).order_by(col(Record.updated_at).desc())).all()
    return [_to_summary(r) for r in records]


@router.get("/{record_id}")
def get_record(
    record_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecordOut:
    return _to_out(db, _get_readable(db, record_id, user), user)


@router.put("/{record_id}/blocks")
def update_blocks(
    record_id: uuid.UUID,
    body: BlocksUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_transactional),
) -> RecordOut:
    record = _get_own(db, record_id, user)
    blocks = _validate_blocks(len(record.units), body.blocks)
    _validate_questions(len(blocks), body.questions)
    _save_blocks(db, record, blocks, body.questions)
    record.updated_at = utc_now_naive()
    db.add(record)
    return _to_out(db, record, user)


@router.patch("/{record_id}/answers", status_code=status.HTTP_204_NO_CONTENT)
def save_answers(
    record_id: uuid.UUID,
    body: AnswersUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_transactional),
) -> None:
    """답은 사용자가 쓴 그대로 저장한다 (판정·수정 없음)"""
    record = _get_own(db, record_id, user)
    questions = {q.id: q for q in _questions(db, record.id)}
    for item in body.answers:
        question = questions.get(item.question_id)
        if question is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Question {item.question_id} not found in this record")
        question.answer = item.answer
        db.add(question)
    record.updated_at = utc_now_naive()
    db.add(record)


@router.get("/{record_id}/layouts")
def get_layouts(
    record_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[LayoutOut]:
    record = _get_readable(db, record_id, user)
    layouts = build_layouts(record, _blocks(db, record.id), _questions(db, record.id))
    return [LayoutOut(id=lay.id, title=lay.title, markdown=lay.markdown) for lay in layouts]


@router.put("/{record_id}/groups")
def update_shares(
    record_id: uuid.UUID,
    body: SharesUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_transactional),
) -> list[uuid.UUID]:
    """기록을 공유할 그룹을 통째로 정한다. 내가 속한 그룹에만 공유할 수 있다."""
    record = _get_own(db, record_id, user)
    wanted = set(body.group_ids)
    if wanted - _member_group_ids(db, user.sub):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only share to groups you belong to")
    current = _shared_group_ids(db, record.id)
    db.exec(
        delete(GroupRecord).where(
            col(GroupRecord.record_id) == record.id, col(GroupRecord.group_id).in_(current - wanted)
        )
    )
    db.add_all(GroupRecord(group_id=g, record_id=record.id) for g in wanted - current)
    return sorted(wanted)


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(
    record_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_transactional),
) -> None:
    record = _get_own(db, record_id, user)
    db.exec(delete(Question).where(col(Question.record_id) == record.id))
    db.exec(delete(Block).where(col(Block.record_id) == record.id))
    db.exec(delete(GroupRecord).where(col(GroupRecord.record_id) == record.id))
    db.delete(record)
