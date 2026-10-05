# Python 버전 호환성 테스트 가이드

이 문서는 프로젝트의 Python 버전 호환성을 테스트하는 방법을 설명합니다.

## 개요

프로젝트의 Python 버전 호환성을 Docker를 사용하여 격리된 환경에서 테스트할 수 있습니다.
테스트 이미지(`Dockerfile.test`)는 `uv sync --locked`로 `uv.lock`에 고정된 의존성을 설치한 뒤 pytest를 실행합니다.

지원 Python 범위의 기준은 `pyproject.toml`의 `requires-python`입니다. 매트릭스 버전을 바꿀 때 함께 맞춰 주세요.

### 지원 버전

| Python 버전 | 상태 | 서비스명 |
|-------------|------|----------|
| 3.15 | 최신 | `python315` |
| 3.14 | 기본 (프로덕션) | `python314` |
| 3.13 | 지원 | `python313` |
| 3.12 | 지원 | `python312` |
| 3.11 | 최소 지원 | `python311` |

---

## 빠른 시작

### 특정 버전 테스트

```powershell
# Python 3.14 테스트
docker compose -f docker-compose.python-matrix.yaml up --build python314 --abort-on-container-exit

# Python 3.13 테스트
docker compose -f docker-compose.python-matrix.yaml up --build python313 --abort-on-container-exit

# Python 3.11 테스트
docker compose -f docker-compose.python-matrix.yaml up --build python311 --abort-on-container-exit
```

### 전체 버전 테스트 (스크립트)

```powershell
# Windows PowerShell
.\scripts\test-python-versions.ps1

# 특정 버전만 테스트
.\scripts\test-python-versions.ps1 3.12 3.13
```

```bash
# Linux/macOS
./scripts/test-python-versions.sh

# 특정 버전만 테스트
./scripts/test-python-versions.sh 3.12 3.13
```

### PostgreSQL과 함께 테스트

```powershell
docker compose -f docker-compose.python-matrix.yaml --profile postgres up --build python313-postgres --abort-on-container-exit
```

---

## 새 Python 버전 추가하기

Python 3.16이 출시되었다고 가정하고, 테스트 매트릭스에 추가하는 방법입니다.

### 1단계: docker-compose.python-matrix.yaml 수정

`services` 섹션에 새 서비스를 추가합니다:

```yaml
  # ============================================
  # Python 3.16
  # ============================================
  python316:
    container_name: test-python316
    build:
      context: .
      dockerfile: Dockerfile.test
      args:
        PYTHON_VERSION: "3.16"
    volumes:
      - ./test-results:/app/test-results
    environment:
      <<: *test-environment
    command: ["-v", "--tb=short", "-x"]
```

### 2단계: 테스트 스크립트 수정 (선택사항)

`scripts/test-python-versions.ps1`과 `scripts/test-python-versions.sh`의 기본 버전 목록을 수정합니다:

**PowerShell (`test-python-versions.ps1`):**
```powershell
$DefaultVersions = @("3.16", "3.15", "3.14", "3.13", "3.12", "3.11")
```

**Bash (`test-python-versions.sh`):**
```bash
DEFAULT_VERSIONS=("3.16" "3.15" "3.14" "3.13" "3.12" "3.11")
```

### 3단계: 테스트 실행

```powershell
docker compose -f docker-compose.python-matrix.yaml up --build python316 --abort-on-container-exit
```

---

## 오래된 버전 제거하기

Python 3.11 지원을 종료한다고 가정합니다.

### 1단계: docker-compose.python-matrix.yaml에서 서비스 제거

`python311` 서비스 블록을 삭제합니다.

### 2단계: 테스트 스크립트에서 제거

**PowerShell:**
```powershell
$DefaultVersions = @("3.15", "3.14", "3.13", "3.12")
```

**Bash:**
```bash
DEFAULT_VERSIONS=("3.15" "3.14" "3.13" "3.12")
```

### 3단계: requires-python 및 README 업데이트

`pyproject.toml`의 `requires-python`을 올리고 `uv lock`으로 잠금 파일을 갱신한 뒤,
`README.md`와 `README.ko.md`의 Prerequisites 섹션을 업데이트합니다.

---

## 파일 구조

```
├── Dockerfile.test                      # 테스트용 Docker 이미지
├── docker-compose.python-matrix.yaml    # 버전 매트릭스 Compose
├── scripts/
│   ├── test-python-versions.ps1         # Windows 테스트 스크립트
│   └── test-python-versions.sh          # Linux/macOS 테스트 스크립트
└── test-results/                        # 테스트 결과 (gitignore됨)
```

---

## 테스트 옵션 커스터마이징

### pytest 옵션 변경

`docker-compose.python-matrix.yaml`의 `command`를 수정합니다:

```yaml
# 기본 (상세 출력, 짧은 traceback, 첫 실패시 중단)
command: ["-v", "--tb=short", "-x"]

# 커버리지 포함
command: ["-v", "--cov=app", "--cov-report=term-missing"]

# 특정 테스트만 실행
command: ["-v", "tests/core/"]

# 마커로 필터링
command: ["-v", "-m", "not slow"]
```

### 환경 변수 변경

`x-test-environment` 앵커를 수정합니다:

```yaml
x-test-environment: &test-environment
  DATABASE_URL: "sqlite+aiosqlite:///:memory:"
  OIDC_ENABLED: "false"
  RATE_LIMIT_ENABLED: "false"
  LOG_LEVEL: "DEBUG"  # 추가
```

---

## 정리

테스트 후 리소스를 정리합니다:

```powershell
# 컨테이너만 정리
docker compose -f docker-compose.python-matrix.yaml down

# 컨테이너 + 볼륨 정리
docker compose -f docker-compose.python-matrix.yaml down -v

# 컨테이너 + 볼륨 + 이미지 정리
docker compose -f docker-compose.python-matrix.yaml down -v --rmi local
```

---

## 문제 해결

### 빌드 실패: 패키지 설치 오류

특정 Python 버전에서 패키지가 호환되지 않을 수 있습니다:

1. 에러 메시지에서 문제 패키지 확인
2. `pyproject.toml`의 의존성에 버전 제약(필요 시 environment marker) 추가
3. `uv lock`으로 `uv.lock` 재생성 (테스트 이미지는 `uv sync --locked`이므로 잠금 파일이 최신이어야 함)

```toml
# 예: 특정 Python 버전에서만 다른 버전 제약이 필요한 경우
dependencies = [
    "some-package>=1.0,<2.0; python_version < '3.13'",
]
```

### 테스트 실패: 버전별 차이

Python 버전 간 동작 차이가 있을 수 있습니다:

- `typing` 모듈 변경사항
- 새로운 문법 지원
- 표준 라이브러리 변경

코드에서 버전별 분기가 필요할 수 있습니다:

```python
import sys

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self
```

### Docker 빌드 캐시 문제

캐시를 무시하고 새로 빌드:

```powershell
docker compose -f docker-compose.python-matrix.yaml build --no-cache python314
```

---

## CI/CD 통합 (GitHub Actions 예시)

```yaml
name: Python Compatibility

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [python311, python312, python313, python314, python315]
    
    steps:
      - uses: actions/checkout@v4
        # 모노레포: 아래 명령은 wapul-be 디렉터리에서 실행
      
      - name: Build and test
        working-directory: wapul-be
        run: |
          docker compose -f docker-compose.python-matrix.yaml \
            up --build ${{ matrix.service }} \
            --abort-on-container-exit
      
      - name: Cleanup
        if: always()
        working-directory: wapul-be
        run: docker compose -f docker-compose.python-matrix.yaml down -v
```
