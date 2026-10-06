<div align="center">

<a id="top"></a>

# wapul-fe

**wapul 프론트엔드 (SvelteKit)**

[![SvelteKit](https://img.shields.io/badge/SvelteKit-3-FF3E00?style=flat-square&logo=svelte&logoColor=white)](https://svelte.dev/docs/kit)
[![Svelte](https://img.shields.io/badge/Svelte-5-FF3E00?style=flat-square&logo=svelte&logoColor=white)](https://svelte.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-6-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-4-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vite.dev)
[![Vitest](https://img.shields.io/badge/Vitest-4-6E9F18?style=flat-square&logo=vitest&logoColor=white)](https://vitest.dev)
[![Storybook](https://img.shields.io/badge/Storybook-10-FF4785?style=flat-square&logo=storybook&logoColor=white)](https://storybook.js.org)
[![Docs](https://img.shields.io/badge/Docs-Online-FF3E00?style=flat-square&logo=readme&logoColor=white)](https://jjh4450.github.io/wapul/frontend/)

**[문서](https://jjh4450.github.io/wapul/frontend/)**

</div>

---

```bash
pnpm install
pnpm dev        # 개발 서버 (/v1 요청은 localhost:2614의 wapul-be로 프록시)
pnpm format     # prettier 적용
pnpm lint       # prettier 검사 + eslint + oxlint(anti-slop) + 스토리 검사
pnpm check      # 타입 검사
pnpm test       # vitest (브라우저 프로젝트는 로컬 Chromium 필요)
pnpm storybook  # Storybook
pnpm ui:add button  # shadcn 컴포넌트 추가 + 스토리 생성
pnpm api:gen    # ../openapi/openapi.json → src/lib/api/schema.ts (백엔드 API 타입)
```

배포 빌드에서는 `VITE_API_BASE_URL`에 백엔드 주소를 넣어야 합니다.

자세한 내용은 문서 사이트의 [프론트엔드 문서](https://jjh4450.github.io/wapul/frontend/)를 참고하세요 (원본: `docs/frontend/`).
