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

`src/lib/components/` 아래 모든 컴포넌트는 스토리가 있어야 합니다. 스토리 하나가 Storybook 화면, 자동 문서, 테스트를 함께 만듭니다.

```
pnpm ui:add button
  1. shadcn-svelte add  → src/lib/components/ui/button/ 에 소스 복사
  2. 스토리 골격 생성     → button/button.stories.svelte (스토리가 없을 때만)
  3. prettier
        ↓
Storybook: src/**/*.stories.svelte 를 자동 인식 → 사이드바 UI/Button, 자동 문서(autodocs)
        ↓
pnpm test: addon-vitest가 스토리를 테스트로 실행 (렌더링, play, a11y)
```

| 명령 | 동작 |
|------|------|
| `pnpm ui:add <name...>` | `shadcn-svelte add` 실행 후, 스토리 없는 컴포넌트에 `<name>.stories.svelte` 생성, prettier 적용 |
| `pnpm ui:stories` | 직접 만든 컴포넌트 등 스토리 없는 것에 스토리 생성 |
| `pnpm ui:check` | 스토리 없는 컴포넌트가 있으면 실패 (`pnpm lint`에 포함) |

- 대상: `src/lib/components/ui/`와 `src/lib/components/`의 직속 항목. 폴더(shadcn 형식)는 안에 `*.stories.svelte`가 하나 있어야 하고, 단일 `Name.svelte` 파일은 옆에 `Name.stories.svelte`가 있어야 합니다.
- 이미 스토리가 있는 컴포넌트는 건드리지 않습니다. shadcn 컴포넌트를 다시 받아도 작성한 스토리는 유지됩니다.
- 스토리에는 앱과 같은 `layout.css`가 적용됩니다. 툴바의 테마 버튼으로 다크 모드도 확인합니다.

#### 골격을 실제 사용 예로 채우기

생성된 골격은 `index.ts`가 내보내는 `Root`만 렌더링합니다.

```svelte
<script module lang="ts">
  import { defineMeta } from '@storybook/addon-svelte-csf';
  import * as Button from './index.js';

  const { Story } = defineMeta({
    title: 'UI/Button',
    component: Button.Root,
    tags: ['autodocs']
  });
</script>

<Story name="Default">
  <Button.Root>Button</Button.Root>
</Story>
```

골격 그대로 두지 말고 실제 사용 예로 바꿉니다.

- **복합 컴포넌트**(Card, Dialog 등)는 부품(`Header`, `Trigger`, `Content` 등)을 조합해 씁니다. `<Dialog.Root />`만 있으면 화면에 아무것도 나오지 않습니다.
- **변형**(`variant`, `size` 등)마다 스토리를 하나씩 둡니다.

```svelte
<Story name="Outline">
  <Button.Root variant="outline">Outline</Button.Root>
</Story>

<Story name="Small">
  <Button.Root size="sm">Small</Button.Root>
</Story>
```

- 상호작용(클릭, 포커스 이동, 위치)은 `play` 함수로, 접근성은 `addon-a11y`로 검사합니다. 둘 다 실제 브라우저에서 돌기 때문에 `pnpm test`에 Chromium이 필요합니다 ([테스트 문서](testing.md)).

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
