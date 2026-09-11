"""DB engine + session factory.

SQLite locally, Postgres when DATABASE_URL points at one (app/config.py,
decision D17) — `connect_args` and `with_for_update()` behaviour are the spots
that differ, both called out where they matter.
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy.schema import CreateColumn

from app.config import DATABASE_URL

_is_sqlite = DATABASE_URL.startswith("sqlite")

_engine_kwargs: dict = {}
if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs["pool_pre_ping"] = True
    if os.environ.get("VERCEL"):
        # Each serverless invocation may be a fresh process; don't hold pooled
        # connections open against the hosted database between them.
        _engine_kwargs["poolclass"] = NullPool

engine = create_engine(DATABASE_URL, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db(bind=None) -> None:
    """Create missing tables, then add missing columns to existing ones. Still
    no Alembic: this only ever ADDS, so a column added to models.py reaches a
    database created before it (the dev DB, the phone's shop) without deleting
    anything. Renames, type changes and drops still need a hand migration."""
    from app.db import models  # noqa: F401  (registers models on Base.metadata)
    bind = bind or engine
    Base.metadata.create_all(bind=bind)
    add_missing_columns(bind)


def add_missing_columns(bind) -> list[str]:
    """ALTER TABLE ... ADD COLUMN for every model column the database lacks.
    Returns the "table.column" names it added."""
    inspector = inspect(bind)
    quote = bind.dialect.identifier_preparer.quote
    added: list[str] = []
    with bind.begin() as conn:
        for table in Base.metadata.sorted_tables:
            present = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in present:
                    continue
                if not column.nullable and column.server_default is None:
                    raise RuntimeError(
                        f"{table.name}.{column.name} is NOT NULL with no server_default, so it "
                        "can't be added to a table that already has rows — give it one")
                spec = CreateColumn(column).compile(dialect=bind.dialect)
                conn.execute(text(f"ALTER TABLE {quote(table.name)} ADD COLUMN {spec}"))
                added.append(f"{table.name}.{column.name}")
    return added


def get_db():
    """FastAPI dependency: yields a session, always closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
