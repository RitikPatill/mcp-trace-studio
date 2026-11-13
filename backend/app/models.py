from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Run(SQLModel, table=True):
    id: str = Field(primary_key=True)
    started_at: datetime
    ended_at: Optional[datetime] = Field(default=None)
    server_name: str
    model_name: Optional[str] = Field(default=None)


class Span(SQLModel, table=True):
    id: str = Field(primary_key=True)
    run_id: str = Field(index=True)
    direction: str  # "client→upstream" | "upstream→client"
    method: Optional[str] = Field(default=None)
    msg_id: Optional[str] = Field(default=None)  # str(frame.id)
    started_at: datetime
    ended_at: Optional[datetime] = Field(default=None)
    duration_ms: Optional[float] = Field(default=None)


class ToolCall(SQLModel, table=True):
    id: str = Field(primary_key=True)
    span_id: str
    run_id: str = Field(index=True)
    tool_name: str
    args_json: str  # JSON string of params["arguments"]
    result_json: Optional[str] = Field(default=None)
    error: Optional[str] = Field(default=None)
    started_at: datetime
    ended_at: Optional[datetime] = Field(default=None)
    duration_ms: Optional[float] = Field(default=None)
