# API Overview

The wapul backend provides a REST API. It currently ships only the infrastructure layer; there are no domain endpoints yet.

## Base URL

All APIs are served under the `/v1` prefix:

- **Development**: `http://localhost:2614/v1`
- **Production**: `https://your-domain.com/v1`

## Authentication

All API endpoints (except health check) require authentication via OIDC Bearer token:

```
Authorization: Bearer <access_token>
```

> 📖 **Detailed Guide**: [Authentication Guide](../guides/auth.ko.md)

## Endpoint Layout

| Path | Auth | Description |
|------|------|-------------|
| `GET /health` | Not required | Health check (for load balancers / container orchestration) |
| `/v1/*` | Required | Domain APIs (none yet) |

Register new routers on the `authed` router in `app/api/v1/__init__.py` to get the `/v1` prefix and authentication (`get_current_user`) automatically. Register public routers directly on `api_router`.

```python
from app.api.v1 import authed

authed.include_router(items.router)  # → /v1/items, auth required
```

> 📖 **Detailed Guide**: [REST API Reference](rest-api.en.md)

## Rate Limiting

Rate limiting applies to `/v1/*` paths:

- **Default**: 60 requests per 60 seconds per user
- **Headers**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

> 📖 **Detailed Guide**: [Rate Limiting Guide](../development/rate-limit.md)

## Error Handling

`DomainException` and unhandled exceptions return a consistent error response (`app/core/error_handlers.py`):

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

FastAPI's built-in errors such as request validation failures (`422`) use the `{"detail": ...}` format.

Common HTTP status codes:

- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `429` - Too Many Requests
- `500` - Internal Server Error

## Data Formats

- **Request**: JSON (`Content-Type: application/json`)
- **Response**: JSON (`Content-Type: application/json`)
- **Dates**: ISO 8601 format (`2024-01-15T10:00:00Z`)
- **UUIDs**: Standard UUID v4 format

!!! warning "JSON requests require the `Content-Type` header"
    Requests that carry a body (`POST`, `PUT`, `PATCH`) must include the `Content-Type: application/json` header.

    - **Missing header** → `422 Unprocessable Entity` (the body is not parsed as JSON)
    - **Wrong type** (e.g. `text/plain`) → `415 Unsupported Media Type`
    - `application/json` and `application/*+json` media types are accepted.
    - Bodyless requests (`GET`, `DELETE`, etc.) are unaffected.

    Most HTTP clients (`fetch`, `axios`, `httpx`, ...) set this header automatically when sending JSON, but you must set it explicitly when sending a raw body (e.g. `curl --data`). (This strict check is enabled by default since FastAPI 0.132.)

## Interactive Documentation (Test Links)

When running the local dev server, you can test the API at these URLs:

| Item | Test Link (Development) |
|------|--------------------------|
| **Swagger UI** | [http://localhost:2614/docs](http://localhost:2614/docs) |
| **ReDoc** | [http://localhost:2614/redoc](http://localhost:2614/redoc) |

!!! warning "Warning"
    These links are only available when `DOCS_ENABLED=true` and `ENVIRONMENT` is not `production`.
