#!/usr/bin/env bash
# 로컬 문서 서버 실행 (openapi.json 생성 후 mkdocs serve)
# 사용 (레포 루트에서): ./scripts/serve-docs.sh
# Storybook은 별도로 실행: cd wapul-fe && pnpm storybook

set -e
root="$(cd "$(dirname "$0")/.." && pwd)"

echo "Generating docs/backend/api/openapi.json..."
(
  cd "$root/wapul-be"
  OIDC_ENABLED=false DATABASE_URL="sqlite:///:memory:" uv run --group docs python -c "
import json
from app.main import app
with open('../docs/backend/api/openapi.json', 'w') as f:
    json.dump(app.openapi(), f, indent=2)
print('openapi.json generated.')
"
)

echo "Starting mkdocs serve..."
cd "$root"
exec uv run --project wapul-be --group docs mkdocs serve "$@"
