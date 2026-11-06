from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import Engine, event
from sqlmodel import Session, SQLModel, create_engine

from .settings import settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def set_wal_mode(dbapi_conn, _connection_record):
        dbapi_conn.execute("PRAGMA journal_mode=WAL")

    return engine


def init_db() -> None:
    from . import models  # noqa: F401 — registers table metadata

    SQLModel.metadata.create_all(get_engine())


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
