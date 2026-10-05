# 로컬 문서 서버 실행 (openapi.json 생성 후 mkdocs serve)
# 사용 (레포 루트에서): .\scripts\serve-docs.ps1
# Storybook은 별도로 실행: cd wapul-fe; pnpm storybook

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Write-Host "Generating docs/backend/api/openapi.json..." -ForegroundColor Cyan
Push-Location "$root\wapul-be"
try {
    & uv run --group docs python scripts/export_openapi.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Failed to generate openapi.json. Ensure uv is installed." -ForegroundColor Red
        exit 1
    }
    Copy-Item "$root\openapi\openapi.json" "$root\docs\backend\api\openapi.json"
} finally {
    Pop-Location
}

Write-Host "Starting mkdocs serve..." -ForegroundColor Cyan
Set-Location $root
& uv run --project wapul-be --group docs mkdocs serve @args
