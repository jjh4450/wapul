#!/usr/bin/env bash
# 로컬 문서 서버 실행 (openapi.json 생성 후 mkdocs serve)
# 사용 (레포 루트에서): ./scripts/serve-docs.sh
# Storybook은 별도로 실행: cd wapul-fe && pnpm storybook

set -e
root="$(cd "$(dirname "$0")/.." && pwd)"

echo "Generating docs/backend/api/openapi.json..."
(
  cd "$root/wapul-be"
  uv run --group docs python scripts/export_openapi.py
  cp ../openapi/openapi.json ../docs/backend/api/openapi.json
)

echo "Starting mkdocs serve..."
cd "$root"
exec uv run --project wapul-be --group docs mkdocs serve "$@"
