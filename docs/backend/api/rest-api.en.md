# REST API Reference

View the complete API spec in Swagger UI format.

<swagger-ui src="openapi.json"/>

!!! info "Automatic OpenAPI injection"
    `openapi.json` is generated from the FastAPI app (`app.openapi()`) at docs build time.
    New routers show up on this page with no extra work.
    Locally, `./scripts/serve-docs.sh` generates it and then runs `mkdocs serve`.

## Main Endpoints

### Health

```http
GET    /health                  # Server status (no auth required)
```

### v1

The `/v1` router (`authed`) is empty. List domain endpoints here as you add them.
