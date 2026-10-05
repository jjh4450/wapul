# REST API 레퍼런스

전체 API 스펙을 Swagger UI 형식으로 확인할 수 있습니다.

<swagger-ui src="openapi.json"/>

!!! info "OpenAPI 스펙 자동 주입"
    `openapi.json`은 문서 빌드 시 FastAPI 앱(`app.openapi()`)에서 자동 생성됩니다.
    라우터를 추가하면 별도 작업 없이 이 페이지에 반영됩니다.
    로컬에서는 `./scripts/serve-docs.sh`가 생성 후 `mkdocs serve`를 실행합니다.

## 주요 엔드포인트

### 헬스체크 (Health)

```http
GET    /health                  # 서버 상태 확인 (인증 불필요)
```

### v1

`/v1` 라우터(`authed`)는 비어 있습니다. 도메인 엔드포인트를 추가하면 이곳에 정리하세요.
