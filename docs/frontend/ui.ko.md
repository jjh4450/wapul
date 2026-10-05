# UI: Tailwind CSS와 shadcn-svelte

## Tailwind CSS 4

Tailwind 4는 설정 파일 없이 **CSS에서 설정**합니다. 진입점은 `src/routes/layout.css`이고, `+layout.svelte`가 이 파일을 불러옵니다.

`layout.css`가 하는 일:

- `tailwindcss`, `tw-animate-css`, `shadcn-svelte/tailwind.css`, Noto Sans 폰트(`@fontsource-variable/noto-sans`) import
- `@plugin '@tailwindcss/typography'`: 마크다운 본문용 `prose` 클래스
- `@custom-variant dark (&:is(.dark *))`: `.dark` 클래스 기반 다크 모드
- `:root` / `.dark`에 디자인 토큰(`--background`, `--primary` 등) 정의 (oklch 색상)

색상이나 반경을 바꿀 때는 컴포넌트가 아니라 이 토큰을 수정합니다.

prettier의 `prettier-plugin-tailwindcss`가 클래스 순서를 자동 정렬합니다 (`tailwindStylesheet: ./src/routes/layout.css`).

## shadcn-svelte

컴포넌트는 패키지로 설치하지 않고, CLI로 소스를 `src/lib/components/ui/`에 복사해 직접 소유합니다.

```bash
cd wapul-fe
pnpm ui:add button          # shadcn-svelte add + 스토리 생성 + prettier
```

### Storybook 연동

`src/lib/components/` 아래 모든 컴포넌트는 스토리가 있어야 합니다. `tools/ui-stories.ts`가 이를 관리합니다.

| 명령 | 동작 |
|------|------|
| `pnpm ui:add <name...>` | `shadcn-svelte add` 실행 후, 스토리 없는 컴포넌트에 `<name>.stories.svelte` 생성, prettier 적용 |
| `pnpm ui:stories` | 직접 만든 컴포넌트 등 스토리 없는 것에 스토리 생성 |
| `pnpm ui:check` | 스토리 없는 컴포넌트가 있으면 실패 (`pnpm lint`에 포함) |

- 대상: `src/lib/components/ui/`와 `src/lib/components/`의 직속 항목. 폴더(shadcn 형식)는 안에 `*.stories.svelte`가 하나 있어야 하고, 단일 `Name.svelte` 파일은 옆에 `Name.stories.svelte`가 있어야 합니다.
- 생성되는 스토리는 `Root`만 렌더링하는 최소 골격입니다(제목 `UI/<Name>`, 직접 만든 건 `Components/<Name>`). Card, Dialog 같은 복합 컴포넌트는 실제 사용 예로 채워야 합니다. 예: `<Dialog.Root />`만 있으면 아무것도 보이지 않습니다.
- `.storybook/preview.ts`가 `src/routes/layout.css`를 불러오므로 스토리에도 디자인 토큰이 적용되고, 툴바에서 라이트/다크를 바꿀 수 있습니다.

### shadcn-svelte MCP

루트 `.mcp.json`에 커뮤니티 MCP 서버 [shadcn-svelte-mcp](https://github.com/Michael-Obele/shadcn-svelte-mcp)가 등록되어 있습니다(공식 서버는 없음). Claude Code가 컴포넌트 문서, 데모 코드, Bits UI API를 조회해 props를 추측하지 않게 합니다. 처음 열 때 Claude Code가 프로젝트 MCP 사용 승인을 묻습니다. 컴포넌트 추가 절차는 `.claude/skills/ui-component/SKILL.md`에 있습니다.

`components.json` 주요 설정:

| 항목 | 값 | 의미 |
|------|----|------|
| `style` | `luma` | 컴포넌트 스타일 프리셋 |
| `tailwind.baseColor` | `olive` | 기본 색 팔레트 |
| `iconLibrary` | `tabler` | 아이콘: `@tabler/icons-svelte` |
| `aliases.*` | `#lib/...` | 생성 코드의 import 경로 ([`#lib` 별칭](index.md)) |

### 생성 코드와 린트

shadcn-svelte가 생성한 코드는 이 레포의 lint 규칙(특히 anti-slop)에 걸릴 수 있습니다. 컴포넌트를 추가한 뒤에는 `pnpm format`과 `pnpm lint`를 실행하고, 걸린 부분은 규칙을 끄지 말고 코드를 고칩니다. `src/lib/utils.ts`의 `any` 사용처럼 shadcn 타입 유틸에 필요한 예외는 이유를 적은 `eslint-disable` 주석으로 남깁니다.

`utils.ts`의 `cn()`은 `cn` 패키지에서 다시 내보낸 클래스 이름 결합 헬퍼입니다. shadcn 컴포넌트는 `tailwind-variants`로 변형(variant)을 정의합니다.
