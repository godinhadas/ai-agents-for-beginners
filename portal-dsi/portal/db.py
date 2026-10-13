"""Ligação à base de dados (SQLite por omissão, configurável por PORTAL_DATABASE_URL)."""

import os
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool


class Base(DeclarativeBase):
    pass


engine: Engine | None = None
SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)


def configure(url: str | None = None) -> Engine:
    """(Re)configura o motor. Os testes usam 'sqlite://' (memória)."""
    global engine
    url = url or os.getenv("PORTAL_DATABASE_URL", "sqlite:///./portal.db")
    kwargs: dict = {}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
    engine = create_engine(url, **kwargs)

    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):
            # SQLite só aplica chaves estrangeiras com este PRAGMA.
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    SessionLocal.configure(bind=engine)
    return engine


def init_db() -> None:
    from . import models  # noqa: F401  (regista as tabelas)

    if engine is None:
        configure()
    Base.metadata.create_all(engine)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
