"""DB engine + session factory.

SQLite for now (see app/config.py, decision D17) — `connect_args` and
`with_for_update()` behaviour below are the two spots that differ from
Postgres, both called out where they matter.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import DATABASE_URL

_is_sqlite = DATABASE_URL.startswith("sqlite")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if _is_sqlite else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db() -> None:
    """Create tables that don't exist yet. No migrations (Alembic) at this
    stage — acceptable while the schema is still moving; revisit before the
    schema is genuinely frozen (the permanent listing-id format already is,
    per db/models.py's own note)."""
    from app.db import models  # noqa: F401  (registers models on Base.metadata)
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency: yields a session, always closed after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
