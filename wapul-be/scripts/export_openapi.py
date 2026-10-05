# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2026 Hipster Timer Project Contributors

"""루트 openapi/openapi.json 생성 (프론트엔드 타입 생성의 원본)

사용 (wapul-be에서): uv run python scripts/export_openapi.py
  --check: 스펙 입력(소스) 해시가 openapi/source.sha256과 같으면 exit 0. 표준 라이브러리만 사용하므로 의존성 설치 전에 실행 가능
"""

import hashlib
import json
import os
import sys
from pathlib import Path

BE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BE_DIR.parent / "openapi"
SPEC = OUT_DIR / "openapi.json"
HASH = OUT_DIR / "source.sha256"

# 스펙에 영향을 주는 입력. 이 중 하나라도 바뀌면 재생성
INPUTS = ("app", "pyproject.toml", "uv.lock", "scripts/export_openapi.py")


def source_hash() -> str:
    files = []
    for name in INPUTS:
        path = BE_DIR / name
        files.extend(path.rglob("*.py") if path.is_dir() else [path])

    h = hashlib.sha256()
    for f in sorted(files, key=lambda p: p.relative_to(BE_DIR).as_posix()):
        h.update(f.relative_to(BE_DIR).as_posix().encode() + b"\0")
        # Windows autocrlf 체크아웃에서도 같은 해시가 나오도록 줄바꿈 정규화
        h.update(f.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return h.hexdigest()


def main() -> None:
    digest = source_hash()
    if "--check" in sys.argv:
        fresh = SPEC.exists() and HASH.exists() and HASH.read_text().strip() == digest
        print("openapi spec is up to date." if fresh else "openapi spec is stale.")
        sys.exit(0 if fresh else 1)

    sys.path.insert(0, str(BE_DIR))
    # 로컬 .env 값과 무관하게 항상 같은 스펙이 나오도록 고정 (버전이 바뀌면 커밋 diff가 매번 생김)
    os.environ.update(
        ENVIRONMENT="development",
        APP_VERSION="dev",
        OIDC_ENABLED="false",
        DATABASE_URL="sqlite:///:memory:",
    )
    from app.main import app

    OUT_DIR.mkdir(exist_ok=True)
    SPEC.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    HASH.write_text(digest + "\n")
    print(f"{SPEC.name} generated.")


if __name__ == "__main__":
    main()
