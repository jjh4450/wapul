<div align="center">

<a id="top"></a>

# wapul-be

**Backend API for wapul (FastAPI)**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.142-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supported-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![Docs](https://img.shields.io/badge/Docs-Online-009688?style=flat-square&logo=readme&logoColor=white)](https://jjh4450.github.io/wapul/)

**[Documentation](https://jjh4450.github.io/wapul/)** • **[한국어](README.ko.md)**

</div>

---

<!-- docs:start -->

## Overview

`wapul-be` is the backend of the [wapul](https://github.com/jjh4450/wapul) monorepo. It currently ships only the
infrastructure layer — no domain endpoints yet. Add routers to the `authed` router in `app/api/v1/__init__.py`.

### What's included

| Area | Location | Description |
|------|----------|-------------|
| App | `app/main.py` | FastAPI app, lifespan, CORS, `GET /health` |
| API router | `app/api/v1/__init__.py` | Empty `/v1` router (`authed`) that requires authentication |
| Auth | `app/core/auth/` | OIDC JWT verification (JWKS cache), `get_current_user` dependency |
| Rate limiting | `app/ratelimit/` | Per-rule HTTP rate limit, WebSocket helper, Cloudflare / trusted proxy client IP |
| Errors | `app/core/error_handlers.py` | `DomainException` → HTTP response mapping |
| Logging | `app/core/logging.py`, `app/middleware/request_logger.py` | Logging setup, request logger |
| Config | `app/core/config.py` | `pydantic-settings` based environment variables |
| DB | `app/db/` | SQLModel session (SQLite default, PostgreSQL supported), DB keep-alive |
| Models | `app/models/base.py` | `UUIDBase`, `TimestampMixin`, `UpdateMixin` (pydantic `MISSING` sentinel) |
| Migrations | `alembic/` | Alembic (no migrations yet) |
| Tests | `tests/` | pytest |

## Quick Start

### Prerequisites

- Python 3.11+ (3.14 recommended)
- [uv](https://docs.astral.sh/uv/)

### Run

```bash
cd wapul-be

# Install dependencies (dev group included by default)
uv sync

# Environment variables (optional)
cp .env.example .env

# Development server
uv run uvicorn app.main:app --reload --port 2614
```

- Health check: http://localhost:2614/health
- Swagger UI: http://localhost:2614/docs (disabled when `ENVIRONMENT=production`)

### Docker

```bash
cd wapul-be
docker compose up --build
```

**Exposed Port:** `2614`

### Tests

```bash
uv run pytest
```

### Migrations

```bash
uv run alembic revision --autogenerate -m "describe change"
uv run alembic upgrade head
```

### Docs (local)

```bash
# run from the repo root (unified docs: backend + frontend)
uv sync --project wapul-be --group docs
./scripts/serve-docs.sh
```

## Configuration

All settings are read from environment variables (or `.env`). See `.env.example` and
[Configuration](https://jjh4450.github.io/wapul/getting-started/configuration/) for the full list.

<!-- docs:end -->

## License

This project is licensed under the Mozilla Public License 2.0. See [LICENSE](../LICENSE).

---

<div align="center">

**[Back to Top](#top)**

</div>
