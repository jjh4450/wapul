# 린트와 포맷

`pnpm lint`는 네 단계를 순서대로 실행하고, 하나라도 실패하면 멈춥니다.

```bash
pnpm format   # prettier --write . (먼저 실행)
pnpm lint     # prettier --check . && eslint . && oxlint && pnpm ui:check
```

| 단계 | 도구 | 역할 |
|------|------|------|
| 1 | prettier | 포맷 |
| 2 | eslint | TypeScript, Svelte, Storybook 규칙 |
| 3 | oxlint | anti-slop 규칙 (AI가 자주 만드는 "근거 없는" 패턴 차단) |
| 4 | `ui:check` | 스토리 없는 컴포넌트 검출 ([UI 문서](ui.md)) |

## prettier

`prettier.config.js`:

- **공백 2칸** 들여쓰기 (탭 사용 안 함)
- 작은따옴표, trailing comma 없음, 줄 길이 100
- 플러그인: `prettier-plugin-svelte`, `prettier-plugin-tailwindcss` (Tailwind 클래스 정렬)

`.prettierignore`로 `tools/oxlint/anti-slop/`(vendoring한 코드)를 제외합니다. 원본과의 diff를 작게 유지하기 위해서입니다.

## eslint

`eslint.config.js` (flat config): `@eslint/js` 권장 + `typescript-eslint` 권장 + `eslint-plugin-svelte` 권장 + `eslint-plugin-storybook` 권장, 마지막에 `eslint-config-prettier`로 포맷 관련 규칙을 끕니다. `.gitignore`에 있는 경로는 검사하지 않습니다.

TypeScript 프로젝트라 `no-undef`는 끕니다 (typescript-eslint 권장).

## oxlint + anti-slop

[anti-slop](https://github.com/dmmulroy/anti-slop)은 낮은 근거(low-evidence) 패턴을 거부하는 oxlint JS 플러그인입니다. 타입을 포기하는 탈출구(`unknown`, `as` 연쇄, 런타임 `typeof`)나 읽기 어려운 코드를 막습니다. `.oxlintrc.json`에서 **모든 규칙을 `error`로** 켭니다.

| 규칙 | 금지하는 것 |
|------|-------------|
| `no-array-filter-map` | `.filter().map()`처럼 배열을 연속으로 두 번 순회 (iterator helper나 단일 변환 사용) |
| `no-reduce-accumulator-copy` | `reduce` 안에서 누적값을 매번 복사 (2차 시간 복잡도) |
| `oxc/no-accumulating-spread` | 누적값을 spread로 매번 복사 (oxlint 내장 규칙) |
| `no-chained-type-assertions` | `x as A as B` 같은 연쇄 타입 단언 |
| `no-conditional-empty-object-spread` | `...(cond ? { a } : {})`로 필드를 생략하는 패턴 |
| `no-known-value-widening` | 이미 알고 있는 값을 넓은 타입으로 흘려 정보를 버리는 것 |
| `no-widen-then-assert` | 값을 넓혔다가 다시 좁은 타입으로 단언하는 것 |
| `no-module-mocking` | `vi.mock` 같은 모듈 mock (실제 인터페이스로 의존성 교체) |
| `no-object-parameters` | `object` 타입 파라미터 (소유자가 정의한 타입을 경계에서 파싱) |
| `no-reflect-apply`, `no-reflect-get` | `Reflect.apply`, `Reflect.get` (타입 있는 호출/접근 사용) |
| `no-runtime-typeof` | 런타임 `typeof` 검사 (외부 값은 I/O 경계에서 의미 있는 타입으로 디코딩) |
| `no-shape-in-symbol-names` | 심볼 이름에 "shape" 포함 (구조가 아니라 도메인 역할로 이름 짓기) |
| `no-unknown-parameters` | `unknown` 파라미터 (`cause`, 타입 가드 대상 제외) |
| `no-unknown-returns` | `unknown` / `Promise<unknown>` 반환 |
| `no-unknown-type-aliases` | `unknown`으로 풀리는 타입 별칭 |
| `no-unsafe-dictionary-type` | 값 타입이 `unknown`, `any`, `object`, `{}`인 딕셔너리 타입 |
| `require-readable-spacing` | 선언과 논리적 문장 그룹 사이의 빈 줄 (자동 수정 가능) |
| `require-safety-comment-for-type-assertion` | `as` 단언마다 근처에 `SAFETY` 주석 (`as const` 제외) |

```ts
// require-safety-comment-for-type-assertion
// SAFETY: 서버가 항상 이 형태로 응답함을 API 계약으로 보장
const user = data as User;
```

`require-readable-spacing`은 `pnpm exec oxlint --fix`로 자동 수정할 수 있습니다.

검사 제외(`ignorePatterns`): `.claude/`, `.storybook/`, `.svelte-kit/`, `tools/oxlint/anti-slop/`.

### 버전 고정

`oxlint`와 `@oxlint/plugins`는 **`1.86.0`으로 정확히 고정**합니다 (`^` 없음). anti-slop이 oxlint의 JS 플러그인 API를 직접 쓰기 때문에, 버전을 올릴 때는 플러그인이 그대로 동작하는지 `pnpm lint`로 확인한 뒤 두 패키지를 함께 올립니다.

## vendoring한 코드

`tools/oxlint/anti-slop/`은 외부 코드를 복사해 둔 것입니다. **직접 수정하지 말고**, 바꿔야 하면 아래 절차를 따릅니다.

| 경로 | 출처 | 기록 |
|------|------|------|
| `tools/oxlint/anti-slop/` | [dmmulroy/anti-slop](https://github.com/dmmulroy/anti-slop) `skills/install-anti-slop/assets/anti-slop/` | `UPSTREAM.md` |
| `.../vendor/eslint-stylistic/` | [ESLint Stylistic](https://github.com/eslint-stylistic/eslint-stylistic)의 `padding-line-between-statements` (MIT) | `vendor/eslint-stylistic/UPSTREAM.md`, `LICENSE` |

- `require-readable-spacing` 규칙이 ESLint Stylistic의 `padding-line-between-statements`를 oxlint API로 옮긴 코드를 사용합니다. MIT `LICENSE` 파일은 반드시 함께 유지합니다.
- `effect/` 디렉터리(Effect 라이브러리 전용 규칙)는 복사만 되어 있고 **켜져 있지 않습니다**.

### 업데이트 절차

1. upstream의 특정 커밋을 정해 해당 디렉터리를 비교합니다.
2. 필요한 변경을 옮기되, 로컬 적응 사항(`UPSTREAM.md`에 기록)은 유지합니다.
3. `UPSTREAM.md`의 커밋 해시와 변경 사항을 갱신합니다.
4. `pnpm lint`와 `pnpm check`로 확인합니다.

!!! note "UPSTREAM.md의 테스트 언급"
    `vendor/eslint-stylistic/UPSTREAM.md`는 `require-readable-spacing.test.ts` 등 RuleTester 테스트와 `pnpm sync:skill-assets`를 언급하지만, 이 파일들과 스크립트는 upstream 레포에만 있고 이 레포에는 복사되지 않았습니다. 규칙 동작은 upstream에서 검증된 것을 그대로 가져온 상태입니다.
