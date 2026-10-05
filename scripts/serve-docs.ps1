# 로컬 문서 서버 실행 (openapi.json 생성 후 mkdocs serve)
# 사용 (레포 루트에서): .\scripts\serve-docs.ps1
# Storybook은 별도로 실행: cd wapul-fe; pnpm storybook

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "Generating docs/backend/api/openapi.json..." -ForegroundColor Cyan
$env:OIDC_ENABLED = "false"
$env:DATABASE_URL = "sqlite:///:memory:"
Push-Location "$root\wapul-be"
try {
    & uv run --group docs python -c @"
import json
from app.main import app
with open('../docs/backend/api/openapi.json', 'w') as f:
    json.dump(app.openapi(), f, indent=2)
print('openapi.json generated.')
"@
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to generate openapi.json. Ensure uv is installed." -ForegroundColor Red
        exit 1
    }
} finally {
    Pop-Location
}

Write-Host "Starting mkdocs serve..." -ForegroundColor Cyan
Set-Location $root
& uv run --project wapul-be --group docs mkdocs serve @args
