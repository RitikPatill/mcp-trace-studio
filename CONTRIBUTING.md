# Contributing

## Prerequisites

| Tool | Version |
|------|---------|
| [uv](https://docs.astral.sh/uv/) | ≥ 0.5 |
| [pnpm](https://pnpm.io/) | ≥ 9 |
| [just](https://just.systems/) | ≥ 1.36 |
| Python | ≥ 3.11 |
| Node.js | ≥ 20 |

## Dev setup

```bash
cd backend && uv sync
cd frontend && pnpm install
```

## Running tests and lint

```bash
just test                  # pytest -v
just lint                  # ruff check + ruff format (backend)
cd frontend && pnpm lint   # next lint
cd frontend && pnpm build  # type-check (tsc via Next.js build)
```

## Pre-commit hooks

Ruff (Python) and Prettier (TypeScript) hooks are already configured. Install them once:

```bash
cd backend && uv run pre-commit install
```

After that, every `git commit` runs the formatters automatically.

## PR conventions

Branch off `main`, keep commits atomic and scoped, and ensure CI is green before requesting a review.

## Code style

- **Python** — ruff defaults: 88-character lines, rule sets `E`, `F`, `I`, `UP`.
- **TypeScript** — Prettier defaults (single quotes, no semicolons where optional, 2-space indent).
