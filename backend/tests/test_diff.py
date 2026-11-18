"""Tests for GET /runs/{a}/diff/{b}."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app import models  # noqa: F401 — registers table metadata
from app.database import get_session
from app.main import app
from app.models import ToolCall
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


def _make_tc(session, run_id, tool_name, args_json, result_json, duration_ms):
    tc = ToolCall(
        id=str(uuid.uuid4()),
        span_id=str(uuid.uuid4()),
        run_id=run_id,
        tool_name=tool_name,
        args_json=args_json,
        result_json=result_json,
        started_at=datetime.now(timezone.utc),
        ended_at=datetime.now(timezone.utc),
        duration_ms=duration_ms,
    )
    session.add(tc)


@pytest.fixture()
def two_runs(override_db):
    """Seed run A and run B with aligned + mismatched tool calls."""
    with Session(override_db) as session:
        run_a = create_run(session, server_name="fs")
        run_b = create_run(session, server_name="fs")
        id_a = run_a.id  # capture before session closes
        id_b = run_b.id

        # Shared tool — different args/results
        _make_tc(session, id_a, "read_file", '{"path":"/a"}', '"hello"', 10.0)
        _make_tc(session, id_b, "read_file", '{"path":"/b"}', '"world"', 20.0)

        # Second call of same tool — also different
        _make_tc(session, id_a, "read_file", '{"path":"/c"}', '"foo"', 5.0)
        _make_tc(session, id_b, "read_file", '{"path":"/c"}', '"bar"', 15.0)

        # Tool only in run A
        _make_tc(session, id_a, "list_dir", '{"path":"/"}', '"[]"', 3.0)

        session.commit()
    return id_a, id_b


def test_diff_ok(client, two_runs):
    a, b = two_runs
    r = client.get(f"/runs/{a}/diff/{b}")
    assert r.status_code == 200
    data = r.json()
    assert data["run_a"]["id"] == a
    assert data["run_b"]["id"] == b
    entries = data["entries"]
    # At least 3 entries: 2 × read_file + 1 × list_dir
    assert len(entries) >= 3


def test_diff_aligned_by_tool_and_index(client, two_runs):
    a, b = two_runs
    data = client.get(f"/runs/{a}/diff/{b}").json()
    entries = data["entries"]

    rf_entries = [e for e in entries if e["tool_name"] == "read_file"]
    assert len(rf_entries) == 2
    assert rf_entries[0]["call_index"] == 0
    assert rf_entries[1]["call_index"] == 1


def test_diff_args_changed(client, two_runs):
    a, b = two_runs
    data = client.get(f"/runs/{a}/diff/{b}").json()
    rf = [e for e in data["entries"] if e["tool_name"] == "read_file"]
    assert rf[0]["args_changed"] is True
    assert rf[0]["result_changed"] is True


def test_diff_latency_delta(client, two_runs):
    a, b = two_runs
    data = client.get(f"/runs/{a}/diff/{b}").json()
    rf = [e for e in data["entries"] if e["tool_name"] == "read_file"]
    # run_b duration 20 − run_a duration 10 = 10
    assert abs(rf[0]["latency_delta_ms"] - 10.0) < 0.001


def test_diff_one_sided_entry(client, two_runs):
    """list_dir only exists in run A — tool_call_b should be null."""
    a, b = two_runs
    data = client.get(f"/runs/{a}/diff/{b}").json()
    ld = [e for e in data["entries"] if e["tool_name"] == "list_dir"]
    assert len(ld) == 1
    assert ld[0]["tool_call_a"] is not None
    assert ld[0]["tool_call_b"] is None


def test_diff_404_run_a_not_found(client, two_runs):
    _, b = two_runs
    r = client.get(f"/runs/nonexistent/diff/{b}")
    assert r.status_code == 404


def test_diff_404_run_b_not_found(client, two_runs):
    a, _ = two_runs
    r = client.get(f"/runs/{a}/diff/nonexistent")
    assert r.status_code == 404
