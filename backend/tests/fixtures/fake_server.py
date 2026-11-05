"""Minimal MCP server for tests.

Implements one tool: echo(text: str) -> text.

Can be run as a subprocess (for integration testing against the CLI) or
imported directly in in-process tests.  All anyio / server startup is inside
``if __name__ == "__main__"`` so importing this module has no side effects.
"""
from __future__ import annotations

import anyio
from mcp.server import MCPServer

# ---------------------------------------------------------------------------
# Server definition (importable, side-effect-free)
# ---------------------------------------------------------------------------

server = MCPServer(name="fake", version="0.1.0")


@server.tool()
def echo(text: str) -> str:
    """Return the input text unchanged."""
    return text


# ---------------------------------------------------------------------------
# Subprocess entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    anyio.run(server.run_stdio_async)
