"""Integration tests for the REST API."""
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
from app.models import Run, Span
from app.store import create_run


@pytest.fixture(autouse=True)
def override_db(tmp_path):
    """Replace the DB with a fresh in-memory SQLite for every test."""
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


# ---------------------------------------------------------------------------
# GET /runs
# ---------------------------------------------------------------------------


def test_list_runs_empty(client):
    r = client.get("/runs")
    assert r.status_code == 200
    assert r.json() == []


def test_list_runs_returns_created(client, override_db):
    with Session(override_db) as session:
        create_run(session, server_name="fs")

    r = client.get("/runs")
    assert r.status_code == 200
    runs = r.json()
    assert len(runs) == 1
    assert runs[0]["server_name"] == "fs"


# ---------------------------------------------------------------------------
# GET /runs/{id}
# ---------------------------------------------------------------------------


def test_run_not_found(client):
    r = client.get("/runs/does-not-exist")
    assert r.status_code == 404


def test_get_run(client, override_db):
    with Session(override_db) as session:
        run = create_run(session, server_name="web")
        run_id = run.id

    r = client.get(f"/runs/{run_id}")
    assert r.status_code == 200
    assert r.json()["id"] == run_id


# ---------------------------------------------------------------------------
# GET /runs/{id}/spans
# ---------------------------------------------------------------------------


def test_get_spans_run_not_found(client):
    r = client.get("/runs/does-not-exist/spans")
    assert r.status_code == 404


def test_create_run_and_get_spans(client, override_db):
    now = datetime.now(timezone.utc)

    with Session(override_db) as session:
        run = create_run(session, server_name="fs")
        run_id = run.id

        for i in range(2):
            span = Span(
                id=str(uuid.uuid4()),
                run_id=run_id,
                direction="client→upstream",
                method="tools/list",
                started_at=now,
                ended_at=now,
                duration_ms=0.0,
            )
            session.add(span)
        session.commit()

    r = client.get(f"/runs/{run_id}/spans")
    assert r.status_code == 200
    spans = r.json()
    assert len(spans) == 2
