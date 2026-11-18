"""Tests for POST /runs/{id}/replay."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import models  # noqa: F401 — registers table metadata
from app.database import get_session
from app.main import app
from app.models import Run, ToolCall
from app.store import create_run


@pytest.fixture(autouse=True)
def override_db(tmp_path):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(test_engine)

    def _get_test_session():
        with Session(test_engine) as session:
            yield session

    app.dependency_overrides[get_session] = _get_test_session
    yield test_engine
    app.dependency_overrides.clear()
    SQLModel.metadata.drop_all(test_engine)


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def servers_yaml(tmp_path: Path) -> Path:
    p = tmp_path / "servers.yaml"
    p.write_text("servers:\n  fake:\n    command: echo\n    args: []\n")
    return p


@pytest.fixture()
def run_with_tool_calls(override_db):
    """Seed a run with two ToolCall rows; return the run id."""
    with Session(override_db) as session:
        run = create_run(session, server_name="fake")
        run_id = run.id  # capture before session closes
        for i in range(2):
            tc = ToolCall(
                id=str(uuid.uuid4()),
                span_id=str(uuid.uuid4()),
                run_id=run_id,
                tool_name="list_files",
                args_json=f'{{"path": "/tmp/{i}"}}',
                result_json='["a.txt"]',
                started_at=datetime.now(timezone.utc),
                ended_at=datetime.now(timezone.utc),
                duration_ms=float(10 + i),
            )
            session.add(tc)
        session.commit()
    return run_id


def test_replay_returns_new_run(client, run_with_tool_calls, servers_yaml):
    """POST /runs/{id}/replay returns 202 with a new run id."""
    noop = AsyncMock(return_value=None)
    with (
        patch("app.api.runs.execute_replay", noop),
        patch("app.api.runs.settings") as mock_settings,
    ):
        mock_settings.servers_yaml = str(servers_yaml)
        r = client.post(
            f"/runs/{run_with_tool_calls}/replay",
            json={"server_name": "fake"},
        )

    assert r.status_code == 202
    data = r.json()
    assert data["id"] != run_with_tool_calls
    assert data["parent_run_id"] == run_with_tool_calls
    assert data["server_name"] == "fake"
    assert data["tool_call_count"] == 0
    assert data["ended_at"] is None


def test_replay_404_original_not_found(client, servers_yaml):
    noop = AsyncMock(return_value=None)
    with (
        patch("app.api.runs.execute_replay", noop),
        patch("app.api.runs.settings") as mock_settings,
    ):
        mock_settings.servers_yaml = str(servers_yaml)
        r = client.post(
            "/runs/does-not-exist/replay",
            json={"server_name": "fake"},
        )
    assert r.status_code == 404


def test_replay_400_unknown_server(client, run_with_tool_calls, servers_yaml):
    noop = AsyncMock(return_value=None)
    with (
        patch("app.api.runs.execute_replay", noop),
        patch("app.api.runs.settings") as mock_settings,
    ):
        mock_settings.servers_yaml = str(servers_yaml)
        r = client.post(
            f"/runs/{run_with_tool_calls}/replay",
            json={"server_name": "does_not_exist"},
        )
    assert r.status_code == 400
    assert "does_not_exist" in r.json()["detail"]
