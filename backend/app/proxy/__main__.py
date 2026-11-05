"""CLI entry point: python -m app.proxy <server-name> [--config servers.yaml]"""
from __future__ import annotations

import argparse
import sys

import anyio

from .config import load_servers
from .core import MCPProxy


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

    proxy = MCPProxy(server_cfg=servers[args.server])
    anyio.run(proxy.run_stdio)


if __name__ == "__main__":
    main()
