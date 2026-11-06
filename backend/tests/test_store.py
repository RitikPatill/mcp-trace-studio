"""Unit tests for store helpers and FrameRecorder."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import models  # noqa: F401 — registers table metadata
from app.store import (
    FrameRecorder,
    close_run,
    create_run,
    get_run,
    get_spans,
    list_runs,
)


@pytest.fixture()
def engine():
    """In-memory SQLite engine — fresh for each test."""
    eng = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    yield eng
    SQLModel.metadata.drop_all(eng)


@pytest.fixture()
def session(engine):
    with Session(engine) as sess:
        yield sess


# ---------------------------------------------------------------------------
# Basic CRUD helpers
# ---------------------------------------------------------------------------


def test_create_and_list_runs(session):
    r1 = create_run(session, server_name="fs")
    r2 = create_run(session, server_name="web")
    runs = list_runs(session)
    ids = [r.id for r in runs]
    assert r1.id in ids
    assert r2.id in ids
    # ordered started_at DESC — r2 should come first (created later)
    assert runs[0].id == r2.id


def test_get_run_not_found(session):
    result = get_run(session, "nope")
    assert result is None


def test_close_run(session):
    run = create_run(session, server_name="fs")
    assert run.ended_at is None
    ended = datetime.now(timezone.utc)
    close_run(session, run.id, ended)
    updated = get_run(session, run.id)
    assert updated is not None
    assert updated.ended_at is not None


# ---------------------------------------------------------------------------
# FrameRecorder round-trip
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_frame_recorder_tool_call_roundtrip(engine):
    """Drive FrameRecorder with a synthetic request + response pair."""
    from mcp.types import JSONRPCRequest, JSONRPCResponse

    with Session(engine) as session:
        run = create_run(session, server_name="test")
        run_id = run.id

    recorder = FrameRecorder(run_id=run_id, engine=engine)

    # Outbound tools/call request
    request = JSONRPCRequest(
        jsonrpc="2.0",
        id=42,
        method="tools/call",
        params={"name": "read_file", "arguments": {"path": "/tmp/foo.txt"}},
    )
    await recorder.on_frame(run_id, "client→upstream", request)

    # Inbound response (no method field)
    response = JSONRPCResponse(
        jsonrpc="2.0",
        id=42,
        result={"content": [{"type": "text", "text": "hello"}]},
    )
    await recorder.on_frame(run_id, "upstream→client", response)

    with Session(engine) as session:
        spans = get_spans(session, run_id)
        assert len(spans) == 1
        span = spans[0]
        assert span.method == "tools/call"
        assert span.duration_ms is not None
        assert span.duration_ms >= 0

        from sqlmodel import select
        from app.models import ToolCall

        tcs = list(session.exec(select(ToolCall).where(ToolCall.run_id == run_id)).all())
        assert len(tcs) == 1
        tc = tcs[0]
        assert tc.tool_name == "read_file"
        assert tc.result_json is not None
        result_data = json.loads(tc.result_json)
        assert "content" in result_data
        assert tc.duration_ms is not None
        assert tc.duration_ms >= 0
