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
    _completar_esquema()


def _completar_esquema() -> None:
    """Acrescenta colunas novas a tabelas já existentes (actualizações sem perder dados).

    Solução simples para SQLite enquanto não há migrações formais (Alembic): só acrescenta
    colunas em falta e normaliza valores de versões anteriores; nunca apaga nada.
    """
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    with engine.begin() as con:
        for tabela in Base.metadata.sorted_tables:
            if not insp.has_table(tabela.name):
                continue
            existentes = {c["name"] for c in insp.get_columns(tabela.name)}
            for col in tabela.columns:
                if col.name in existentes:
                    continue
                tipo = col.type.compile(dialect=engine.dialect)
                padrao = col.default.arg if col.default is not None and not callable(col.default.arg) else None
                sql = f'ALTER TABLE {tabela.name} ADD COLUMN "{col.name}" {tipo}'
                if isinstance(padrao, bool):
                    sql += f" DEFAULT {int(padrao)}"
                elif isinstance(padrao, (int, float)):
                    sql += f" DEFAULT {padrao}"
                elif isinstance(padrao, str):
                    sql += " DEFAULT '" + padrao.replace("'", "''") + "'"
                con.execute(text(sql))
        # Valores de versões anteriores
        if insp.has_table("utilizadores"):
            con.execute(text("UPDATE utilizadores SET perfil='colaborador' WHERE perfil='chefia'"))
        for t in ("catalogo", "pedidos"):
            if insp.has_table(t):
                con.execute(text(f"UPDATE {t} SET tipo='intervencao' WHERE tipo='incidente'"))
                con.execute(text(f"UPDATE {t} SET tipo='outro' WHERE tipo='informacao'"))


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
