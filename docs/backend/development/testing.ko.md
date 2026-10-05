# pytest로 테스트 실행하기

이 문서는 `wapul-be/tests/` 폴더를 이용해 **pytest**로 테스트를 실행하는 방법을 소개합니다.

## 사전 요구사항

- Python 3.11+ (3.14 권장), [uv](https://docs.astral.sh/uv/)
- 개발 의존성 설치: `uv sync` (dev 그룹 기본 포함)

---

## 기본 명령어

### 전체 테스트 실행

```bash
uv run pytest
```

- `tests/` 아래 모든 테스트 수집·실행
- `pyproject.toml`의 `[tool.pytest.ini_options]` 설정을 사용합니다 (`.env` 자동 로드 포함)

### 출력 옵션

```bash
# 상세 출력 (-v)
uv run pytest -v

# 짧은 traceback
uv run pytest --tb=short

# 첫 실패 시 중단
uv run pytest -x

# 조합 예시
uv run pytest -v --tb=short -x
```

### 커버리지

```bash
# app 패키지 커버리지 + 터미널 요약
uv run pytest --cov=app --cov-report=term-missing

# HTML 리포트 생성 (브라우저에서 확인)
uv run pytest --cov=app --cov-report=html
```

---

## 디렉터리/파일 지정

### 특정 디렉터리

```bash
# core (인증, 설정) 테스트만
uv run pytest tests/core/

# 모델 베이스 (UUIDBase, TimestampMixin, UpdateMixin) 테스트만
uv run pytest tests/models/

# ratelimit 테스트만
uv run pytest tests/ratelimit/
```

### 특정 파일

```bash
uv run pytest tests/core/test_auth.py
```

### 특정 함수/클래스

```bash
# 테스트 함수 이름으로 (부분 일치)
uv run pytest tests/ratelimit/ -k "test_storage"

# 정확한 테스트 경로
uv run pytest tests/models/test_update_mixin.py::<테스트_함수명>
```

---

## 마커로 필터링

`pyproject.toml`에 등록된 마커를 사용해 테스트 유형별로 실행할 수 있습니다.

| 마커 | 설명 |
|------|------|
| `e2e` | End-to-end (전체 HTTP API 흐름) |
| `integration` | 통합 테스트 (DB, 트랜잭션 등) |
| `ratelimit` | Rate limit 관련 테스트 |

```bash
# E2E만 실행
uv run pytest -m e2e

# 특정 마커 제외
uv run pytest -m "not ratelimit"
```

---

## tests/ 폴더 구조

| 경로 | 설명 |
|------|------|
| `tests/core/` | 인증, 설정 테스트 |
| `tests/db/` | DB keep-alive 테스트 |
| `tests/models/` | `app/models/base.py` 베이스 모델 계약 테스트 |
| `tests/ratelimit/` | Rate limit 미들웨어·스토리지·Cloudflare·WebSocket 테스트 |
| `tests/conftest.py` | 공통 fixture (DB 엔진/세션, 테스트 유저, E2E 클라이언트 등) |

도메인을 추가하면 `tests/domain/{domain}/test_*.py` 형식으로 테스트를 추가합니다.

---

## PostgreSQL로 테스트

기본은 SQLite 메모리 DB입니다. PostgreSQL로 실행하려면:

```bash
# 1. PostgreSQL 컨테이너 기동
docker compose -f docker-compose.test.yaml up -d

# 2. 환경 변수 설정 후 pytest
# Windows PowerShell
$env:TEST_DATABASE_URL="postgresql://testuser:testpass@localhost:5432/testdb"
uv run pytest

# Linux/macOS
TEST_DATABASE_URL="postgresql://testuser:testpass@localhost:5432/testdb" uv run pytest

# 3. 정리
docker compose -f docker-compose.test.yaml down -v
```

---

## 관련 문서

- [Python 버전 호환성 테스트](python-version-testing.ko.md) — Docker로 여러 Python 버전에서 테스트하는 방법
