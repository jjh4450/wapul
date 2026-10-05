# Frontend

`wapul-fe/` — SvelteKit frontend.

Stack: SvelteKit 3 + Svelte 5 (runes mode enforced), TypeScript, Vite, `adapter-static`, Tailwind CSS 4 + shadcn-svelte, mdsvex, enhanced-img, vitest, Storybook 10.

## Development

```bash
cd wapul-fe
pnpm install
pnpm dev            # dev server
pnpm storybook      # Storybook (http://localhost:6006)
```

## Checks

```bash
pnpm format         # apply prettier first
pnpm lint           # prettier check + eslint + oxlint (anti-slop rules)
pnpm check          # svelte-check type checking
pnpm test           # vitest (browser projects need local Chromium)
```

CI runs only the node (`server`) vitest project. Imports use the `#lib` subpath alias instead of `$lib`.

Detailed guides (UI, linting, testing) are written in Korean; see the Korean pages for the full reference.

## Component catalog

UI components are documented in Storybook. Deployed Storybook: [storybook/](../../storybook/index.html)
