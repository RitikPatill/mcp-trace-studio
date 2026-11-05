"""Tests for the MCP proxy (M2).

Unit tests for config loading and frame logging, plus two async integration
tests that drive list_tools and call_tool round-trips through the proxy using
in-process anyio memory streams (no subprocess, no network).
"""
from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage
from mcp.types import JSONRPCRequest

from app.proxy.config import ServerConfig, load_servers
from app.proxy.core import MCPProxy
from app.proxy.frames import log_frame

SERVERS_YAML = Path(__file__).parent.parent / "servers.yaml"


# ---------------------------------------------------------------------------
# Unit: config loading
# ---------------------------------------------------------------------------


def test_load_servers_valid_yaml():
    servers = load_servers(SERVERS_YAML)
    assert "filesystem" in servers
    assert "fake" in servers
    fs = servers["filesystem"]
    assert isinstance(fs, ServerConfig)
    assert fs.command == "uvx"
    assert "mcp-server-filesystem" in fs.args


def test_load_servers_missing_file():
    with pytest.raises(FileNotFoundError):
        load_servers("/nonexistent/path/servers.yaml")


# ---------------------------------------------------------------------------
# Unit: frame logging
# ---------------------------------------------------------------------------


def test_log_frame_emits_json(capsys):
    req = JSONRPCRequest(id=42, method="tools/list", jsonrpc="2.0")
    msg = SessionMessage(message=req)
    log_frame("run-abc", "client→upstream", msg.message)

    captured = capsys.readouterr()
    line = captured.err.strip().splitlines()[-1]
    record = json.loads(line)

    assert record["run_id"] == "run-abc"
    assert record["direction"] == "client→upstream"
    assert record["method"] == "tools/list"
    assert record["msg_id"] == 42
    assert "ts" in record


# ---------------------------------------------------------------------------
# Async integration helpers
# ---------------------------------------------------------------------------


def _make_streams():
    """Return four (tx, rx) pairs for the in-process proxy bridge."""
    c2p = anyio.create_memory_object_stream(16)   # client → proxy inbound
    p2c = anyio.create_memory_object_stream(16)   # proxy inbound → client
    p2s = anyio.create_memory_object_stream(16)   # proxy upstream → server
    s2p = anyio.create_memory_object_stream(16)   # server → proxy upstream
    return c2p, p2c, p2s, s2p


async def _run_server_in_background(tg: anyio.abc.TaskGroup, p2s_rx, s2p_tx):
    """Start the fake MCPServer low-level run in the task group."""
    # Import here so the module-level import doesn't launch anyio.
    from tests.fixtures.fake_server import server as fake_srv

    srv = fake_srv._lowlevel_server
    tg.start_soon(
        srv.run,
        p2s_rx,
        s2p_tx,
        srv.create_initialization_options(),
    )


# ---------------------------------------------------------------------------
# Async integration: list_tools round-trip
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_list_tools_roundtrip():
    (c2p_tx, c2p_rx), (p2c_tx, p2c_rx), (p2s_tx, p2s_rx), (s2p_tx, s2p_rx) = (
        _make_streams()
    )
    proxy = MCPProxy(server_cfg=ServerConfig(command="fake", args=[]))
    result_holder: list = []

    async def client_task():
        async with ClientSession(read_stream=p2c_rx, write_stream=c2p_tx) as client:
            await client.initialize()
            result = await client.list_tools()
            result_holder.append(result)
        # Signal EOF to proxy so it cleans up and cancels the task group.
        await c2p_tx.aclose()

    async with anyio.create_task_group() as tg:
        # Proxy bridges inbound (client) ↔ upstream (server)
        tg.start_soon(
            proxy.run_streams,
            c2p_rx,   # inbound_rx
            p2c_tx,   # inbound_tx
            s2p_rx,   # upstream_rx
            p2s_tx,   # upstream_tx
        )
        await _run_server_in_background(tg, p2s_rx, s2p_tx)
        tg.start_soon(client_task)

    assert len(result_holder) == 1, "client_task did not complete"
    tools = result_holder[0].tools
    assert any(t.name == "echo" for t in tools), f"echo tool missing: {tools}"


# ---------------------------------------------------------------------------
# Async integration: call_tool round-trip
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_call_tool_roundtrip():
    (c2p_tx, c2p_rx), (p2c_tx, p2c_rx), (p2s_tx, p2s_rx), (s2p_tx, s2p_rx) = (
        _make_streams()
    )
    proxy = MCPProxy(server_cfg=ServerConfig(command="fake", args=[]))
    result_holder: list = []

    async def client_task():
        async with ClientSession(read_stream=p2c_rx, write_stream=c2p_tx) as client:
            await client.initialize()
            result = await client.call_tool("echo", {"text": "hello proxy"})
            result_holder.append(result)
        await c2p_tx.aclose()

    async with anyio.create_task_group() as tg:
        tg.start_soon(
            proxy.run_streams,
            c2p_rx,
            p2c_tx,
            s2p_rx,
            p2s_tx,
        )
        await _run_server_in_background(tg, p2s_rx, s2p_tx)
        tg.start_soon(client_task)

    assert len(result_holder) == 1, "client_task did not complete"
    call_result = result_holder[0]
    assert not call_result.is_error
    # The echo tool returns a TextContent with text="hello proxy"
    assert len(call_result.content) == 1
    assert call_result.content[0].text == "hello proxy"
