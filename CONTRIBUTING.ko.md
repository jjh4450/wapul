# wapul 기여 가이드

**[English version](CONTRIBUTING.md)**

wapul에 관심을 가져주셔서 감사합니다. 이 문서는 기여 절차와 가이드라인을 설명합니다.

이 레포지터리는 모노레포입니다:

| 디렉터리 | 설명 |
|----------|------|
| `wapul-be/` | 백엔드 (FastAPI, uv) |
| `wapul-fe/` | 프론트엔드 (SvelteKit, pnpm) |

## 목차

- [시작하기 전에](#시작하기-전에)
- [개발 환경](#개발-환경)
- [코딩 표준](#코딩-표준)
- [커밋 가이드라인](#커밋-가이드라인)
- [Pull Request 절차](#pull-request-절차)
- [버전 관리 및 릴리스](#버전-관리-및-릴리스)
- [리뷰 프로세스](#리뷰-프로세스)

---

## 시작하기 전에

### 기존 이슈 확인

작업을 시작하기 전에, 동일한 이슈나 PR이 있는지 확인하세요:

1. [기존 이슈](https://github.com/jjh4450/wapul/issues) 검색
2. [기존 PR](https://github.com/jjh4450/wapul/pulls) 검색

없다면, 먼저 이슈를 생성하여 변경 사항을 논의하세요.

### Issue First 정책

**사소하지 않은 모든 변경은 먼저 이슈가 필요합니다.**

- 버그 수정: 버그 리포트 이슈 생성
- 새 기능: 기능 요청 이슈 생성
- 문서: 작은 수정은 바로 PR 가능

이를 통해 프로젝트 방향과 일치하는 작업을 보장하고 중복 작업을 방지합니다.

---

## 개발 환경

### 필수 사항

- Python 3.11+ (3.14 권장)
- [uv](https://docs.astral.sh/uv/)
- Git
- Docker (선택, PostgreSQL 테스트용)

### 설정 (백엔드)

```bash
# Fork 후 clone
git clone https://github.com/YOUR_USERNAME/wapul.git
cd wapul/wapul-be

# 의존성 설치 (dev 그룹 기본 포함, .venv 자동 생성)
uv sync

# 환경 파일 복사
cp .env.example .env
```

프론트엔드(`wapul-fe/`)는 pnpm을 사용하며, 변경 시 `pnpm format` 후 `pnpm lint`, `pnpm check`, `pnpm test`를 통과해야 합니다. 자세한 내용은 [프론트엔드 문서](https://jjh4450.github.io/wapul/frontend/)를 참고하세요.

### 린트와 포맷

**백엔드 변경은 ruff 린트와 포맷 검사를 통과해야 합니다** (CI에서 확인).

```bash
uv run ruff format   # 포맷 적용
uv run ruff check    # 린트
```

규칙과 `noqa` 사용 원칙은 [린트와 포맷 가이드](https://jjh4450.github.io/wapul/backend/development/linting/)를 참고하세요.

### 테스트 실행

**모든 코드 변경은 테스트를 통과해야 합니다.**

```bash
# 전체 테스트 실행
uv run pytest

# 커버리지 포함
uv run pytest --cov=app --cov-report=term-missing

# 특정 테스트 파일
uv run pytest tests/core/test_auth.py
```

### 서버 실행

```bash
uv run uvicorn app.main:app --reload --port 2614
```

---

## 코딩 표준

### Python 스타일

**PEP 8**을 따르며, 다음 사항을 준수합니다:

- 포맷은 `ruff format`이 결정합니다 (줄 길이 최대 120자)
- 모든 함수 파라미터와 반환값에 타입 힌트 사용
- 모든 public 함수, 클래스, 모듈에 docstring 작성

### 아키텍처 원칙

1. **계층형 아키텍처**: Router → Service → Domain → Data
2. **도메인 예외**: 서비스에서는 HTTP 예외가 아닌 `DomainException` 하위 클래스 사용
3. **UTC 저장**: 모든 datetime은 UTC naive로 데이터베이스에 저장
4. **소유자 격리**: 모든 리소스는 `owner_id`로 필터링

### 파일 명명

| 유형 | 패턴 | 예시 |
|------|------|------|
| Router | `app/api/v1/{domain}.py` | `items.py` |
| Service | `app/domain/{domain}/service.py` | `service.py` |
| Schema | `app/domain/{domain}/schema/dto.py` | `dto.py` |
| Model | `app/models/{domain}.py` | `item.py` |
| Test | `tests/domain/{domain}/test_*.py` | `test_service.py` |

---

## 커밋 가이드라인

### 커밋 메시지 형식

Conventional Commit 형식을 따릅니다:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 타입

| 타입 | 설명 |
|------|------|
| `feat` | 새 기능 |
| `fix` | 버그 수정 |
| `docs` | 문서만 변경 |
| `style` | 코드 스타일 (포맷팅, 로직 변경 없음) |
| `refactor` | 버그 수정도 기능 추가도 아닌 코드 변경 |
| `test` | 테스트 추가 또는 수정 |
| `chore` | 빌드 프로세스, 의존성 등 |

### 예시

```
feat(be): 사용자 프로필 조회 엔드포인트 추가

OIDC 토큰의 클레임으로 현재 사용자 프로필을 반환.

- UserProfile 모델 추가
- GET /v1/users/me 엔드포인트 추가
- 서비스/라우터 테스트 추가

Closes #42
```

### 커밋 원칙

1. **원자적 커밋**: 각 커밋은 하나의 논리적 변경
2. **빌드 가능**: 각 커밋에서 모든 테스트 통과
3. **설명적**: 제목은 무엇을, 본문은 왜를 설명
4. **이슈 참조**: Footer에 `Closes #N` 또는 `Fixes #N` 사용

---

## Pull Request 절차

### 제출 전 체크리스트

- [ ] 모든 테스트 통과 (`uv run pytest`)
- [ ] 스타일 가이드라인 준수
- [ ] 새 코드에 적절한 테스트 작성
- [ ] 필요시 문서 업데이트
- [ ] 커밋 메시지 가이드라인 준수
- [ ] 최신 `main`에 리베이스

### PR 제목 형식

커밋 메시지 제목과 동일:

```
feat(be): 사용자 프로필 조회 엔드포인트 추가
fix(auth): JWKS 캐시 만료 처리
docs: Windows 설치 가이드 업데이트
```

### PR 설명

PR 템플릿을 사용하세요. 다음을 포함합니다:

1. **요약**: 이 PR이 하는 일
2. **관련 이슈**: 이슈 링크 (`Closes #N`)
3. **변경 사항**: 변경 내용 목록
4. **테스트 계획**: 검증 방법

### PR 크기

- PR은 집중적이고 적절한 크기로 유지
- 큰 변경은 논리적으로 리뷰 가능한 단위로 분리
- PR이 너무 커지면 분리를 논의

---

## 버전 관리 및 릴리스

### 버전 형식

백엔드는 `vX.Y.Z` 형식을 사용합니다 (1.0.0부터 시작):

| 자리 | 올라가는 때 | 누가 |
|------|-------------|------|
| X | API 경로 버전 변경 (`/v1` → `/v2`) | 메인테이너가 Backend Docker 워크플로를 `major` 입력으로 수동 실행 |
| Y | API 계약 변경 (`openapi/openapi.json`의 `info.version`, 스펙 내용 해시) | CI 자동 |
| Z | 그 외 모든 릴리스 | CI 자동 |

`/v1` 아래에서는 호환을 깨는 변경을 하지 않습니다. 깨지는 변경은 `/v2`로 추가합니다.

### 동작 방식

버전 관리는 CI/CD를 통해 **완전히 자동화**되어 있습니다. 백엔드 변경이 `main`에 머지되면:

1. GitHub Actions가 마지막 릴리스 태그와 API 계약을 비교해 다음 버전을 계산
2. Docker 이미지를 `X.Y.Z`, `X.Y`, `X`, `latest` 태그로 빌드
3. CHANGELOG.md의 `[Unreleased]` 섹션이 실제 버전으로 치환
4. 릴리스 태그와 GitHub Release가 자동으로 생성

매주 마지막 릴리스를 같은 태그로 다시 빌드해 베이스 이미지와 시스템 패키지 보안 패치를 반영합니다. 이미지를 고정해야 하면 태그 대신 digest(`@sha256:...`)를 사용하세요.

**기여자는 버전 번호를 직접 설정하거나 변경하지 않습니다.**

### 기여자가 해야 할 것

PR에 사용자에게 영향을 주는 변경이 포함되어 있다면, `wapul-be/CHANGELOG.md`의 `[Unreleased]` 섹션을 업데이트하세요:

```markdown
## [Unreleased]

### Added
- **새 기능 설명** (`scope`): 추가된 내용의 상세 설명

### Fixed
- **버그 설명** (`scope`): 수정된 내용과 이유
```

적절한 카테고리를 사용하세요: Added, Changed, Deprecated, Removed, Fixed, Security.

`[Unreleased]`에 `_No unreleased changes._`가 있다면, 해당 내용을 교체하세요:

```markdown
## [Unreleased]

### Added
- **사용자 프로필 조회** (`users`): `GET /v1/users/me` 엔드포인트 추가
```

CI 파이프라인이 릴리스 시 `[Unreleased]`를 실제 버전으로 변환합니다.

### 하지 말아야 할 것

- 버전 태그를 수동으로 생성하지 **마세요**
- `[Unreleased]` 아래의 이미 릴리스된 버전 항목을 수정하지 **마세요**
- `.env`나 `config.py`의 `APP_VERSION`을 수정하지 **마세요** — 빌드 시 자동 주입됩니다

---

## 리뷰 프로세스

### 리뷰어가 확인하는 것

1. **정확성**: 코드가 의도한 대로 동작하는가?
2. **테스트**: 엣지 케이스가 커버되었는가?
3. **아키텍처**: 프로젝트 패턴을 따르는가?
4. **성능**: 명백한 성능 이슈가 있는가?
5. **보안**: 보안 우려 사항이 있는가?

### 리뷰 대응

- 재리뷰 요청 전에 모든 코멘트 처리
- 동의하지 않으면 이유를 설명
- 처리 후 대화를 resolved로 표시

### 리뷰 타임라인

- 메인테이너는 3-5 영업일 내 초기 리뷰 제공 목표
- 복잡한 PR은 더 걸릴 수 있음
- 1주일 후 응답 없으면 PR에서 핑

---

## 도움 받기

- **버그**: [Issue](https://github.com/jjh4450/wapul/issues) 생성
- **보안**: [SECURITY.md](SECURITY.md) 참조

---

*좋은 코드는 좋은 리뷰에서 나옵니다. 기여해 주셔서 감사합니다.*
