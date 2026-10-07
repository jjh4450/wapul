# Contributing to wapul

**[한국어 버전](CONTRIBUTING.ko.md)**

Thank you for your interest in contributing to wapul. This document describes the contribution process and guidelines.

This repository is a monorepo:

| Directory | Description |
|-----------|-------------|
| `wapul-be/` | Backend (FastAPI, uv) |
| `wapul-fe/` | Frontend (SvelteKit, pnpm) |
| `wapul-ml/` | Block-splitting model: training and experiments (Python, runs in Docker) |
| `wapul-seg/` | The model packaged for the browser: TypeScript module + Rust WASM (pnpm, cargo) |
| `model/` | The trained model files the segmenter ships, copied from `wapul-ml/models/` by hand |

## Table of Contents

- [Before You Start](#before-you-start)
- [Development Environment](#development-environment)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Versioning and Releases](#versioning-and-releases)
- [Review Process](#review-process)

---

## Before You Start

### Check Existing Issues

Before starting work, check if there's already an issue or PR for your intended change:

1. Search [existing issues](https://github.com/jjh4450/wapul/issues)
2. Search [existing pull requests](https://github.com/jjh4450/wapul/pulls)

If none exists, create an issue first to discuss the change.

### Issue First Policy

**All non-trivial changes require an issue first.**

- Bug fixes: Create a bug report issue
- New features: Create a feature request issue
- Documentation: Small fixes can go directly to PR

This ensures your work aligns with project direction and prevents duplicate effort.

---

## Development Environment

### Prerequisites

- Python 3.11+ (3.14 recommended)
- [uv](https://docs.astral.sh/uv/)
- Git
- Docker (optional, for PostgreSQL testing)

### Setup (backend)

```bash
# Fork and clone
git clone https://github.com/YOUR_USERNAME/wapul.git
cd wapul/wapul-be

# Install dependencies (dev group included by default, .venv created automatically)
uv sync

# Copy environment file
cp .env.example .env
```

The frontend (`wapul-fe/`) uses pnpm; run `pnpm format`, then make sure `pnpm lint`, `pnpm check` and `pnpm test` pass. See the [frontend docs](https://jjh4450.github.io/wapul/frontend/).

The segmenter (`wapul-seg/`) has two parts, both checked in CI:

- Rust (`src/`): `cargo fmt --check`, `cargo clippy --target wasm32-unknown-unknown`, `cargo test --release`. Building the WASM needs the `wasm32-unknown-unknown` target and `wasm-bindgen-cli` at the version in `Cargo.lock`; `scripts/build-wasm.sh` writes `pkg/`, which the TypeScript imports.
- TypeScript (`js/`): `pnpm install`, `pnpm format`, then `pnpm lint`, `pnpm check`, `pnpm test`. `pnpm test` compares every stage with the Python model on `tests/cases.json`; regenerate that file with `tests/make_cases.py` whenever `wapul-ml`'s `normalize.py`, `units.py` or `features/` change.

The TypeScript and Rust in `wapul-seg/` copy the Python in `wapul-ml/`, which stays the original: change the Python first, then the copies, then make the parity test pass. Node rules for the languages the Python side does not have live only in `js/src/languages.ts`. See [Deploy](https://jjh4450.github.io/wapul/ml/deploy/) for the decisions behind this layout.

### Lint and Format

**Backend changes must pass ruff lint and format checks** (enforced in CI).

```bash
uv run ruff format   # apply formatting
uv run ruff check    # lint
```

See the [Linting & Formatting guide](https://jjh4450.github.io/wapul/backend/development/linting/) for the rule set and `noqa` policy.

### Running Tests

**All code changes must pass tests.**

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app --cov-report=term-missing

# Run specific test file
uv run pytest tests/core/test_auth.py
```

### Running the Server

```bash
uv run uvicorn app.main:app --reload --port 2614
```

---

## Coding Standards

### Python Style

This project follows **PEP 8** with the following specifics:

- Formatting is decided by `ruff format` (max line length 120)
- Use type hints for all function parameters and return values
- Use `"""docstrings"""` for all public functions, classes, and modules

### Type Hints

```python
# Good
def create_item(self, data: ItemCreate) -> Item:
    """Create a new item."""
    ...

# Bad
def create_item(self, data):
    ...
```

### Docstrings

Use Korean or English, but be consistent within a file:

```python
def get_owned_item(self, item_id: UUID, owner_id: str) -> Item:
    """
    소유자의 Item 조회

    비즈니스 규칙:
    - Item이 존재해야 함
    - 요청자가 소유자여야 함

    :param item_id: Item ID
    :param owner_id: 요청자 ID (OIDC sub)
    :raises ItemNotFoundError: Item이 없거나 소유자가 다를 때
    """
```

### Architecture Principles

1. **Layered Architecture**: Router → Service → Domain → Data
2. **Domain Exceptions**: Use `DomainException` subclasses, not HTTP exceptions in services
3. **UTC Storage**: All datetimes stored as UTC naive in database
4. **Owner Isolation**: All resources filtered by `owner_id`

### File Naming

| Type | Pattern | Example |
|------|---------|---------|
| Router | `app/api/v1/{domain}.py` | `items.py` |
| Service | `app/domain/{domain}/service.py` | `service.py` |
| Schema | `app/domain/{domain}/schema/dto.py` | `dto.py` |
| Model | `app/models/{domain}.py` | `item.py` |
| Test | `tests/domain/{domain}/test_*.py` | `test_service.py` |

---

## Commit Guidelines

### Commit Message Format

Follow the conventional commit format:

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Code style (formatting, no logic change) |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `test` | Adding or updating tests |
| `chore` | Build process, dependencies, etc. |

### Examples

```
feat(be): add current user profile endpoint

Return the current user's profile built from OIDC token claims.

- Add UserProfile model
- Add GET /v1/users/me endpoint
- Add service and router tests

Closes #42
```

```
fix(ratelimit): ignore spoofed X-Forwarded-For from untrusted peers

Only trust forwarding headers when the peer is in TRUSTED_PROXY_IPS.

Fixes #87
```

### Commit Principles

1. **Atomic commits**: Each commit should be a single logical change
2. **Buildable**: Each commit should pass all tests
3. **Descriptive**: Subject line should describe what, body explains why
4. **Reference issues**: Use `Closes #N` or `Fixes #N` in footer

---

## Pull Request Process

### Before Submitting

- [ ] All tests pass (`uv run pytest`)
- [ ] Code follows style guidelines
- [ ] New code has appropriate tests
- [ ] Documentation updated if needed
- [ ] Commit messages follow guidelines
- [ ] Rebased on latest `main`

### PR Title Format

Same as commit message subject:

```
feat(be): add current user profile endpoint
fix(auth): handle expired JWKS cache gracefully
docs: update installation guide for Windows
```

### PR Description

Use the PR template. Include:

1. **Summary**: What this PR does
2. **Related Issue**: Link to issue (`Closes #N`)
3. **Changes**: List of changes made
4. **Test Plan**: How to verify the changes

### Size Matters

- Keep PRs focused and reasonably sized
- Large changes should be split into logical, reviewable chunks
- If a PR grows too large, discuss splitting it

---

## Versioning and Releases

### Version Format

The backend uses `vX.Y.Z` (starting at 1.0.0):

| Part | Bumped when | By |
|------|-------------|----|
| X | API path version changes (`/v1` → `/v2`) | A maintainer runs the Backend Docker workflow manually with the `major` input |
| Y | API contract changes (`info.version` in `openapi/openapi.json`, a hash of the spec) | CI, automatically |
| Z | Every other release | CI, automatically |

Don't make breaking changes under `/v1`. Add breaking changes under `/v2`.

The frontend uses `fe-vX.Y.Z` with the same rules (Y bumps when the frontend ships against a new API contract; X via the Frontend Deploy workflow's `major` input). On each frontend release CI tags the `main` commit and force-updates the `deploy/fe` branch with a `wapul-fe/VERSION` file; the hosting provider builds and deploys from `deploy/fe`. Don't push to `deploy/fe` or create `fe-v*` tags by hand.

The segmenter uses `seg-vX.Y.Z`: Y bumps when the model files in `model/` change, Z on every other release, X via the Segmenter Release workflow's `major` input (when `segment()`'s results or call shape change). Each release is the npm package `wapul-seg@X.Y.Z`, published from `wapul-seg/js` by CI through npm trusted publishing (no token), plus a `seg-vX.Y.Z` tag. The frontend pins it in `package.json`. Don't create `seg-v*` tags or publish by hand. To ship a new model, copy the files from `wapul-ml/models/segmenter-vN/` into `model/` in a PR; CI versions and releases it.

### How It Works

Versioning is **fully automated** via CI/CD. When backend changes are merged to `main`:

1. GitHub Actions compares the last release tag and API contract to compute the next version
2. Docker image is built and tagged `X.Y.Z`, `X.Y`, `X`, and `latest`
3. `[Unreleased]` section in CHANGELOG.md is replaced with the actual version
4. The release tag and GitHub Release are created automatically

Every week the last release is rebuilt under the same tags to pick up base image and system package security patches. To pin an exact image, use its digest (`@sha256:...`) instead of a tag.

**Contributors should never manually set or bump version numbers.**

### What Contributors Should Do

When your PR includes user-facing changes, update `wapul-be/CHANGELOG.md` under the `[Unreleased]` section:

```markdown
## [Unreleased]

### Added
- **New feature description** (`scope`): Details of what was added

### Fixed
- **Bug description** (`scope`): What was fixed and why
```

Use the appropriate category: Added, Changed, Deprecated, Removed, Fixed, or Security.

If `[Unreleased]` shows `_No unreleased changes._`, replace it with your entry:

```markdown
## [Unreleased]

### Added
- **Current user profile** (`users`): Added `GET /v1/users/me` endpoint
```

The CI pipeline will handle converting `[Unreleased]` to the actual version on release.

### What NOT to Do

- Do **not** create version tags manually
- Do **not** edit version entries below `[Unreleased]` (those are already released)
- Do **not** modify `APP_VERSION` in `.env` or `config.py` — it's injected at build time

---

## Review Process

### What Reviewers Look For

1. **Correctness**: Does the code do what it claims?
2. **Tests**: Are edge cases covered?
3. **Architecture**: Does it follow project patterns?
4. **Performance**: Any obvious performance issues?
5. **Security**: Any security concerns?

### Responding to Reviews

- Address all comments before requesting re-review
- Explain your reasoning if you disagree
- Mark conversations as resolved after addressing

### Review Timeline

- Maintainers aim to provide initial review within 3-5 business days
- Complex PRs may take longer
- Ping in the PR if no response after a week

---

## Getting Help

- **Bugs**: Create an [Issue](https://github.com/jjh4450/wapul/issues)
- **Security**: See [SECURITY.md](SECURITY.md)

---

*Good code comes from good reviews. Thank you for contributing.*
