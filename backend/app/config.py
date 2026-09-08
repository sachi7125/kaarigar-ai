"""Loads config/config.yaml and .env. Single source of tunables + secrets.

Reuses pipelines.common's loader rather than re-implementing it — the backend
and the pipelines read the same config.yaml, so there is exactly one parser.
Adds only what's backend-specific: the database URL.

DATABASE_URL defaults to a local SQLite file. The architecture doc specifies
PostgreSQL ("single system of record") and none is installed on this dev
machine — SQLAlchemy's engine URL is the only thing that changes to move to
Postgres later (set DATABASE_URL in .env), so nothing here is Postgres-specific
by accident. See decision D17.
"""
from __future__ import annotations

from pipelines.common import cfg_get, env_get, load_config, REPO_ROOT

DATABASE_URL = env_get("DATABASE_URL") or f"sqlite:///{REPO_ROOT / 'backend' / 'data' / 'kaarigar.db'}"

__all__ = ["cfg_get", "env_get", "load_config", "DATABASE_URL", "REPO_ROOT"]
