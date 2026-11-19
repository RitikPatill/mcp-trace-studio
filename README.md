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

## What works now (M7)

Two self-contained example agents in `examples/` populate the dashboard with realistic demo traces. Run `just demo` to execute both agents and then open the dashboard to explore the recorded tool calls.

| Component | State |
|-----------|-------|
| `backend/` — FastAPI app, `/health` endpoint, pydantic-settings | running |
| `backend/tests/` — API tests (health, proxy, store, API, replay, diff, example agents) | passing |
| `frontend/` — Next.js 15, TypeScript, Tailwind v4, shadcn/ui (badge, button, card, separator, skeleton, dialog) | dev server starts |
| `justfile` — `backend`, `frontend`, `dev`, `test`, `lint`, `demo` recipes | working |
| Pre-commit hooks — ruff (Python) + Prettier (TS/frontend) | configured |
| MIT LICENSE, `.gitignore` | present |
| **`backend/app/proxy/`** — transparent MCP stdio proxy (`MCPProxy`) | **done** |
| **`backend/servers.yaml`** — upstream server registry (`filesystem`, `fake`, `search`) | **done** |
| **`backend/app/models.py`** — SQLModel tables: `Run` (with `parent_run_id`), `Span`, `ToolCall` | **done** |
| **`backend/app/database.py`** — SQLite engine (WAL mode), `init_db`, `get_session` | **done** |
| **`backend/app/store.py`** — store helpers + `FrameRecorder` + `get_tool_calls_for_run` | **done** |
| **`backend/app/api/runs.py`** — `GET /runs`, `GET /runs/{id}`, `GET /runs/{id}/spans`, `POST /runs/{id}/replay`, `GET /runs/{a}/diff/{b}`, `WS /ws/runs/{id}` | **done** |
| **`backend/app/api/replay.py`** — `execute_replay` background task (MCP stdio client, records spans + tool calls) | **done** |
| **`frontend/src/app/runs/page.tsx`** — runs list with status badge, duration, tool count, server chip | **done** |
| **`frontend/src/app/runs/[id]/page.tsx`** — run detail page: header with Replay/Diff buttons, waterfall, side panel | **done** |
| **`frontend/src/app/runs/[id]/diff/[compareId]/page.tsx`** — diff page: two RunCards + DiffTable | **done** |
| **`frontend/src/hooks/useRunWebSocket.ts`** — WebSocket hook; streams new spans live | **done** |
| **`frontend/src/components/timeline/WaterfallTimeline.tsx`** — zoomable waterfall | **done** |
| **`frontend/src/components/timeline/SpanDetailPanel.tsx`** — span metadata, JSON trees | **done** |
| **`frontend/src/components/timeline/LatencySparkline.tsx`** — SVG bar sparkline | **done** |
| **`frontend/src/components/timeline/JsonDisplay.tsx`** — syntax-highlighted collapsible JSON | **done** |
| **`frontend/src/components/replay/ReplayDialog.tsx`** — modal to pick server + model, fires replay | **done** |
| **`frontend/src/components/replay/DiffRunPickerDialog.tsx`** — modal run list picker for diff | **done** |
| **`frontend/src/components/diff/DiffTable.tsx`** — aligned tool call table with expand-to-diff | **done** |
| **`frontend/src/components/diff/JsonLineDiff.tsx`** — line-by-line JSON diff (green/red) using `diff` package | **done** |
| **`frontend/src/lib/utils.ts`** — `djb2`, `serverColor`, `serverBarColor` helpers | **done** |
| **`frontend/src/lib/api.ts`** — typed fetch client (`replayRun`, `getDiff`, etc.) | **done** |
| **`examples/filesystem_agent.py`** — filesystem research agent (list_directory → read_file → TODO scan) | **done** |
| **`examples/search_server.py`** — toy local MCP search server (in-memory knowledge base, 3 tools) | **done** |
| **`examples/search_agent.py`** — web-search demo agent (get_topics → search → fetch_page) | **done** |

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
| `POST /runs/{id}/replay` | Re-execute captured tool calls; returns new run (202) |
| `GET /runs/{a}/diff/{b}` | Align tool calls across two runs, return diff entries |
| `WS /ws/runs/{id}` | Live stream of new spans (polls every 500 ms) |

```bash
curl http://localhost:8000/runs
curl http://localhost:8000/runs/<run-id>/spans
curl -X POST http://localhost:8000/runs/<run-id>/replay \
     -H 'Content-Type: application/json' \
     -d '{"server_name": "filesystem"}'
curl http://localhost:8000/runs/<run-a>/diff/<run-b>
```

> **SQLite migration note:** `parent_run_id` is a new nullable column on `Run`. If you have an existing `traces.db` from M5 or earlier, run:
> ```bash
> sqlite3 backend/traces.db "ALTER TABLE run ADD COLUMN parent_run_id TEXT;"
> ```
> Or delete `traces.db` for a clean start. Tests use in-memory DBs and are unaffected.

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

### Quick demo

Populate the dashboard with realistic traces in one command (no backend needed first — agents write directly to SQLite):

```bash
just demo
```

Then start the backend and frontend:

```bash
just backend   # Terminal 1
just frontend  # Terminal 2
```

Open <http://localhost:3000> and explore the two recorded runs:
- **filesystem** — `list_directory` → `read_file` × N → TODO scan summary
- **search** — `get_topics` → `search` → `fetch_page` × N → research brief

### Full demo flow

1. `just backend` + `just frontend` in two terminals.
2. Confirm the backend is healthy: <http://localhost:8000/health>.
3. Open <http://localhost:3000> — you are redirected to the **Runs** page.
4. Run the proxy against an MCP server; runs appear live (5-second poll).
5. Click a run row to open the waterfall timeline; click any span bar to inspect args/result JSON.
6. On the run detail page, click **Replay** to pick a server and model, then watch the new run fill in live via WebSocket.
7. Click **Diff** on either run, pick a second run to compare, and view the aligned tool-call table with JSON line diffs and latency-delta badges.
8. Toggle dark/light theme with the button at the bottom of the sidebar.

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
| M4 — Dashboard UI | done |
| M5 — trace timeline UI | done |
| M6 — Replay + Diff | done |
| M7 — example agents (`just demo`) | done |

---

## License

MIT © 2026 Ritik
