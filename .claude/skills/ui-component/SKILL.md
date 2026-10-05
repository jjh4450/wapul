---
name: ui-component
description: Add a shadcn-svelte component or a custom Svelte component to wapul-fe and wire it into Storybook. Use whenever a UI component is added, created, or installed under wapul-fe/src/lib/components.
---

# Adding a UI component (wapul-fe)

Only add the components the task actually needs. Never install extras to try things out.

## shadcn-svelte component

1. Look up the component with the `shadcn-svelte` MCP server (docs, demo code, Bits UI API). Do not guess props.
2. From `wapul-fe/`: `pnpm ui:add <name...>`
   - runs `shadcn-svelte add`, scaffolds `<name>.stories.svelte` for any component without a story, and runs prettier.
3. Replace the scaffolded `Default` story with real usage from the MCP demo:
   - compound components (card, dialog, ...) need their parts (`Header`, `Trigger`, `Content`, ...), the scaffold only renders `Root`. A scaffolded `<Dialog.Root />` renders nothing.
   - add one story per meaningful variant (e.g. `variant`, `size`) using `args`.
4. `pnpm lint` and `pnpm check`. shadcn output can break anti-slop rules: fix the code, never disable the rule.

## Custom component

Put it at `src/lib/components/<Name>.svelte` (or a folder with `index.ts` + `<name>.svelte`), then `pnpm ui:stories` to scaffold the story and fill it in as above.

## Rules

- `pnpm lint` runs `pnpm ui:check`, which fails if any component under `src/lib/components/` or `src/lib/components/ui/` has no story.
- Story titles: `UI/<Name>` for shadcn, `Components/<Name>` for custom.
