# 프론트엔드

`wapul-fe/` — SvelteKit 프론트엔드 (pnpm). 배포는 Vercel에서 합니다.

## 개발

```bash
cd wapul-fe
pnpm install
pnpm dev            # 개발 서버
pnpm storybook      # Storybook (http://localhost:6006)
```

## 검증

```bash
pnpm lint           # prettier + eslint + oxlint (anti-slop 규칙)
pnpm check          # svelte-check 타입 검사
pnpm test           # vitest (브라우저 모드 포함)
```

## 컴포넌트 카탈로그

UI 컴포넌트는 Storybook으로 문서화합니다. 배포된 Storybook: [storybook/](../storybook/index.html)
