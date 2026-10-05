# 설치

## 사전 요구사항

- Python 3.11+ (3.14 권장)
- [uv](https://docs.astral.sh/uv/) 패키지 매니저

## 단계별 설치

### 1. 저장소 클론

```bash
git clone https://github.com/jjh4450/wapul.git
cd wapul/wapul-be
```

### 2. 의존성 설치

```bash
# .venv 생성 + 의존성 설치 (dev 그룹 기본 포함)
uv sync

# 문서 빌드 의존성까지 설치
uv sync --group docs
```

### 3. 환경 변수 설정

```bash
# 예시 환경 파일 복사
cp .env.example .env

# .env 파일을 설정에 맞게 편집
# 자세한 내용은 구성 가이드 참조
```

### 4. 데이터베이스 초기화

```bash
# 데이터베이스 마이그레이션 실행
uv run alembic upgrade head
```

!!! note
    아직 마이그레이션 파일이 없습니다. 개발 중에는 앱 시작 시 SQLModel 메타데이터로 테이블이 생성됩니다.

### 5. 서버 시작

```bash
# 자동 리로드가 있는 개발 서버
uv run uvicorn app.main:app --reload --port 2614
```

서버는 다음 주소에서 접근 가능합니다:
- REST API: http://localhost:2614/docs (Swagger UI)

## Docker 설치

### Docker Compose 사용

```bash
# 빌드 및 실행
docker compose up --build

# 백그라운드 실행
docker compose up -d

# 로그 보기
docker compose logs -f
```

### 사전 빌드된 이미지 사용

```bash
# 최신 이미지 받기
docker pull ghcr.io/jjh4450/wapul-be:latest

# 컨테이너 실행
docker run -d \
  --name wapul-be \
  -p 2614:2614 \
  -e DATABASE_URL=sqlite:///./data/wapul.db \
  -e OIDC_ENABLED=false \
  -v wapul-data:/app/data \
  ghcr.io/jjh4450/wapul-be:latest
```

## 설치 확인

서버를 시작한 후 설치를 확인하세요:

```bash
# 헬스체크
curl http://localhost:2614/health

# 예상 응답:
# {"status":"healthy", ..., "version":"dev", "environment":"development"}
```

## 문제 해결

### 일반적인 문제

**포트 사용 중**
```bash
# 다른 포트 사용
uv run uvicorn app.main:app --reload --port 8000
```

**데이터베이스 연결 오류**
- `.env` 파일의 `DATABASE_URL` 확인
- PostgreSQL 사용 시 데이터베이스 서버 실행 확인
- 데이터베이스 권한 확인

**Docker: `unable to open database file`**
- 공식 이미지는 엔트리포인트에서 `/app/data` 볼륨에 쓰기 권한을 부여합니다. 위의 `docker run` 예시대로 `-v wapul-data:/app/data`와 `DATABASE_URL=sqlite:///./data/wapul.db`를 사용하면 됩니다. 이전에 실패한 컨테이너를 삭제한 뒤 이미지를 다시 받고 실행해 보세요.

**모듈을 찾을 수 없음**
```bash
# 의존성 재동기화
uv sync
```
