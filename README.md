# MCP Trace Studio

> Local-first observability dashboard that proxies MCP traffic, captures agent tool calls as traces, and lets you replay and diff runs — Chrome DevTools for AI agents.

![demo](docs/demo.gif)

## What it is

Debugging MCP agents today means reading raw stdout and sprinkling `print()` statements. MCP Trace Studio fixes that: a transparent Python proxy sits between your agent and your MCP servers, records every JSON-RPC frame as a structured span, and renders the results the way Chrome DevTools renders a network waterfall — live, zoomable, clickable. The entire stack runs offline against SQLite; no data leaves your machine, no cloud account required.

The proxy speaks both stdio and SSE/HTTP transports and requires zero changes to your agent. A FastAPI backend stores runs as `run → span → tool_call` with timing, arguments, results, and errors. The Next.js dashboard adds a **Replay** view — rerun a captured trace against a different model or server — and a **Diff** view that aligns two runs side-by-side and highlights argument changes, output changes, and latency deltas.

## Quickstart

**Prerequisites:** [uv](https://docs.astral.sh/uv/) ≥ 0.5, [pnpm](https://pnpm.io/) ≥ 9, [just](https://just.systems/) ≥ 1.36, Python ≥ 3.11, Node.js ≥ 20.

```bash
git clone https://github.com/RitikPatill/mcp-trace-studio.git
cd mcp-trace-studio
cd backend && uv sync && cd ..
cd frontend && pnpm install && cd ..
just demo                # populate SQLite with two example agent runs
```

Then open two terminals:

```bash
# Terminal 1
just backend             # FastAPI on http://localhost:8000

# Terminal 2
just frontend            # Next.js on http://localhost:3000
```

Open <http://localhost:3000> and you will land on the Runs list with the demo traces already loaded.

## Usage

After `just demo`, the dashboard shows two runs: a filesystem research agent and a web-search agent. Click any run row to open the waterfall timeline. Click a span bar to inspect the raw JSON args and return value. Use the **Replay** button to rerun the trace against a different server config and watch new spans stream in live. Use the **Diff** button to compare any two runs and see which tool arguments changed, which outputs changed, and by how much latency shifted.

To trace your own agent, point it at the proxy instead of your real MCP server:

```bash
cd backend && uv run python -m app.proxy filesystem
```

Add server definitions to `backend/servers.yaml`. The proxy forwards faithfully and writes every frame to SQLite as a structured span.

```bash
# one API call example
curl http://localhost:8000/runs
curl -X POST http://localhost:8000/runs/<run-id>/replay \
     -H 'Content-Type: application/json' \
     -d '{"server_name": "filesystem"}'
```

## Architecture

```
Agent (Claude Desktop / CLI)
        │  MCP stdio / SSE
        ▼
   MCP Proxy ──writes spans──▶  FastAPI + SQLite
  (Python · mcp-sdk)               (SQLModel)
        │                               │
        │  forwards                     │  REST / WebSocket
        ▼                               ▼
 Real MCP Servers               Next.js Dashboard
 (filesystem, search…)         (Timeline · Diff · Replay)
```

## Project structure

```
mcp-trace-studio/
├── backend/          Python package — FastAPI app, proxy, SQLModel store
│   ├── app/          Application modules: api, proxy, models, store, settings
│   ├── tests/        pytest suite covering proxy, API, diff, replay, agents
│   └── servers.yaml  MCP server definitions consumed by proxy and replay
├── frontend/         Next.js 15 dashboard (TypeScript, Tailwind, shadcn/ui)
│   └── src/          Pages, components, hooks, API client
├── examples/         Two runnable demo agents (filesystem + web-search)
├── docs/             Screenshot and demo GIF
├── scripts/          Screenshot capture and demo recording helpers
└── justfile          Task runner: backend / frontend / test / lint / demo
```

## Roadmap

- [ ] OpenTelemetry export — emit spans via OTLP HTTP to Jaeger, Tempo, or Grafana Cloud while keeping SQLite as the local store.
- [ ] Langfuse bridge — post completed runs to Langfuse as observations for teams already using it for LLM cost tracking.
- [ ] OpenAI function-calling adapter — map `tool_calls` in chat completion responses to the same schema so non-MCP agents appear in the diff view.
- [ ] Multi-user mode — JWT auth, per-user run isolation, and a PostgreSQL backend option for shared team deployments.

## License

MIT — see LICENSE.

---

Built autonomously by [autodev](https://github.com/RitikPatill/autodev),
a multi-agent orchestrator I designed. Each commit in this repo was
authored by me; the implementation work was performed by Sonnet under
the orchestrator's control. Read the orchestrator's README to see how.
