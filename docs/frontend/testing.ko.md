# 테스트와 Storybook

## vitest 프로젝트

`vite.config.ts`의 `test.projects`에 프로젝트 3개가 있습니다.

| 프로젝트 | 환경 | 대상 파일 | Chromium |
|----------|------|-----------|----------|
| `server` | node | `src/**/*.{test,spec}.{js,ts}` (`.svelte.` 제외) | 불필요 |
| `client` | 브라우저 (Playwright) | `src/**/*.svelte.{test,spec}.{js,ts}` | 필요 |
| `storybook` | 브라우저 (Playwright) | 모든 story를 테스트로 렌더링 | 필요 |

- **화면과 컴포넌트의 동작은 story의 `play` 함수로 검증합니다.** 사용자가 보는 상태(불러오는 중, 빈 목록, 에러 등)마다 story를 두고, `play`에서 클릭·입력한 뒤 결과를 확인합니다. 같은 시나리오를 `*.svelte.spec.ts`에 다시 쓰지 않습니다.
- **UI가 아닌 로직은 `*.spec.ts`(server)로 작성합니다.** 예: `src/lib/study.spec.ts`, `src/lib/api/client.spec.ts`. CI에서 도는 테스트는 이것뿐입니다.
- 화면 컴포넌트는 라우터에 기대지 않습니다. `id`는 props로 받고 이동은 콜백(`onsaved` 등)으로 넘기며, `+page.svelte`가 `$app/state`와 `goto`로 연결합니다. vitest에서는 SvelteKit 라우터가 돌지 않기 때문입니다.
- `expect.requireAssertions: true`: assertion이 하나도 없는 테스트는 실패합니다.
- 모듈 mock(`vi.mock`)은 anti-slop `no-module-mocking` 규칙으로 금지됩니다. 의존성은 인터페이스로 주입해 교체합니다.

### 가짜 API

백엔드 없이 화면을 돌릴 때는 `src/lib/api/fake.ts`의 `FakeApi`로 `fetch`를 바꿔 끼웁니다. 화면은 실제 API 클라이언트를 그대로 쓰고 응답만 가짜가 정합니다. 데이터는 `src/lib/api/fixtures.ts`에 API 타입으로 적어 두어, API 계약이 바뀌면 `pnpm check`에서 드러납니다.

```svelte
<script module lang="ts">
  const api = new FakeApi([
    ['GET /v1/records/:id', reply(record)],
    ['PATCH /v1/records/:id/answers', empty()]
  ]);
</script>

<Story
  name="SavesOnlyChangedAnswers"
  beforeEach={() => api.install()}
  play={async ({ canvas, userEvent }) => {
    // ...입력한 뒤
    await expect(api.callsTo('PATCH', '/v1/records/record-1/answers')).toHaveLength(1);
  }}
/>
```

- `install()`은 되돌리는 함수를 돌려주므로 `beforeEach`에서 그대로 반환합니다.
- 정하지 않은 요청은 501로 응답하고 콘솔에 에러를 남깁니다.
- 화면 story는 story마다 가짜 API가 달라서 `autodocs`(여러 story를 한 페이지에 렌더)를 쓰지 않습니다.

### 실행

```bash
pnpm test                                  # 전체 (Chromium 필요)
pnpm exec vitest run --project server      # node 테스트만 (CI와 동일)
pnpm exec vitest run --project client      # 컴포넌트 테스트만
```

브라우저 프로젝트를 로컬에서 처음 돌릴 때는 Chromium과 Linux 시스템 라이브러리를 한 번 설치해야 합니다.

```bash
pnpm exec playwright install chromium            # 이미 ~/.cache/ms-playwright에 있으면 생략
sudo pnpm exec playwright install-deps chromium  # libnss3, libnspr4 등 (Linux/WSL)
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
