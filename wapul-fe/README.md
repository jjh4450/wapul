# wapul-fe

wapul 프론트엔드 (SvelteKit, pnpm). Vercel로 배포합니다.

```bash
pnpm install
pnpm dev        # 개발 서버
pnpm format     # prettier 적용
pnpm lint       # prettier 검사 + eslint + oxlint(anti-slop)
pnpm check      # 타입 검사
pnpm test       # vitest (브라우저 프로젝트는 로컬 Chromium 필요)
pnpm storybook  # Storybook
```

자세한 내용은 문서 사이트의 [프론트엔드 문서](https://jjh4450.github.io/wapul/frontend/)를 참고하세요 (원본: `docs/frontend/`).

## 프로젝트 재생성

이 프로젝트는 [`sv`](https://github.com/sveltejs/cli)로 만들었습니다. 같은 구성으로 다시 만들려면:

```sh
pnpm dlx sv@1.1.0 create --template minimal --types ts --add prettier eslint tailwindcss="plugins:typography" sveltekit-adapter="adapter:static" ai-tools="ide:claude-code+delivery:plugin" storybook enhanced-img vitest="usages:unit,component" mdsvex --install pnpm wapul-fe
```

생성 후 추가한 것: shadcn-svelte, oxlint + anti-slop(`tools/oxlint/anti-slop/`), prettier 공백 2칸 설정.
