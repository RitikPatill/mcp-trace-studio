# Roadmap

Possible future directions for MCP Trace Studio. These are not committed deliverables — just the most requested or interesting ideas.

---

## OpenTelemetry export

Export spans to any OTel-compatible backend (Jaeger, Tempo, Honeycomb, Grafana Cloud).

Map `Run → Trace`, `Span → OTel Span`, `ToolCall → child span` with attributes. Emit via OTLP HTTP exporter; keep SQLite as the primary local store so the offline story is unchanged.

---

## Langfuse bridge

Post completed runs to Langfuse as observations using their REST API. Useful for teams already using Langfuse for LLM cost tracking who want MCP tool-call traces in the same dashboard.

---

## Non-MCP adapters

An OpenAI function-calling adapter that maps `tool_calls` in chat completions responses to the same `Run / Span / ToolCall` schema, enabling side-by-side comparison of MCP and direct function-calling agent runs in the diff view.

---

## Multi-user / hosted mode

JWT auth layer on the FastAPI backend, per-user run isolation, and a PostgreSQL option in place of SQLite for concurrent writes. This would enable a small team to share a single trace server without traces leaking between users.
