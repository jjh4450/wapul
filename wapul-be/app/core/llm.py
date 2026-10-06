# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2026 Hipster Timer Project Contributors

"""Claude API 호출

구조화된 출력(pydantic 모델) 하나를 받는 호출만 쓴다. 안전 분류기가 거절하면
서버 쪽 fallback이 다른 모델로 다시 시도한다.
"""

from functools import cache
from typing import TypeVar

import anthropic
from pydantic import BaseModel

from app.core.config import settings

T = TypeVar("T", bound=BaseModel)


class LLMError(RuntimeError):
    """호출이 실패했거나 쓸 수 있는 답이 없다"""


@cache
def get_client() -> anthropic.Anthropic:
    # 키가 비어 있으면 SDK가 환경 변수나 ant 프로필에서 찾는다
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY or None)


def parse(system: str, user: str, output: type[T], client: anthropic.Anthropic | None = None) -> T:
    try:
        response = (client or get_client()).beta.messages.parse(
            model=settings.LLM_MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": settings.LLM_EFFORT},
            system=system,
            messages=[{"role": "user", "content": user}],
            output_format=output,
        )
    except anthropic.APIError as e:
        raise LLMError(str(e)) from e
    if response.stop_reason == "refusal":
        raise LLMError(f"refused: {response.stop_details}")
    if response.parsed_output is None:
        raise LLMError(f"no parsed output, stop_reason={response.stop_reason}")
    return response.parsed_output
