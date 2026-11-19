"""Filesystem research agent — demo agent for MCP Trace Studio.

Spawns the MCP proxy (which records every tool call to SQLite) and runs a
fixed sequence of tool calls against the ``filesystem`` server:

1. list_directory(path)        — enumerate top-level entries
2. read_file(path)             — README.md + up to 4 .py files
3. Scan content for TODO/FIXME
4. Print a plain-text summary

No LLM API key required; the "agent" is a hardcoded tool-call sequence.
The trace is the product — open the dashboard to explore it.

Must be run from ``backend/`` so that ``uv run python -m app.proxy filesystem``
can find both the project (pyproject.toml) and servers.yaml:

    cd backend && uv run python ../examples/filesystem_agent.py ..
"""
from __future__ import annotations

import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

import anyio
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_entries(listing_text: str) -> tuple[list[str], list[str]]:
    """Parse ``[DIR] name`` / ``[FILE] name`` lines into two lists."""
    dirs: list[str] = []
    files: list[str] = []
    for line in listing_text.splitlines():
        line = line.strip()
        if line.startswith("[DIR]"):
            dirs.append(line[len("[DIR]"):].strip())
        elif line.startswith("[FILE]"):
            files.append(line[len("[FILE]"):].strip())
    return dirs, files


def _join_path(base: str, name: str) -> str:
    """Join base + name robustly for whatever the server uses as a separator."""
    # If name is already an absolute path (the server sometimes returns full
    # paths), use it as-is.
    if name.startswith("/") or (len(name) > 1 and name[1] == ":"):
        return name
    return str(Path(base) / name)


def _scan_todos(text: str, path: str) -> list[str]:
    """Return lines from *text* that contain TODO or FIXME."""
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if "TODO" in line or "FIXME" in line:
            hits.append(f"  {path}:{i}: {line.strip()}")
    return hits


# ---------------------------------------------------------------------------
# Core agent logic
# ---------------------------------------------------------------------------

async def research_repo(target_path: str = ".") -> None:
    """Walk *target_path* via the filesystem MCP server and find TODOs."""
    params = StdioServerParameters(
        command="uv",
        args=["run", "python", "-m", "app.proxy", "filesystem"],
    )

    print(f"[filesystem-agent] researching: {target_path}")
    print("[filesystem-agent] spawning proxy → filesystem server …")

    async with stdio_client(params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            # ----------------------------------------------------------------
            # 1. list_directory
            # ----------------------------------------------------------------
            print(f"[filesystem-agent] → list_directory({target_path!r})")
            dir_result = await session.call_tool(
                "list_directory", {"path": target_path}
            )
            listing_text = (
                dir_result.content[0].text if dir_result.content else ""
            )
            _, files = _extract_entries(listing_text)

            # ----------------------------------------------------------------
            # 2. Decide which files to read
            # ----------------------------------------------------------------
            candidates: list[str] = []
            # README first (highest value)
            for f in files:
                name = Path(f).name
                if name.lower() == "readme.md":
                    candidates.append(_join_path(target_path, f))
                    break

            # Up to 4 .py files
            py_files = [f for f in files if f.endswith(".py")][:4]
            candidates.extend(_join_path(target_path, f) for f in py_files)

            # If nothing found, read a sample of whatever files are there
            if not candidates and files:
                candidates = [_join_path(target_path, f) for f in files[:4]]

            # ----------------------------------------------------------------
            # 3. read_file for each candidate
            # ----------------------------------------------------------------
            all_todos: list[str] = []
            read_count = 0
            for file_path in candidates:
                print(f"[filesystem-agent] → read_file({file_path!r})")
                try:
                    file_result = await session.call_tool(
                        "read_file", {"path": file_path}
                    )
                    if file_result.is_error:
                        print(
                            f"[filesystem-agent]   ⚠ read error: "
                            f"{file_result.content[0].text if file_result.content else 'unknown'}"
                        )
                        continue
                    body = (
                        file_result.content[0].text
                        if file_result.content
                        else ""
                    )
                    read_count += 1
                    all_todos.extend(_scan_todos(body, file_path))
                except Exception as exc:  # noqa: BLE001
                    print(f"[filesystem-agent]   ⚠ exception: {exc}")

            # ----------------------------------------------------------------
            # 4. Summary
            # ----------------------------------------------------------------
            print()
            print("=" * 60)
            print("FILESYSTEM RESEARCH SUMMARY")
            print("=" * 60)
            print(f"Target path : {target_path}")
            print(f"Files listed: {len(files)}")
            print(f"Files read  : {read_count}")
            print(f"TODOs/FIXMEs: {len(all_todos)}")
            if all_todos:
                print()
                print("Findings:")
                for hit in all_todos:
                    print(hit)
            else:
                print("No TODO or FIXME markers found in the files read.")
            print("=" * 60)
            print()
            print("[filesystem-agent] trace written to backend/traces.db")
            print("[filesystem-agent] open http://localhost:3000 to explore")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    await research_repo(target)


if __name__ == "__main__":
    anyio.run(main)
