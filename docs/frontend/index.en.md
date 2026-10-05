# Frontend

`wapul-fe/` — SvelteKit frontend (pnpm), deployed on Vercel.

## Development

```bash
cd wapul-fe
pnpm install
pnpm dev            # dev server
pnpm storybook      # Storybook (http://localhost:6006)
```

## Checks

```bash
pnpm lint           # prettier + eslint + oxlint (anti-slop rules)
pnpm check          # svelte-check type checking
pnpm test           # vitest (including browser mode)
```

## Component catalog

UI components are documented in Storybook. Deployed Storybook: [storybook/](../../storybook/index.html)
