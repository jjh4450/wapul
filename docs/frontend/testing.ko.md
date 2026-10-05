# 테스트와 Storybook

## vitest 프로젝트

`vite.config.ts`의 `test.projects`에 프로젝트 3개가 있습니다.

| 프로젝트 | 환경 | 대상 파일 | Chromium |
|----------|------|-----------|----------|
| `server` | node | `src/**/*.{test,spec}.{js,ts}` (`.svelte.` 제외) | 불필요 |
| `client` | 브라우저 (Playwright) | `src/**/*.svelte.{test,spec}.{js,ts}` | 필요 |
| `storybook` | 브라우저 (Playwright) | 모든 story를 테스트로 렌더링 | 필요 |

- 순수 로직은 `*.spec.ts`(server), 컴포넌트는 `*.svelte.spec.ts`(client)로 작성합니다. 예제: `src/lib/vitest-examples/`.
- `expect.requireAssertions: true`: assertion이 하나도 없는 테스트는 실패합니다.
- 모듈 mock(`vi.mock`)은 anti-slop `no-module-mocking` 규칙으로 금지됩니다. 의존성은 인터페이스로 주입해 교체합니다.

### 실행

```bash
pnpm test                                  # 전체 (Chromium 필요)
pnpm exec vitest run --project server      # node 테스트만 (CI와 동일)
pnpm exec vitest run --project client      # 컴포넌트 테스트만
```

브라우저 프로젝트를 로컬에서 처음 돌릴 때는 Chromium을 한 번 설치해야 합니다 (약 100MB 이상).

```bash
pnpm exec playwright install chromium
```

### CI

**CI(`fe-ci.yml`)는 `server` 프로젝트만 실행합니다.** 브라우저 프로젝트는 Chromium 설치가 무거워 CI에서 제외했습니다. 컴포넌트나 story를 바꿨다면 PR 전에 로컬에서 `pnpm test`를 돌려 주세요.

## Storybook

Storybook 10 (`@storybook/sveltekit`)으로 컴포넌트를 문서화합니다.

```bash
pnpm storybook          # 개발 서버 (http://localhost:6006)
pnpm build-storybook    # 정적 빌드 → storybook-static/
```

- 스토리 위치: `src/**/*.stories.@(js|ts|svelte)`, `src/**/*.mdx`. Svelte CSF(`.stories.svelte`) 형식을 씁니다 (`@storybook/addon-svelte-csf`).
- 애드온: `addon-docs`(자동 문서), `addon-a11y`(접근성 검사), `addon-vitest`(story를 vitest로 실행), `@chromatic-com/storybook`.
- 접근성: `.storybook/preview.ts`의 `a11y.test`가 `'todo'`라 위반은 테스트 UI에만 표시되고 실패로 처리되지 않습니다. 실패로 막으려면 `'error'`로 바꿉니다.
- `src/stories/`의 Button/Header/Page는 Storybook 기본 예제입니다.

### 배포

문서 사이트 배포(`.github/workflows/docs.yml`) 때 `pnpm build-storybook`으로 빌드해 사이트의 `/storybook/` 경로에 함께 올립니다. 정적 빌드라 Chromium은 필요 없습니다.
