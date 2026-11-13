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

## What works now (M3)

Trace storage, ingestion, and REST/WebSocket API are live.

| Component | State |
|-----------|-------|
| `backend/` — FastAPI app, `/health` endpoint, pydantic-settings | running |
| `backend/tests/` — 16 tests (health, proxy, store, API) | passing |
| `frontend/` — Next.js 15, TypeScript, Tailwind v4, shadcn/ui initialized | dev server starts |
| `justfile` — `backend`, `frontend`, `dev`, `test`, `lint` recipes | working |
| Pre-commit hooks — ruff (Python) + Prettier (TS/frontend) | configured |
| MIT LICENSE, `.gitignore` | present |
| **`backend/app/proxy/`** — transparent MCP stdio proxy (`MCPProxy`) | **done** |
| **`backend/servers.yaml`** — upstream server registry | **done** |
| **`backend/app/models.py`** — SQLModel tables: `Run`, `Span`, `ToolCall` | **done** |
| **`backend/app/database.py`** — SQLite engine (WAL mode), `init_db`, `get_session` | **done** |
| **`backend/app/store.py`** — store helpers + `FrameRecorder` (request/response correlation) | **done** |
| **`backend/app/api/runs.py`** — `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/spans`, `WS /ws/runs/{id}` | **done** |

The dashboard UI, replay, and diff are **not yet implemented** — see the roadmap below.

### Using the proxy

Point your MCP client at the proxy instead of a real server:

```bash
# Forward all traffic to the 'filesystem' server defined in servers.yaml
cd backend
uv run python -m app.proxy filesystem
```

Every JSON-RPC frame is logged as a JSON-lines record to stderr **and written to SQLite** as a structured span. `tools/call` frames are correlated with their responses to produce timed `ToolCall` rows.

### REST API

| Endpoint | Description |
|----------|-------------|
| `GET /runs` | List all runs, most recent first |
| `GET /runs/{id}` | Get a single run (404 if not found) |
| `GET /runs/{id}/spans` | All spans for a run, with nested tool calls |
| `WS /ws/runs/{id}` | Live stream of new spans (polls every 500 ms) |

```bash
curl http://localhost:8000/runs
curl http://localhost:8000/runs/<run-id>/spans
```

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

<!-- TODO: extend demo flow once M4 ships the dashboard UI. -->

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
| M2 — MCP proxy core (stdio, frame logging, pytest suite) | done |
| M3 — trace storage + REST/WebSocket API | done |
| M4 — Dashboard UI | |
| M5 — Replay + Diff | |

---

## License

MIT © 2026 Ritik
