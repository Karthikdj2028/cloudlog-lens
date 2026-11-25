"""Explicit database engine/session construction; importing this module has no side effects."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def build_engine(database_url: str, *, echo: bool = False) -> Engine:
    """Build a database engine; SQLite connections enforce foreign keys."""
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, echo=echo, connect_args=connect_args)
    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return engine


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Create sessions with explicit transaction ownership."""
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Yield one transaction and commit/rollback at the application boundary."""
    session = factory()
    try:
        with session.begin():
            yield session
    finally:
        session.close()
