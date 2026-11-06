from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

import anyio
from sqlalchemy import Engine
from sqlmodel import Session, select

from .models import Run, Span, ToolCall


# ---------------------------------------------------------------------------
# Plain sync helpers (all accept Session, no global state)
# ---------------------------------------------------------------------------


def create_run(
    session: Session,
    server_name: str,
    model_name: str | None = None,
) -> Run:
    run = Run(
        id=str(uuid.uuid4()),
        started_at=datetime.now(timezone.utc),
        server_name=server_name,
        model_name=model_name,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def close_run(session: Session, run_id: str, ended_at: datetime) -> None:
    run = session.get(Run, run_id)
    if run is None:
        return
    run.ended_at = ended_at
    session.add(run)
    session.commit()


def list_runs(session: Session) -> list[Run]:
    stmt = select(Run).order_by(Run.started_at.desc())  # type: ignore[arg-type]
    return list(session.exec(stmt).all())


def get_run(session: Session, run_id: str) -> Run | None:
    return session.get(Run, run_id)


def get_spans(session: Session, run_id: str) -> list[Span]:
    stmt = select(Span).where(Span.run_id == run_id).order_by(Span.started_at)  # type: ignore[arg-type]
    return list(session.exec(stmt).all())


def get_spans_after(session: Session, run_id: str, after: datetime) -> list[Span]:
    stmt = (
        select(Span)
        .where(Span.run_id == run_id, Span.started_at > after)
        .order_by(Span.started_at)  # type: ignore[arg-type]
    )
    return list(session.exec(stmt).all())


def get_tool_calls_for_spans(
    session: Session, span_ids: list[str]
) -> list[ToolCall]:
    if not span_ids:
        return []
    stmt = select(ToolCall).where(ToolCall.span_id.in_(span_ids))  # type: ignore[attr-defined]
    return list(session.exec(stmt).all())


# ---------------------------------------------------------------------------
# FrameRecorder — stateful per-run, NOT thread-safe, single async task only
# ---------------------------------------------------------------------------


class FrameRecorder:
    """Correlates request→response frames and writes Spans + ToolCalls."""

    def __init__(self, run_id: str, engine: Engine) -> None:
        self._run_id = run_id
        self._engine = engine
        # msg_id → (span_id, tool_call_id, started_at)
        self._pending: dict[str, tuple[str, str, datetime]] = {}

    async def on_frame(
        self,
        run_id: str,
        direction: str,
        frame: Any,
    ) -> None:
        method: str | None = getattr(frame, "method", None)
        frame_id = getattr(frame, "id", None)
        msg_id = str(frame_id) if frame_id is not None else None

        now = datetime.now(timezone.utc)

        if direction == "client→upstream" and method == "tools/call":
            # Start of a tool call — write Span + ToolCall skeleton
            span_id = str(uuid.uuid4())
            tc_id = str(uuid.uuid4())

            params = getattr(frame, "params", None) or {}
            if isinstance(params, dict):
                tool_name = params.get("name", "")
                arguments = params.get("arguments", {})
            else:
                tool_name = getattr(params, "name", "")
                arguments = getattr(params, "arguments", {}) or {}

            args_json = json.dumps(arguments)

            def _write_start(session: Session) -> None:
                span = Span(
                    id=span_id,
                    run_id=run_id,
                    direction=direction,
                    method=method,
                    msg_id=msg_id,
                    started_at=now,
                )
                tc = ToolCall(
                    id=tc_id,
                    span_id=span_id,
                    run_id=run_id,
                    tool_name=tool_name,
                    args_json=args_json,
                    started_at=now,
                )
                session.add(span)
                session.add(tc)
                session.commit()

            await anyio.to_thread.run_sync(
                lambda: _write_with_engine(self._engine, _write_start)
            )

            if msg_id is not None:
                self._pending[msg_id] = (span_id, tc_id, now)

        elif (
            direction == "upstream→client"
            and method is None
            and msg_id is not None
            and msg_id in self._pending
        ):
            # Completion of a pending tool call
            span_id, tc_id, started_at = self._pending.pop(msg_id)
            ended_at = datetime.now(timezone.utc)
            duration_ms = (ended_at - started_at).total_seconds() * 1000

            result_obj = getattr(frame, "result", None)
            error_obj = getattr(frame, "error", None)
            result_json = json.dumps(result_obj) if result_obj is not None else None
            error_str = json.dumps(error_obj) if error_obj is not None else None

            def _write_end(session: Session) -> None:
                span = session.get(Span, span_id)
                if span is not None:
                    span.ended_at = ended_at
                    span.duration_ms = duration_ms
                    session.add(span)
                tc = session.get(ToolCall, tc_id)
                if tc is not None:
                    tc.result_json = result_json
                    tc.error = error_str
                    tc.ended_at = ended_at
                    tc.duration_ms = duration_ms
                    session.add(tc)
                session.commit()

            await anyio.to_thread.run_sync(
                lambda: _write_with_engine(self._engine, _write_end)
            )

        else:
            # Non-tool-call frame — just record the span with both timestamps = now
            span_id = str(uuid.uuid4())

            def _write_other(session: Session) -> None:
                span = Span(
                    id=span_id,
                    run_id=run_id,
                    direction=direction,
                    method=method,
                    msg_id=msg_id,
                    started_at=now,
                    ended_at=now,
                    duration_ms=0.0,
                )
                session.add(span)
                session.commit()

            await anyio.to_thread.run_sync(
                lambda: _write_with_engine(self._engine, _write_other)
            )


def _write_with_engine(engine: Engine, fn: Callable[[Session], None]) -> None:
    with Session(engine) as session:
        fn(session)
