# Configuration

This guide covers all configuration options available in the wapul backend.

## Environment Variables

Configuration is done via `.env` file or environment variables.

## Environment Mode

| Variable | Description | Default |
|----------|-------------|---------|
| `ENVIRONMENT` | Runtime environment (`development`, `staging`, `production`) | `development` |

!!! warning "Warning"
    **Production Mode**: When `ENVIRONMENT=production`, the following settings are automatically applied:
    - `DEBUG` → `False`
    - `OPENAPI_URL` → `""` (disabled)
    - `DOCS_URL` → `""` (disabled)
    - `REDOC_URL` → `""` (disabled)

## Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name (OpenAPI title) | `wapul-be` |
| `APP_VERSION` | Application version (injected at build time) | `dev` |
| `DOCS_ENABLED` | Master switch for all API docs (Swagger, ReDoc) | `True` |
| `DEBUG` | Enable debug mode | `True` |
| `OPENAPI_URL` | OpenAPI schema URL (empty string to disable) | `/openapi.json` |
| `DOCS_URL` | Swagger UI URL (empty string to disable) | `/docs` |
| `REDOC_URL` | ReDoc URL (empty string to disable) | `/redoc` |
| `LOG_LEVEL` | Log level | `INFO` |

## Database Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | DB connection string | `sqlite:///./wapul.db` |
| `TEST_DATABASE_URL` | DB connection string for tests (optional) | - |
| `POOL_SIZE` | Connection pool size | `5` |
| `MAX_OVERFLOW` | Max overflow connections | `10` |
| `DB_POOL_PRE_PING` | Validate connections before use | `True` |
| `DB_POOL_RECYCLE` | Connection recycle time (seconds) | `3600` |
| `DB_KEEPALIVE_INTERVAL_SECONDS` | Interval (seconds) for periodic keep-alive `SELECT 1`; `0` or less disables it | `0` |

**Database URL Examples:**

```bash
# SQLite (development)
DATABASE_URL=sqlite:///./wapul.db

# PostgreSQL (production)
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```

!!! tip "DB Keep-Alive (prevent idle auto-pause)"
    Some managed/serverless databases automatically pause an instance (or drop idle
    connections) after a period without traffic. Set `DB_KEEPALIVE_INTERVAL_SECONDS`
    to a positive value (seconds) to run a lightweight `SELECT 1` on that interval and
    keep the database awake. A value of `0` (the default) or any negative value disables it.

    Seconds conversion:

    | Interval | Seconds |
    |----------|---------|
    | 5 minutes | `300` |
    | 1 hour | `3600` |
    | 6 hours | `21600` |
    | 12 hours | `43200` |
    | 1 day | `86400` |
    | (ref) 7 days = Supabase pause threshold | `604800` |

    Keep the interval well below the pause threshold (7 days). `86400` (1 day) is a
    good default so a single missed ping (app restart/outage) still leaves plenty of margin.

## Authentication (OIDC)

| Variable | Description | Default |
|----------|-------------|---------|
| `OIDC_ENABLED` | Enable OIDC authentication | `True` |
| `OIDC_ISSUER_URL` | OIDC Provider issuer URL | - |
| `OIDC_AUDIENCE` | Client ID for token validation | - |
| `OIDC_DISCOVERY_URL` | Custom discovery endpoint | Auto-generated |
| `OIDC_JWKS_CACHE_TTL_SECONDS` | JWKS cache TTL | `3600` |

> 📖 **Detailed Guide**: [Authentication Guide](../guides/auth.ko.md)

## Rate Limiting

**HTTP Rate Limiting:**

| Variable | Description | Default |
|----------|-------------|---------|
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `True` |
| `RATE_LIMIT_DEFAULT_WINDOW` | Default window size (seconds) | `60` |
| `RATE_LIMIT_DEFAULT_REQUESTS` | Default max requests per window | `60` |

**WebSocket Rate Limiting:**

| Variable | Description | Default |
|----------|-------------|---------|
| `WS_RATE_LIMIT_ENABLED` | Enable WebSocket rate limiting | `True` |
| `WS_CONNECT_WINDOW` | Connection limit window (seconds) | `60` |
| `WS_CONNECT_MAX` | Max connections per window | `10` |
| `WS_MESSAGE_WINDOW` | Message limit window (seconds) | `60` |
| `WS_MESSAGE_MAX` | Max messages per window | `120` |

> 📖 **Detailed Guide**: [Rate Limiting Guide](../development/rate-limit.ko.md)

## Proxy Settings (Cloudflare / Trusted Proxy)

| Variable | Description | Default |
|----------|-------------|---------|
| `PROXY_FORCE` | Enforce proxy usage (block direct access) | `False` |
| `CF_ENABLED` | Enable Cloudflare proxy mode | `False` |
| `CF_IP_CACHE_TTL` | Cloudflare IP list cache TTL (seconds) | `86400` |
| `TRUSTED_PROXY_IPS` | Trusted proxy IPs (comma-separated, CIDR supported) | `""` |
| `ORIGIN_VERIFY_HEADER` | Custom header name for origin verification (optional) | `""` |
| `ORIGIN_VERIFY_SECRET` | Secret value for origin verification header | `""` |

## CORS (Cross-Origin Resource Sharing)

| Variable | Description | Default |
|----------|-------------|---------|
| `CORS_ALLOWED_ORIGINS` | Allowed origins (comma-separated) | Development defaults |
| `CORS_ALLOW_CREDENTIALS` | Allow credentials (cookies, etc.) | `False` |
| `CORS_ALLOW_METHODS` | Allowed HTTP methods (comma-separated) | `*` |
| `CORS_ALLOW_HEADERS` | Allowed headers (comma-separated) | `*` |

!!! warning "Warning"
    `CORS_ALLOWED_ORIGINS="*"` and `CORS_ALLOW_CREDENTIALS=true` cannot be used together.

!!! tip "Tip"
    When using WebSocket, include `ws://` or `wss://` URLs in `CORS_ALLOWED_ORIGINS`.

## Example .env File

```bash
# Environment
ENVIRONMENT=development

# Database
DATABASE_URL=sqlite:///./wapul.db

# Authentication (Development - disabled)
OIDC_ENABLED=false

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_DEFAULT_WINDOW=60
RATE_LIMIT_DEFAULT_REQUESTS=60

# Logging
LOG_LEVEL=INFO
```

## Production Configuration

For production deployment, see the [Production Guide](../deployment/production.md).
