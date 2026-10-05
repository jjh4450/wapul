# 린트와 포맷 (ruff)

백엔드는 [ruff](https://docs.astral.sh/ruff/) 하나로 린트와 포맷을 모두 처리합니다. 설정은 `wapul-be/pyproject.toml`의 `[tool.ruff]`에 있습니다.

## 명령어

`wapul-be/`에서 실행합니다.

```bash
uv run ruff check            # 린트
uv run ruff check --fix      # 자동 수정 가능한 항목 수정
uv run ruff format           # 포맷 적용
uv run ruff format --check   # 포맷 검사만 (CI와 동일)
```

커밋 전에 `ruff format`과 `ruff check`를 모두 통과시켜야 합니다. CI(`.github/workflows/be-ci.yml`)는 `ruff check`, `ruff format --check`, `pytest` 순서로 실행하며, 하나라도 실패하면 PR이 통과하지 않습니다.

## 포맷 규칙

- 줄 길이: 최대 120자 (`line-length = 120`)
- 그 외는 ruff 기본값(Black 호환): 공백 4칸 들여쓰기, 큰따옴표
- 대상 Python 버전: 3.11 (`target-version = "py311"`)

## 린트 규칙

| 규칙 | 의미 | 켠 이유 |
|------|------|---------|
| `E4`, `E7`, `E9`, `F` | ruff 기본 규칙 (문법 오류, 미사용 import/변수 등) | 기본 위생 |
| `B` (flake8-bugbear) | 가변 기본 인자, 예외 체인 누락(`raise ... from`) 등 흔한 버그 패턴 | 실제 버그로 이어지는 패턴 |
| `ANN401` | `Any` 타입 힌트 금지 | 타입을 포기하는 AI식 탈출구 차단 |
| `BLE` | `except Exception` 같은 넓은 예외 처리 금지 | 오류를 조용히 삼키는 코드 차단 |
| `PGH003` | 규칙 코드 없는 `# type: ignore` 금지 | 무엇을 무시하는지 명시 |

### FastAPI `Depends()` 예외

FastAPI의 `param = Depends(...)` 패턴은 `B008`(기본 인자에서 함수 호출)에 걸리지만, 의존성 주입의 정상적인 사용법입니다. 그래서 `[tool.ruff.lint.flake8-bugbear]`의 `extend-immutable-calls`에 `Depends`, `Query`, `Path`, `Body`, `Header`를 등록해 예외 처리합니다. 다른 FastAPI 파라미터 함수(`Cookie`, `Form` 등)를 쓰게 되면 이 목록에 추가하세요.

## `noqa` 사용 원칙

규칙을 피해야 할 정당한 이유가 있을 때만 `noqa`를 쓰고, **반드시 규칙 코드와 이유를 함께 적습니다.**

```python
# Good: 규칙 코드 + 이유
except Exception as e:  # noqa: BLE001 - 태스크가 죽지 않도록 모든 실패를 삼킴

# Bad: 무엇을, 왜 무시하는지 알 수 없음
except Exception:  # noqa
```

현재 의도적으로 남겨둔 넓은 예외 처리는 세 곳입니다.

| 위치 | 이유 |
|------|------|
| `app/core/auth/middleware.py` | 토큰 검증이 어떤 이유로 실패해도 미인증으로 진행 (실제 401은 `get_current_user`에서 처리) |
| `app/db/keepalive.py` | keep-alive 백그라운드 태스크가 일시적 DB 장애로 죽지 않도록 함 |
| `app/ratelimit/cloudflare.py` | Cloudflare IP 목록을 못 받아도 Fail-Safe 모드로 계속 동작 |
