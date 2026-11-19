"""Web-search demo agent — demo agent for MCP Trace Studio.

Spawns the MCP proxy (which records every tool call to SQLite) pointing at
the toy ``search`` server and runs a fixed research sequence:

1. get_topics()                — log available topics
2. search(query)               → up to 3 results
3. fetch_page(url)             — for each result
4. Print a formatted research brief to stdout

No LLM API key required; the "agent" is a hardcoded tool-call sequence.
The trace is the product — open the dashboard to explore it.

Must be run from ``backend/`` so that ``uv run python -m app.proxy search``
can find both the project (pyproject.toml) and servers.yaml:

    cd backend && uv run python ../examples/search_agent.py "MCP observability"
"""
from __future__ import annotations

import sys

import anyio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


# ---------------------------------------------------------------------------
# Core agent logic
# ---------------------------------------------------------------------------

async def research_topic(query: str = "MCP observability") -> None:
    """Research *query* via the toy search MCP server."""
    params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "app.proxy", "search"],
    )

    print(f"[search-agent] query: {query!r}")
    print("[search-agent] spawning proxy → search server …")

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # ----------------------------------------------------------------
            # 1. get_topics — discover what the server knows about
            # ----------------------------------------------------------------
            print("[search-agent] → get_topics()")
            topics_result = await session.call_tool("get_topics", {})
            topics_text = (
                topics_result.content[0].text if topics_result.content else "[]"
            )
            # The MCP server serialises the list as a JSON string in TextContent
            import json as _json
            try:
                topics: list[str] = _json.loads(topics_text)
            except ValueError:
                topics = [t.strip() for t in topics_text.split(",") if t.strip()]
            print(f"[search-agent]   topics: {', '.join(topics)}")

            # ----------------------------------------------------------------
            # 2. search
            # ----------------------------------------------------------------
            print(f"[search-agent] → search({query!r})")
            search_result = await session.call_tool("search", {"query": query})
            search_text = (
                search_result.content[0].text if search_result.content else "[]"
            )
            try:
                results: list[dict] = _json.loads(search_text)
            except ValueError:
                results = []
            print(f"[search-agent]   {len(results)} result(s)")

            # ----------------------------------------------------------------
            # 3. fetch_page for each result
            # ----------------------------------------------------------------
            pages: list[tuple[str, str]] = []
            for item in results:
                url = item.get("url", "")
                title = item.get("title", url)
                print(f"[search-agent] → fetch_page({url!r})")
                page_result = await session.call_tool(
                    "fetch_page", {"url": url}
                )
                body = (
                    page_result.content[0].text if page_result.content else ""
                )
                pages.append((title, body))

            # ----------------------------------------------------------------
            # 4. Research brief
            # ----------------------------------------------------------------
            print()
            print("=" * 60)
            print(f"RESEARCH BRIEF: {query}")
            print("=" * 60)
            print(f"Available topics : {', '.join(topics)}")
            print(f"Results found    : {len(results)}")
            print()
            for i, (title, body) in enumerate(pages, 1):
                print(f"[{i}] {title}")
                # Print the first two sentences of the body as a snippet
                sentences = [s.strip() for s in body.replace("  ", " ").split(".") if s.strip()]
                snippet = ".  ".join(sentences[:2]) + "." if sentences else body
                print(f"    {snippet}")
                print()
            print("=" * 60)
            print()
            print("[search-agent] trace written to backend/traces.db")
            print("[search-agent] open http://localhost:3000 to explore")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "MCP observability"
    await research_topic(query)


if __name__ == "__main__":
    anyio.run(main)
