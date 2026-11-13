"""CLI entry point: python -m app.proxy <server-name> [--config servers.yaml]"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

import anyio

from ..database import get_engine, init_db
from ..models import Run  # noqa: F401 — registers table metadata
from ..store import FrameRecorder, close_run, create_run
from .config import load_servers
from .core import MCPProxy
from sqlmodel import Session


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MCP transparent proxy — forwards stdio MCP traffic and logs every frame."
    )
    parser.add_argument("server", help="Server name from servers.yaml")
    parser.add_argument(
        "--config",
        default="servers.yaml",
        help="Path to servers.yaml (default: ./servers.yaml)",
    )
    args = parser.parse_args()

    try:
        servers = load_servers(args.config)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.server not in servers:
        available = ", ".join(servers.keys())
        print(
            f"error: unknown server '{args.server}'. Available: {available}",
            file=sys.stderr,
        )
        sys.exit(1)

    server_cfg = servers[args.server]

    # Ensure tables exist
    init_db()

    engine = get_engine()

    # Create a run row
    with Session(engine) as session:
        run = create_run(session, server_name=args.server)
        run_id = run.id

    recorder = FrameRecorder(run_id=run_id, engine=engine)

    async def _run() -> None:
        proxy = MCPProxy(
            server_cfg=server_cfg,
            run_id=run_id,
            on_frame=recorder.on_frame,
        )
        try:
            await proxy.run_stdio()
        finally:
            ended_at = datetime.now(timezone.utc)
            with Session(engine) as session:
                close_run(session, run_id, ended_at)

    anyio.run(_run)


if __name__ == "__main__":
    main()
