# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2026 Hipster Timer Project Contributors

from fastapi import APIRouter, Depends

from app.core.auth import get_current_user

api_router = APIRouter()

# 인증이 필요한 라우터는 authed에, 공개 라우터는 api_router에 직접 등록한다.
authed = APIRouter(prefix="/v1", dependencies=[Depends(get_current_user)])
api_router.include_router(authed)
