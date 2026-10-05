# API 개요

wapul 백엔드는 REST API를 제공합니다. 현재는 인프라 계층만 포함되어 있으며, 도메인 엔드포인트는 아직 없습니다.

## 기본 URL

모든 API는 `/v1` 접두사로 제공됩니다:

- **개발**: `http://localhost:2614/v1`
- **프로덕션**: `https://your-domain.com/v1`

## 인증

모든 API 엔드포인트(헬스체크 제외)는 OIDC Bearer 토큰 인증이 필요합니다:

```
Authorization: Bearer <access_token>
```

> 📖 **상세 가이드**: [인증 가이드](../guides/auth.ko.md)

## 엔드포인트 구성

| 경로 | 인증 | 설명 |
|------|------|------|
| `GET /health` | 불필요 | 헬스체크 (로드밸런서/컨테이너 오케스트레이션용) |
| `/v1/*` | 필요 | 도메인 API (아직 없음) |

새 라우터는 `app/api/v1/__init__.py`의 `authed` 라우터에 등록하면 `/v1` 접두사와 인증(`get_current_user`)이 자동으로 적용됩니다. 공개 라우터는 `api_router`에 직접 등록합니다.

```python
from app.api.v1 import authed

authed.include_router(items.router)  # → /v1/items, 인증 필요
```

> 📖 **상세 가이드**: [REST API 레퍼런스](rest-api.ko.md)

## Rate Limiting

`/v1/*` 경로에 Rate Limiting이 적용됩니다:

- **기본값**: 사용자당 60초에 60회 요청
- **헤더**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

> 📖 **상세 가이드**: [Rate Limiting 가이드](../development/rate-limit.ko.md)

## 에러 처리

`DomainException` 및 처리되지 않은 예외는 일관된 에러 응답을 반환합니다 (`app/core/error_handlers.py`):

```json
{
  "error_id": "8f0c...",
  "status_code": 401,
  "error_type": "AuthenticationRequiredError",
  "message": "Error message here",
  "timestamp": "2026-01-15T10:00:00+00:00",
  "path": "/v1/..."
}
```

요청 검증 실패(`422`) 등 FastAPI 기본 에러는 `{"detail": ...}` 형식을 따릅니다.

일반적인 HTTP 상태 코드:

- `200` - 성공
- `201` - 생성됨
- `400` - 잘못된 요청
- `401` - 인증 필요
- `403` - 권한 없음
- `404` - 찾을 수 없음
- `429` - 요청 한도 초과
- `500` - 서버 내부 오류

## 데이터 형식

- **요청**: JSON (`Content-Type: application/json`)
- **응답**: JSON (`Content-Type: application/json`)
- **날짜**: ISO 8601 형식 (`2024-01-15T10:00:00Z`)
- **UUID**: 표준 UUID v4 형식

!!! warning "JSON 요청에는 `Content-Type` 헤더가 필수입니다"
    본문을 포함하는 요청(`POST`, `PUT`, `PATCH`)은 반드시 `Content-Type: application/json` 헤더를 포함해야 합니다.

    - **헤더 누락** → `422 Unprocessable Entity` (본문이 JSON으로 파싱되지 않음)
    - **잘못된 타입**(예: `text/plain`) → `415 Unsupported Media Type`
    - `application/json` 및 `application/*+json` 계열이 허용됩니다.
    - 본문이 없는 요청(`GET`, `DELETE` 등)은 영향받지 않습니다.

    `fetch`, `axios`, `httpx` 등 대부분의 HTTP 클라이언트는 JSON 전송 시 이 헤더를 자동으로 설정하지만, `curl --data`처럼 본문만 수동으로 보내는 경우 헤더를 직접 지정해야 합니다. (이 엄격한 검사는 FastAPI 0.132부터 기본 활성화되었습니다.)

## 대화형 문서 (테스트 링크)

로컬 개발 서버 실행 시 아래 주소로 접속해 API를 테스트할 수 있습니다.

| 항목 | 테스트 링크 (Development) |
|------|---------------------------|
| **Swagger UI** | [http://localhost:2614/docs](http://localhost:2614/docs) |
| **ReDoc** | [http://localhost:2614/redoc](http://localhost:2614/redoc) |

!!! warning "주의"
    위 링크는 `DOCS_ENABLED=true`이고 `ENVIRONMENT`가 `production`이 아닐 때만 제공됩니다.
