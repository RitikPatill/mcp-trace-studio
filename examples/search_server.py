"""Toy local search MCP server — demo server for MCP Trace Studio.

Exposes three tools backed by an in-memory KNOWLEDGE_BASE about MCP,
tracing, and LLM agents.  No network calls, no external dependencies.

Run as a standalone MCP server (stdio):

    python examples/search_server.py
"""
from __future__ import annotations

import anyio
from mcp.server import MCPServer

# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------

KNOWLEDGE_BASE: list[dict] = [
    {
        "url": "https://example.com/mcp-intro",
        "title": "Introduction to the Model Context Protocol",
        "body": (
            "The Model Context Protocol (MCP) is an open standard that lets AI "
            "agents invoke tools and read resources hosted on MCP servers.  "
            "Clients communicate with servers over stdio or HTTP+SSE using "
            "JSON-RPC 2.0 frames.  Each tool call carries a method name, typed "
            "arguments, and returns a structured result."
        ),
        "tags": ["mcp", "protocol", "json-rpc"],
    },
    {
        "url": "https://example.com/observability",
        "title": "Observability for LLM Agents",
        "body": (
            "Observability means capturing structured traces of every step an "
            "agent takes — tool calls, LLM prompts, intermediate results — so "
            "you can debug failures, compare runs, and spot regressions.  "
            "Key concepts: spans (a single timed unit of work), traces (a "
            "tree of spans for one agent run), and waterfall timelines."
        ),
        "tags": ["observability", "tracing", "spans", "agents"],
    },
    {
        "url": "https://example.com/mcp-proxy",
        "title": "Transparent MCP Proxy Pattern",
        "body": (
            "A transparent proxy sits between the agent client and the real MCP "
            "server, forwarding every JSON-RPC frame and recording it as a span. "
            "Because it speaks the same MCP wire protocol on both sides, no "
            "changes to the agent or the server are needed.  The proxy only adds "
            "latency for the SQLite write, typically under 1 ms."
        ),
        "tags": ["mcp", "proxy", "tracing", "stdio"],
    },
    {
        "url": "https://example.com/sqlite-traces",
        "title": "Storing Agent Traces in SQLite",
        "body": (
            "SQLite in WAL mode is an excellent fit for local trace storage.  "
            "WAL (Write-Ahead Logging) lets a reader and a writer operate "
            "concurrently without blocking.  Runs, spans, and tool calls are "
            "stored in three tables joined by run_id.  Indices on run_id and "
            "started_at keep timeline queries fast even with millions of spans."
        ),
        "tags": ["sqlite", "storage", "tracing", "wal"],
    },
    {
        "url": "https://example.com/replay-diff",
        "title": "Replay and Diff for Agent Debugging",
        "body": (
            "Replay re-executes the tool calls from a captured trace against a "
            "different server or model configuration, producing a new run you "
            "can compare with the original.  Diff aligns two runs by tool-call "
            "sequence and shows argument changes, output differences, and "
            "latency deltas — the git-diff for agent behaviour."
        ),
        "tags": ["replay", "diff", "debugging", "agents"],
    },
    {
        "url": "https://example.com/fastapi-websocket",
        "title": "Live Trace Streaming with FastAPI WebSockets",
        "body": (
            "FastAPI's WebSocket support makes it straightforward to push new "
            "spans to the dashboard as they are written.  A background task "
            "polls the SQLite DB every 500 ms, diffs against the last-sent "
            "snapshot, and broadcasts new rows as JSON.  The Next.js frontend "
            "appends them to the waterfall without a full page reload."
        ),
        "tags": ["fastapi", "websocket", "streaming", "dashboard"],
    },
]

# ---------------------------------------------------------------------------
# Pure business logic (importable, side-effect-free, testable)
# ---------------------------------------------------------------------------


def _search(query: str) -> list[dict]:
    """Return up to 3 KNOWLEDGE_BASE items matching any word in *query*."""
    words = query.lower().split()
    results = []
    for item in KNOWLEDGE_BASE:
        searchable = (
            item["title"] + " " + item["body"] + " " + " ".join(item["tags"])
        ).lower()
        if any(w in searchable for w in words):
            results.append(item)
        if len(results) == 3:
            break
    return results


def _fetch_page(url: str) -> str:
    """Return the body for *url* or an error string if not found."""
    for item in KNOWLEDGE_BASE:
        if item["url"] == url:
            return item["body"]
    return f"error: URL not found in knowledge base: {url}"


def _get_topics() -> list[str]:
    """Return a sorted list of unique tags across all knowledge-base items."""
    tags: set[str] = set()
    for item in KNOWLEDGE_BASE:
        tags.update(item["tags"])
    return sorted(tags)


# ---------------------------------------------------------------------------
# MCP server definition
# ---------------------------------------------------------------------------

server = MCPServer(name="search", version="0.1.0")


@server.tool()
def search(query: str) -> list[dict]:
    """Return up to 3 results whose title/body/tags contain any query word."""
    return _search(query)


@server.tool()
def fetch_page(url: str) -> str:
    """Return the body text of the page at url (from KNOWLEDGE_BASE)."""
    return _fetch_page(url)


@server.tool()
def get_topics() -> list[str]:
    """List all unique tags in the knowledge base."""
    return _get_topics()


# ---------------------------------------------------------------------------
# Subprocess entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    anyio.run(server.run_stdio_async)
