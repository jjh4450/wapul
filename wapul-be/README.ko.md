<div align="center">

<a id="top"></a>

# wapul-be

**wapul 백엔드 API (FastAPI)**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.142-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supported-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![Docs](https://img.shields.io/badge/Docs-Online-009688?style=flat-square&logo=readme&logoColor=white)](https://jjh4450.github.io/wapul/)

**[공식 문서](https://jjh4450.github.io/wapul/)** • **[English](README.md)**

</div>

---

<!-- docs:start -->

## 개요

`wapul-be`는 [wapul](https://github.com/jjh4450/wapul) 모노레포의 백엔드입니다. 현재는 인프라 계층만 포함하며,
도메인 엔드포인트는 아직 없습니다. 새 라우터는 `app/api/v1/__init__.py`의 `authed` 라우터에 등록합니다.

### 포함된 구성 요소

| 영역 | 위치 | 설명 |
|------|------|------|
| 앱 | `app/main.py` | FastAPI 앱, lifespan, CORS, `GET /health` |
| API 라우터 | `app/api/v1/__init__.py` | 인증이 필요한 빈 `/v1` 라우터 (`authed`) |
| 인증 | `app/core/auth/` | OIDC JWT 검증 (JWKS 캐시), `get_current_user` 의존성 |
| 레이트 리밋 | `app/ratelimit/` | 규칙 기반 HTTP 레이트 리밋, WebSocket 헬퍼, Cloudflare / 신뢰 프록시 클라이언트 IP |
| 에러 처리 | `app/core/error_handlers.py` | `DomainException` → HTTP 응답 매핑 |
| 로깅 | `app/core/logging.py`, `app/middleware/request_logger.py` | 로깅 설정, 요청 로거 |
| 설정 | `app/core/config.py` | `pydantic-settings` 기반 환경 변수 |
| DB | `app/db/` | SQLModel 세션 (기본 SQLite, PostgreSQL 지원), DB keep-alive |
| 모델 | `app/models/base.py` | `UUIDBase`, `TimestampMixin`, `UpdateMixin` (pydantic `MISSING` sentinel) |
| 마이그레이션 | `alembic/` | Alembic (아직 마이그레이션 없음) |
| 테스트 | `tests/` | pytest |

## 빠른 시작

### 필수 사항

- Python 3.11+ (3.14 권장)
- [uv](https://docs.astral.sh/uv/)

### 실행

```bash
cd wapul-be

# 의존성 설치 (dev 그룹 기본 포함)
uv sync

# 환경 변수 (선택)
cp .env.example .env

# 개발 서버
uv run uvicorn app.main:app --reload --port 2614
```

- 헬스 체크: http://localhost:2614/health
- Swagger UI: http://localhost:2614/docs (`ENVIRONMENT=production`에서는 비활성화)

### Docker

```bash
cd wapul-be
docker compose up --build
```

**노출 포트:** `2614`

### 테스트

```bash
uv run pytest
```

### 마이그레이션

```bash
uv run alembic revision --autogenerate -m "변경 내용 설명"
uv run alembic upgrade head
```

### 문서 (로컬)

```bash
# 레포 루트에서 실행 (통합 문서: 백엔드 + 프론트엔드)
uv sync --project wapul-be --group docs
./scripts/serve-docs.sh
```

## 설정

모든 설정은 환경 변수(또는 `.env`)에서 읽습니다. 전체 목록은 `.env.example`과
[설정 문서](https://jjh4450.github.io/wapul/getting-started/configuration/)를 참고하세요.

<!-- docs:end -->

## 라이선스

이 프로젝트는 Mozilla Public License 2.0 하에 배포됩니다. [LICENSE](../LICENSE)를 참고하세요.

---

<div align="center">

**[맨 위로](#top)**

</div>
