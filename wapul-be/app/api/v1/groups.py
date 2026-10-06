# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2026 Hipster Timer Project Contributors

"""그룹 API: 만들기, 초대 코드로 가입, 그룹 안에 공유된 기록 조회"""

import secrets
import string
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, col, func, select

from app.api.v1.records import display_name
from app.core.auth import CurrentUser, get_current_user
from app.db.session import get_db, get_db_transactional
from app.models.study import GroupMember, GroupRecord, Record, StudyGroup
from app.schemas.study import (
    GroupCreate,
    GroupDetail,
    GroupJoin,
    GroupOut,
    MemberOut,
    RecordSummary,
    SharedRecordOut,
)

router = APIRouter(prefix="/groups", tags=["Groups"])

# 헷갈리는 글자(0/O, 1/I)는 뺀다
_CODE_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1I")


def _new_invite_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))
        if db.exec(select(StudyGroup).where(StudyGroup.invite_code == code)).first() is None:
            return code


def _to_out(db: Session, group: StudyGroup, role: str) -> GroupOut:
    count = db.exec(select(func.count()).select_from(GroupMember).where(GroupMember.group_id == group.id)).one()
    return GroupOut(id=group.id, name=group.name, invite_code=group.invite_code, role=role, member_count=count)


def _membership(db: Session, group_id: uuid.UUID, user: CurrentUser) -> GroupMember:
    member = db.get(GroupMember, (group_id, user.sub))
    if member is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Group not found")
    return member


@router.post("", status_code=status.HTTP_201_CREATED)
def create_group(
    body: GroupCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_transactional),
) -> GroupOut:
    group = StudyGroup(name=body.name, invite_code=_new_invite_code(db), owner_id=user.sub)
    db.add(group)
    db.flush()
    db.add(GroupMember(group_id=group.id, user_id=user.sub, display_name=display_name(user), role="owner"))
    db.flush()
    return _to_out(db, group, "owner")


@router.get("")
def list_my_groups(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[GroupOut]:
    rows = db.exec(
        select(StudyGroup, GroupMember.role)
        .join(GroupMember, col(GroupMember.group_id) == StudyGroup.id)
        .where(GroupMember.user_id == user.sub)
        .order_by(col(GroupMember.joined_at).desc())
    ).all()
    return [_to_out(db, group, role) for group, role in rows]


@router.post("/join")
def join_group(
    body: GroupJoin,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db_transactional),
) -> GroupOut:
    code = body.invite_code.strip().upper()
    group = db.exec(select(StudyGroup).where(StudyGroup.invite_code == code)).first()
    if group is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invalid invite code")
    member = db.get(GroupMember, (group.id, user.sub))
    if member is None:
        member = GroupMember(group_id=group.id, user_id=user.sub, display_name=display_name(user), role="member")
        db.add(member)
        db.flush()
    return _to_out(db, group, member.role)


@router.get("/{group_id}")
def get_group(
    group_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GroupDetail:
    member = _membership(db, group_id, user)
    group = db.get(StudyGroup, group_id)
    members = db.exec(
        select(GroupMember).where(GroupMember.group_id == group_id).order_by(col(GroupMember.joined_at))
    ).all()
    shared = db.exec(
        select(Record, GroupRecord.shared_at)
        .join(GroupRecord, col(GroupRecord.record_id) == Record.id)
        .where(GroupRecord.group_id == group_id)
        .order_by(col(GroupRecord.shared_at).desc())
    ).all()
    return GroupDetail(
        **_to_out(db, group, member.role).model_dump(),
        members=[MemberOut(display_name=m.display_name, role=m.role) for m in members],
        records=[
            SharedRecordOut(**RecordSummary.model_validate(r, from_attributes=True).model_dump(), shared_at=shared_at)
            for r, shared_at in shared
        ],
    )
