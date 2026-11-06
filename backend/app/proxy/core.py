from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Optional

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server.stdio import stdio_server
from mcp.shared.message import SessionMessage
from mcp.types import JSONRPCMessage

from .config import ServerConfig
from .frames import log_frame


class MCPProxy:
    def __init__(
        self,
        server_cfg: ServerConfig,
        run_id: str | None = None,
        on_frame: Optional[
            Callable[[str, str, JSONRPCMessage], Awaitable[None]]
        ] = None,
    ) -> None:
        self.server_cfg = server_cfg
        self.run_id = run_id or str(uuid.uuid4())
        self._on_frame = on_frame

    async def run_stdio(self) -> None:
        """Connect to upstream via stdio_client, bridge inbound stdio ↔ upstream."""
        params = StdioServerParameters(
            command=self.server_cfg.command,
            args=self.server_cfg.args,
            env=self.server_cfg.env or None,
        )
        async with stdio_client(params) as (upstream_read, upstream_write):
            async with stdio_server() as (inbound_read, inbound_write):
                await self.run_streams(
                    inbound_rx=inbound_read,
                    inbound_tx=inbound_write,
                    upstream_rx=upstream_read,
                    upstream_tx=upstream_write,
                )

    async def run_streams(
        self,
        inbound_rx: MemoryObjectReceiveStream[SessionMessage | Exception],
        inbound_tx: MemoryObjectSendStream[SessionMessage],
        upstream_rx: MemoryObjectReceiveStream[SessionMessage | Exception],
        upstream_tx: MemoryObjectSendStream[SessionMessage],
    ) -> None:
        """Bridge: forward inbound→upstream and upstream→inbound concurrently."""
        async with anyio.create_task_group() as tg:
            tg.start_soon(
                self._forward_session,
                inbound_rx,
                upstream_tx,
                "client→upstream",
                tg.cancel_scope,
            )
            tg.start_soon(
                self._forward_session,
                upstream_rx,
                inbound_tx,
                "upstream→client",
                tg.cancel_scope,
            )

    async def _forward_session(
        self,
        src: MemoryObjectReceiveStream[SessionMessage | Exception],
        dst: MemoryObjectSendStream[SessionMessage],
        direction: str,
        cancel_scope: anyio.CancelScope,
    ) -> None:
        """Read SessionMessage frames from src, log each, write to dst."""
        try:
            async with src, dst:
                async for item in src:
                    if isinstance(item, Exception):
                        # Parse error — skip frame, do not crash
                        continue
                    log_frame(self.run_id, direction, item.message)
                    if self._on_frame:
                        await self._on_frame(self.run_id, direction, item.message)
                    try:
                        await dst.send(item)
                    except (anyio.ClosedResourceError, anyio.BrokenResourceError):
                        break
        except (anyio.ClosedResourceError, anyio.EndOfStream):
            pass
        finally:
            cancel_scope.cancel()
