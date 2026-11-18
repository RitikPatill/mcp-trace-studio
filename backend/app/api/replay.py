from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from sqlalchemy import Engine
from sqlmodel import Session

from ..models import Span, ToolCall
from ..proxy.config import ServerConfig
from ..store import close_run, get_tool_calls_for_run


async def execute_replay(
    original_run_id: str,
    new_run_id: str,
    server_cfg: ServerConfig,
    engine: Engine,
) -> None:
    """Re-execute all tool calls from original_run_id against server_cfg,
    writing results into new_run_id.  Called as a FastAPI BackgroundTask."""

    with Session(engine) as session:
        tool_calls = get_tool_calls_for_run(session, original_run_id)

    params = StdioServerParameters(
        command=server_cfg.command,
        args=server_cfg.args,
        env=server_cfg.env or None,
    )

    try:
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as mcp_session:
                await mcp_session.initialize()

                for tc in tool_calls:
                    started_at = datetime.now(timezone.utc)
                    result_json: str | None = None
                    error: str | None = None

                    try:
                        args = json.loads(tc.args_json)
                        result = await mcp_session.call_tool(tc.tool_name, args)
                        ended_at = datetime.now(timezone.utc)
                        result_json = json.dumps(result.model_dump())
                    except Exception as exc:
                        ended_at = datetime.now(timezone.utc)
                        error = str(exc)

                    duration_ms = (ended_at - started_at).total_seconds() * 1000
                    span_id = str(uuid.uuid4())
                    tc_id = str(uuid.uuid4())

                    with Session(engine) as session:
                        span = Span(
                            id=span_id,
                            run_id=new_run_id,
                            direction="client\u2192upstream",
                            method="tools/call",
                            started_at=started_at,
                            ended_at=ended_at,
                            duration_ms=duration_ms,
                        )
                        new_tc = ToolCall(
                            id=tc_id,
                            span_id=span_id,
                            run_id=new_run_id,
                            tool_name=tc.tool_name,
                            args_json=tc.args_json,
                            result_json=result_json,
                            error=error,
                            started_at=started_at,
                            ended_at=ended_at,
                            duration_ms=duration_ms,
                        )
                        session.add(span)
                        session.add(new_tc)
                        session.commit()
    finally:
        with Session(engine) as session:
            close_run(session, new_run_id, datetime.now(timezone.utc))
