from __future__ import annotations

import asyncio
import collections
from datetime import datetime, timezone
from typing import Optional

import anyio
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlmodel import Session

from ..database import get_engine, get_session
from ..proxy.config import load_servers
from ..settings import settings
from ..store import (
    close_run,
    count_tool_calls_for_run,
    create_run,
    get_run,
    get_spans,
    get_spans_after,
    get_tool_calls_for_run,
    get_tool_calls_for_spans,
)
from ..store import list_runs as store_list_runs
from ..models import Span
from .replay import execute_replay

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
    tool_call_count: int = 0
    parent_run_id: Optional[str] = None


class ReplayRequest(BaseModel):
    server_name: str
    model_name: Optional[str] = None


class DiffEntry(BaseModel):
    tool_name: str
    call_index: int
    tool_call_a: Optional[ToolCallRead]
    tool_call_b: Optional[ToolCallRead]
    args_changed: bool
    result_changed: bool
    latency_delta_ms: Optional[float]


class DiffResult(BaseModel):
    run_a: RunRead
    run_b: RunRead
    entries: list[DiffEntry]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_tool_call_read(tc) -> ToolCallRead:
    return ToolCallRead(
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


def _to_run_read(run, session: Session) -> RunRead:
    return RunRead(
        id=run.id,
        started_at=run.started_at,
        ended_at=run.ended_at,
        server_name=run.server_name,
        model_name=run.model_name,
        tool_call_count=count_tool_calls_for_run(session, run.id),
        parent_run_id=run.parent_run_id,
    )


def _spans_with_tool_calls(spans: list[Span], session: Session) -> list[SpanRead]:
    span_ids = [s.id for s in spans]
    tcs = get_tool_calls_for_spans(session, span_ids)
    tc_by_span: dict[str, list[ToolCallRead]] = {}
    for tc in tcs:
        tc_by_span.setdefault(tc.span_id, []).append(_to_tool_call_read(tc))

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
    return [_to_run_read(r, session) for r in runs]


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


@router.post("/{run_id}/replay", response_model=RunRead, status_code=202)
async def replay_run_endpoint(
    run_id: str,
    body: ReplayRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> RunRead:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    try:
        servers = load_servers(settings.servers_yaml)
    except FileNotFoundError:
        raise HTTPException(
            status_code=400,
            detail=f"servers config not found: {settings.servers_yaml}",
        )

    if body.server_name not in servers:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown server '{body.server_name}'. Available: {sorted(servers.keys())}",
        )

    server_cfg = servers[body.server_name]
    new_run = create_run(
        session,
        server_name=body.server_name,
        model_name=body.model_name if body.model_name is not None else run.model_name,
        parent_run_id=run_id,
    )

    background_tasks.add_task(execute_replay, run_id, new_run.id, server_cfg, get_engine())

    return RunRead(
        id=new_run.id,
        started_at=new_run.started_at,
        ended_at=None,
        server_name=new_run.server_name,
        model_name=new_run.model_name,
        tool_call_count=0,
        parent_run_id=new_run.parent_run_id,
    )


@router.get("/{run_id_a}/diff/{run_id_b}", response_model=DiffResult)
def get_diff(
    run_id_a: str,
    run_id_b: str,
    session: Session = Depends(get_session),
) -> DiffResult:
    run_a = get_run(session, run_id_a)
    if run_a is None:
        raise HTTPException(status_code=404, detail="Run A not found")
    run_b = get_run(session, run_id_b)
    if run_b is None:
        raise HTTPException(status_code=404, detail="Run B not found")

    tcs_a = get_tool_calls_for_run(session, run_id_a)
    tcs_b = get_tool_calls_for_run(session, run_id_b)

    by_name_a: dict[str, list] = collections.defaultdict(list)
    by_name_b: dict[str, list] = collections.defaultdict(list)

    for tc in tcs_a:
        by_name_a[tc.tool_name].append(tc)
    for tc in tcs_b:
        by_name_b[tc.tool_name].append(tc)

    all_names = sorted(set(by_name_a.keys()) | set(by_name_b.keys()))

    entries: list[DiffEntry] = []
    for tool_name in all_names:
        list_a = by_name_a[tool_name]
        list_b = by_name_b[tool_name]
        max_len = max(len(list_a), len(list_b))

        for i in range(max_len):
            tca = list_a[i] if i < len(list_a) else None
            tcb = list_b[i] if i < len(list_b) else None

            args_changed = False
            result_changed = False
            latency_delta_ms: float | None = None

            if tca is not None and tcb is not None:
                args_changed = tca.args_json != tcb.args_json
                result_changed = tca.result_json != tcb.result_json
                if tca.duration_ms is not None and tcb.duration_ms is not None:
                    latency_delta_ms = tcb.duration_ms - tca.duration_ms

            entries.append(
                DiffEntry(
                    tool_name=tool_name,
                    call_index=i,
                    tool_call_a=_to_tool_call_read(tca) if tca is not None else None,
                    tool_call_b=_to_tool_call_read(tcb) if tcb is not None else None,
                    args_changed=args_changed,
                    result_changed=result_changed,
                    latency_delta_ms=latency_delta_ms,
                )
            )

    return DiffResult(
        run_a=_to_run_read(run_a, session),
        run_b=_to_run_read(run_b, session),
        entries=entries,
    )


@router.get("/{run_id}", response_model=RunRead)
def get_run_endpoint(
    run_id: str,
    session: Session = Depends(get_session),
) -> RunRead:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return _to_run_read(run, session)


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
