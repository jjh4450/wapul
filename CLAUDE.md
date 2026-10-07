# wapul

Monorepo.

- `wapul-fe/` — SvelteKit frontend (pnpm). Lint: `pnpm lint` (prettier + eslint + oxlint with anti-slop rules + `ui:check` story check).
- `wapul-be/` — FastAPI backend (uv, Python 3.11+; 3.14 in Docker). Lint/format: `uv run ruff check`, `uv run ruff format`. Test: `uv run pytest`.
- `wapul-ml/` — block-splitting model. Runs in Docker on GPU (host PyTorch is blocked by Windows app control). Library code sits in `wapul_ml/` by role (`data`, `features`, `models`, `evaluation`); experiments are jupytext notebooks in `notebooks/`. `wapul_ml/normalize.py` and `wapul_ml/units.py` are the model's input format, shared with the private data repo cloned at `wapul-ml/data/`; changing them means re-checking corpus and labels. Lint/format: `uv run ruff check`, `uv run ruff format` (same rules as the backend). Details: `docs/ml/`.
- `wapul-seg/` — deploy package for the ML model: TS in `js/` (vite library: normalize, web-tree-sitter parsing, units, AST facts, features) + Rust in `src/` built to WASM (takes the features, returns kinds and blocks: feature vocabulary, LightGBM, block grouping). Both copy the wapul-ml Python, which stays the original. The frontend calls one `segment(code, language)`. Anything that reads the syntax tree stays in TS. Lint (in `js/`): `pnpm lint` (prettier + eslint + oxlint with the same anti-slop rules as the frontend, vendored in `js/tools/oxlint/`); test: `pnpm test`. Rust: host cargo builds are blocked by Windows app control, so run `cargo fmt`, `cargo test`, `cargo clippy --target wasm32-unknown-unknown` in a `rust:1-slim` container with the repo mounted.
- Model to release: root `model/` holds only the packed `wapul-seg.model` and `model.json` (like `openapi/` a contract file outside the packages). Pack `wapul-ml/models/segmenter-vN/` with `cargo run --release --bin model-pack` in `wapul-seg/` (trees as evaluated, feature names hashed); never commit the text model. It ships in the package and the TS fetches it at first use; the WASM has no text-model parser. Released by CI as GitHub Releases; see `docs/ml/deploy.ko.md` for the decisions before changing the setup.
- Docs: unified mkdocs site at repo root (`docs/backend`, `docs/frontend`, Storybook built into `site/storybook/`). Local: `./scripts/serve-docs.sh`.
- UI components: shadcn-svelte MCP is registered in `.mcp.json`. Add components with `pnpm ui:add <name>` (auto-scaffolds a story); every component needs a story (`pnpm ui:check`, part of `pnpm lint`). See the `ui-component` skill.
- API contract: root `openapi/openapi.json` is generated from the backend (`wapul-be/scripts/export_openapi.py`) and committed by CI (`openapi.yml`) on main; don't hand-edit. Frontend types: `pnpm api:gen` → `wapul-fe/src/lib/api/schema.ts` (gitignored).
- Backend versioning: `vX.Y.Z` computed by CI (`be-docker.yml`); Y bumps on API contract change, Z otherwise, X via manual `major` dispatch. Never bump or tag versions by hand. Details: `CONTRIBUTING.md`.
- Segmenter versioning: `seg-vX.Y.Z` computed by CI (`seg-release.yml`); Y bumps when `model/wapul-seg.model` changes, Z otherwise, X via manual `major` dispatch. The release is the npm package `wapul-seg@X.Y.Z` (the `js/dist/` folder), published by CI (OIDC trusted publishing is blocked for this repo by npm/cli#9969, so the `NPM_TOKEN` secret is used until that is fixed). Never tag or publish by hand.
- Frontend versioning: `fe-vX.Y.Z` computed by CI (`fe-deploy.yml`, same rules); it force-pushes `deploy/fe` (main + `wapul-fe/VERSION`), which the host (Vercel) builds. Never push `deploy/fe` by hand.
- CI lives in root `.github/workflows/` (`be-*`, `fe-*`, `docs.yml`), path-filtered per package.

---

Behavioral guidelines to reduce common LLM coding mistakes. Merge with project-specific instructions as needed.

**Tradeoff:** These guidelines bias toward caution over speed. For trivial tasks, use judgment.

## 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them - don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

## 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it - don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: Every changed line should trace directly to the user's request.

## 4. Goal-Driven Execution

**Define success criteria. Loop until verified.**

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan:
```
1. [Step] → verify: [check]
2. [Step] → verify: [check]
3. [Step] → verify: [check]
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

---

**These guidelines are working if:** fewer unnecessary changes in diffs, fewer rewrites due to overcomplication, and clarifying questions come before implementation rather than after mistakes.

## Docs

Docs (`README`, `CONTRIBUTING*`, `docs/`) exist to help a newcomer follow this project's rules: setup, run, lint, test, and conventions.

- Don't update docs just because code changed. Update only when a rule or workflow a contributor must follow changes.
- Describe the current rules only. No change history, no "updated to...", no narration of past work. That goes in commit messages.
- Test before adding a line: does a newcomer need this to follow the project's rules? If not, leave it out.
