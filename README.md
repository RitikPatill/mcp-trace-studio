# MCP Trace Studio

> **Local-first observability for MCP agents** — capture, inspect, replay, and diff every tool call your agent makes.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

![Dashboard](docs/screenshot-placeholder.png)

---

## What it is

MCP Trace Studio is a transparent debugging stack for agents that talk to [Model Context Protocol](https://modelcontextprotocol.io/) servers. It sits between your agent client and your MCP servers, records every JSON-RPC frame as a structured span, and renders the resulting traces the way Chrome DevTools renders a page load.

**Target capabilities**

- **Transparent proxy** — stdio and SSE/HTTP transports, zero agent-side changes required.
- **Live waterfall timeline** — watch tool calls appear in real time as the agent runs.
- **Span detail view** — inspect raw args and return values in a collapsible JSON tree.
- **Replay** — rerun a captured trace against a different model or server config and compare latency.
- **Diff** — place two runs side-by-side to see which arguments, outputs, or latencies changed.
- **Fully offline** — SQLite backend, no cloud dependency, your traces never leave your machine.

---

## What works now (M1)

The monorepo scaffold is in place and both services start cleanly.

| Component | State |
|-----------|-------|
| `backend/` — FastAPI app, `/health` endpoint, pydantic-settings | running |
| `backend/tests/` — smoke test for health check (`pytest`) | passing |
| `frontend/` — Next.js 15, TypeScript, Tailwind v4, shadcn/ui initialized | dev server starts |
| `justfile` — `backend`, `frontend`, `dev`, `test`, `lint` recipes | working |
| Pre-commit hooks — ruff (Python) + Prettier (TS/frontend) | configured |
| MIT LICENSE, `.gitignore` | present |

The proxy, trace ingestion, REST/WebSocket API, and all UI features listed above are **not yet implemented** — see the roadmap below.

---

## Architecture

```
           ┌────────────────┐
           │  Agent client  │  (Claude Desktop / local CLI)
           └───────┬────────┘
                   │ MCP (stdio/SSE)
           ┌───────▼────────┐
           │   MCP Proxy    │  ◀── Python, mcp-sdk
           │  (interceptor) │
           └───┬─────────┬──┘
               │         │ forwards
   writes spans│         ▼
               │   ┌─────────────┐
               │   │ Real MCP    │  (filesystem, web, …)
               │   │  servers    │
               │   └─────────────┘
               ▼
       ┌───────────────┐       ┌──────────────────┐
       │  FastAPI +    │◀──────│  Next.js UI      │
       │   SQLite      │  REST │  Timeline/Diff   │
       │   (SQLModel)  │  WS   │  Replay console  │
       └───────────────┘       └──────────────────┘
```

---

## Quickstart

### Prerequisites

| Tool | Version |
|------|---------|
| [uv](https://docs.astral.sh/uv/) | ≥ 0.5 |
| [pnpm](https://pnpm.io/) | ≥ 9 |
| [just](https://just.systems/) | ≥ 1.36 |
| Python | ≥ 3.11 |
| Node.js | ≥ 20 |

### Run (two terminals)

**Terminal 1 — backend**

```bash
just backend
```

Starts FastAPI on <http://localhost:8000>. Health check: <http://localhost:8000/health>.

**Terminal 2 — frontend**

```bash
just frontend
```

Starts Next.js dev server on <http://localhost:3000>.

> **Note:** `just dev` prints this same instruction. Background-process parallelism on Windows requires two terminals for now.

### Demo flow

1. `just backend` + `just frontend` in two terminals.
2. Confirm the backend is healthy: <http://localhost:8000/health>.
3. Open <http://localhost:3000>.

<!-- TODO: update steps 2–4 once M2 ships the proxy (port 7878) and trace ingestion. -->

---

## Development

```bash
# Install backend deps
cd backend && uv sync

# Install frontend deps
cd frontend && pnpm install
```

The `justfile` wraps the common tasks:

```bash
just test   # uv run pytest -v
just lint   # ruff check + ruff format (backend)
```

Manual equivalents:

```bash
# Backend tests
cd backend && uv run pytest -v

# Lint / format
cd backend && uv run ruff check . --fix
cd backend && uv run ruff format .
cd frontend && pnpm prettier --write .
```

---

## Project status

| Milestone | Status |
|-----------|--------|
| M1 — scaffold + readme | done |
| M2 — MCP proxy + SQLite schema | next |
| M3 — REST + WebSocket API | |
| M4 — Dashboard UI | |
| M5 — Replay + Diff | |

---

## License

MIT © 2026 Ritik
