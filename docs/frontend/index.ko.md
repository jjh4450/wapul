# 프론트엔드

`wapul-fe/` — SvelteKit 프론트엔드.

## 스택

| 영역 | 사용 기술 |
|------|-----------|
| 프레임워크 | SvelteKit 3 + Svelte 5 (**runes 모드 강제**), TypeScript 6 |
| 빌드 | Vite 8, `@sveltejs/adapter-static` (정적 사이트로 빌드) |
| 스타일 | Tailwind CSS 4 + `@tailwindcss/typography`, shadcn-svelte — [UI 가이드](ui.md) |
| 콘텐츠 | mdsvex (`.svx`, `.md` 파일을 Svelte 컴포넌트/라우트로 사용) |
| 이미지 | `@sveltejs/enhanced-img` (빌드 시 이미지 최적화) |
| 품질 | prettier + eslint + oxlint(anti-slop) — [린트 가이드](linting.md) |
| 테스트 | vitest (node + 브라우저 모드), Storybook 10 — [테스트 가이드](testing.md) |

## 개발

```bash
cd wapul-fe
pnpm install
pnpm dev            # 개발 서버
pnpm storybook      # Storybook (http://localhost:6006)
pnpm build          # 정적 빌드 → build/
```

## 검증

변경 후 아래를 통과해야 합니다. CI(`.github/workflows/fe-ci.yml`)도 같은 순서로 실행합니다.

```bash
pnpm format         # prettier 적용 (lint 전에 실행)
pnpm lint           # prettier 검사 + eslint + oxlint
pnpm check          # svelte-check 타입 검사
pnpm test           # vitest 전체 (브라우저 프로젝트 포함, 로컬 Chromium 필요)
```

## 디렉터리 구조

```
wapul-fe/
├── src/
│   ├── routes/            # 페이지 (+layout.svelte에서 layout.css 로드)
│   ├── lib/
│   │   ├── components/ui/ # shadcn-svelte 컴포넌트 (CLI로 추가)
│   │   ├── hooks/
│   │   ├── utils.ts       # cn() 등 shadcn 유틸
│   │   └── vitest-examples/  # vitest 예제 (참고용)
│   └── stories/           # Storybook 예제 스토리
├── tools/oxlint/anti-slop/   # vendoring한 oxlint 플러그인 (직접 수정 금지)
├── .storybook/
├── .oxlintrc.json
├── prettier.config.js
├── eslint.config.js
└── vite.config.ts         # SvelteKit + vitest 설정
```

## 컨벤션

### `#lib` import 별칭

`$lib` 대신 Node 표준 [subpath imports](https://nodejs.org/api/packages.html#subpath-imports)인 `#lib`을 씁니다 (`package.json`의 `imports`). shadcn-svelte 설정(`components.json`)도 이 별칭을 사용합니다.

```ts
import { cn } from '#lib/utils';
import favicon from '#lib/assets/favicon.svg';
```

### Svelte 5 runes

`vite.config.ts`에서 `node_modules` 밖의 모든 컴포넌트를 runes 모드로 강제합니다. `$state`, `$derived`, `$props`, `$effect`를 쓰고, 레거시 문법(`export let`, `$:`)은 쓰지 않습니다.

### pnpm

- `.npmrc`의 `engine-strict=true`: 의존성의 `engines`(Node 버전 등) 조건이 맞지 않으면 경고 대신 설치가 실패합니다.
- `pnpm-workspace.yaml`의 `allowBuilds`: 설치 스크립트 실행은 `sharp`, `esbuild`만 허용합니다. 빌드 스크립트가 필요한 패키지를 추가하면 여기에 등록해야 합니다.

## 에디터

- VS Code 추천 확장: `.vscode/extensions.json` (Svelte, Prettier, ESLint, Tailwind CSS). `*.css`는 Tailwind 언어 모드로 열립니다.
- Claude Code: `wapul-fe/.claude/settings.json`에서 공식 Svelte 플러그인(`sveltejs/ai-tools`)을 켭니다.

## 컴포넌트 카탈로그

UI 컴포넌트는 Storybook으로 문서화합니다. 배포된 Storybook: [storybook/](../storybook/index.html)
