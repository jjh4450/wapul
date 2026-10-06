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
from app.models.study import Block, GroupMember, GroupRecord, Question, QuestionKind, Record
from app.schemas.study import (
    AnswersUpdate,
    BlockIn,
    BlockOut,
    BlocksUpdate,
    LayoutOut,
    QuestionOut,
    RecordCreate,
    RecordOut,
    RecordSummary,
    SharesUpdate,
)
from app.services.analysis import analyze
from app.services.layouts import build_layouts
from app.services.questions import EXAMPLES, BlockInfo, build_questions
from app.services.segmenter import get_segmenter

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


def _validate_blocks(code: str, blocks: list[BlockIn]) -> list[BlockIn]:
    line_count = len(code.splitlines())
    ordered = sorted(blocks, key=lambda b: b.start_line)
    previous_end = 0
    for block in ordered:
        if block.start_line > block.end_line or block.end_line > line_count:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"Block '{block.name}' must cover lines within 1..{line_count}",
            )
        if block.start_line <= previous_end:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Block '{block.name}' overlaps another block")
        previous_end = block.end_line
    return ordered


def _replace_blocks(db: Session, record: Record, blocks: list[BlockIn]) -> None:
    """블럭을 바꾸고 질문을 다시 만든다. 같은 자리에 남은 질문의 답은 옮겨 둔다."""
    old_blocks = {b.id: (b.kind, b.start_line, b.end_line) for b in _blocks(db, record.id)}

    def answer_key(kind: QuestionKind, block_key: tuple | None, text: str) -> tuple:
        # 기록마다 바뀌는 질문은 문구까지 같아야 같은 질문으로 본다
        return (kind, block_key, text if kind == QuestionKind.VARYING else None)

    kept = {
        answer_key(q.kind, old_blocks.get(q.block_id), q.text): q.answer for q in _questions(db, record.id) if q.answer
    }

    db.exec(delete(Question).where(col(Question.record_id) == record.id))
    db.exec(delete(Block).where(col(Block.record_id) == record.id))

    new_blocks = [
        Block(
            record_id=record.id,
            position=i,
            kind=b.kind,
            name=b.name,
            start_line=b.start_line,
            end_line=b.end_line,
        )
        for i, b in enumerate(blocks)
    ]
    db.add_all(new_blocks)

    infos = [BlockInfo(b.id, b.kind, b.start_line, b.end_line) for b in new_blocks]
    block_keys = {b.id: (b.kind, b.start_line, b.end_line) for b in new_blocks}
    drafts = build_questions(str(record.id), infos, analyze(record.code, record.language), record.initially_wrong)
    db.add_all(
        Question(
            record_id=record.id,
            block_id=d.block_id,
            position=i,
            kind=d.kind,
            text=d.text,
            answer=kept.get(answer_key(d.kind, block_keys.get(d.block_id), d.text), ""),
        )
        for i, d in enumerate(drafts)
    )
    db.flush()


def _to_summary(record: Record) -> RecordSummary:
    return RecordSummary.model_validate(record, from_attributes=True)


def _to_out(db: Session, record: Record, user: CurrentUser) -> RecordOut:
    is_owner = record.owner_id == user.sub
    return RecordOut(
        **_to_summary(record).model_dump(),
        code=record.code,
        initially_wrong=record.initially_wrong,
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
                examples=EXAMPLES.get(q.kind, []),
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
    """기록을 만들고 코드를 블럭으로 나눈 제안과 질문을 함께 돌려준다"""
    record = Record(owner_id=user.sub, owner_name=display_name(user), **body.model_dump())
    db.add(record)
    db.flush()
    drafts = get_segmenter().segment(record.code, record.language)
    blocks = [BlockIn(kind=d.kind, name=d.name, start_line=d.start_line, end_line=d.end_line) for d in drafts]
    _replace_blocks(db, record, blocks)
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
    _replace_blocks(db, record, _validate_blocks(record.code, body.blocks))
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
