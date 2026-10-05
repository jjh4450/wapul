# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2026 Hipster Timer Project Contributors

"""루트 openapi/openapi.json 생성 (프론트엔드 타입 생성의 원본)

info.version에는 스펙 내용 해시(API 계약 버전)를 넣는다. API가 바뀔 때만 바뀌며, 릴리스 Y 버전 판정에 쓰인다.

사용 (wapul-be에서): uv run python scripts/export_openapi.py
"""

import hashlib
import json
import os
import sys
from pathlib import Path

BE_DIR = Path(__file__).resolve().parent.parent
SPEC = BE_DIR.parent / "openapi" / "openapi.json"


def main() -> None:
    sys.path.insert(0, str(BE_DIR))
    # 로컬 .env 값과 무관하게 항상 같은 스펙이 나오도록 고정
    os.environ.update(
        ENVIRONMENT="development",
        OIDC_ENABLED="false",
        DATABASE_URL="sqlite:///:memory:",
    )
    from app.main import app

    spec = app.openapi()
    spec["info"]["version"] = ""
    spec["info"]["version"] = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:12]

    SPEC.parent.mkdir(exist_ok=True)
    SPEC.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{SPEC.name} generated.")


if __name__ == "__main__":
    main()
