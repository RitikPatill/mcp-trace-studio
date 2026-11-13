from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

import anyio
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlmodel import Session

from ..database import get_session
from ..store import get_run, get_spans, get_spans_after, get_tool_calls_for_spans
from ..store import list_runs as store_list_runs
from ..models import Span

router = APIRouter(prefix="/runs")
ws_router = APIRouter(prefix="/ws")


# ---------------------------------------------------------------------------
# Read models (plain Pydantic — not table=True)
# ---------------------------------------------------------------------------


class ToolCallRead(BaseModel):
    id: str
    span_id: str
    run_id: str
    tool_name: str
    args_json: str
    result_json: Optional[str]
    error: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    duration_ms: Optional[float]


class SpanRead(BaseModel):
    id: str
    run_id: str
    direction: str
    method: Optional[str]
    msg_id: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    duration_ms: Optional[float]
    tool_calls: list[ToolCallRead] = []


class RunRead(BaseModel):
    id: str
    started_at: datetime
    ended_at: Optional[datetime]
    server_name: str
    model_name: Optional[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _spans_with_tool_calls(spans: list[Span], session: Session) -> list[SpanRead]:
    span_ids = [s.id for s in spans]
    tcs = get_tool_calls_for_spans(session, span_ids)
    tc_by_span: dict[str, list[ToolCallRead]] = {}
    for tc in tcs:
        tc_by_span.setdefault(tc.span_id, []).append(
            ToolCallRead(
                id=tc.id,
                span_id=tc.span_id,
                run_id=tc.run_id,
                tool_name=tc.tool_name,
                args_json=tc.args_json,
                result_json=tc.result_json,
                error=tc.error,
                started_at=tc.started_at,
                ended_at=tc.ended_at,
                duration_ms=tc.duration_ms,
            )
        )

    return [
        SpanRead(
            id=s.id,
            run_id=s.run_id,
            direction=s.direction,
            method=s.method,
            msg_id=s.msg_id,
            started_at=s.started_at,
            ended_at=s.ended_at,
            duration_ms=s.duration_ms,
            tool_calls=tc_by_span.get(s.id, []),
        )
        for s in spans
    ]


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[RunRead])
def list_runs(session: Session = Depends(get_session)) -> list[RunRead]:
    runs = store_list_runs(session)
    return [
        RunRead(
            id=r.id,
            started_at=r.started_at,
            ended_at=r.ended_at,
            server_name=r.server_name,
            model_name=r.model_name,
        )
        for r in runs
    ]


@router.get("/{run_id}", response_model=RunRead)
def get_run_endpoint(
    run_id: str,
    session: Session = Depends(get_session),
) -> RunRead:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunRead(
        id=run.id,
        started_at=run.started_at,
        ended_at=run.ended_at,
        server_name=run.server_name,
        model_name=run.model_name,
    )


@router.get("/{run_id}/spans", response_model=list[SpanRead])
def get_run_spans(
    run_id: str,
    session: Session = Depends(get_session),
) -> list[SpanRead]:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    spans = get_spans(session, run_id)
    return _spans_with_tool_calls(spans, session)


# ---------------------------------------------------------------------------
# WebSocket — live stream
# ---------------------------------------------------------------------------


@ws_router.websocket("/runs/{run_id}")
async def ws_run_spans(run_id: str, websocket: WebSocket) -> None:
    await websocket.accept()
    last_seen = datetime.min.replace(tzinfo=timezone.utc)
    try:
        while True:
            def _fetch(last: datetime = last_seen):
                from ..database import get_engine
                from sqlmodel import Session as _Session
                with _Session(get_engine()) as sess:
                    run = get_run(sess, run_id)
                    if run is None:
                        return None
                    spans = get_spans_after(sess, run_id, last)
                    return _spans_with_tool_calls(spans, sess)

            result = await anyio.to_thread.run_sync(_fetch)
            if result is None:
                await websocket.close(code=4004, reason="Run not found")
                return

            if result:
                for span_read in result:
                    await websocket.send_text(span_read.model_dump_json())
                    last_seen = max(last_seen, span_read.started_at)

            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
