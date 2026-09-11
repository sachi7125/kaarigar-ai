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
# Hosted Postgres providers often hand out postgres:// URLs, which SQLAlchemy 2
# no longer accepts.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = "postgresql://" + DATABASE_URL[len("postgres://"):]

# Base every QR code, share card and export link is built from. Defaults to the
# permanent address in config.yaml; KAARIGAR_PUBLIC_URL overrides it per run —
# scripts/run_server.sh sets it to this Mac's Wi-Fi address for the offline
# demo, or it comes from .env as the Vercel address when the database is the
# shared cloud one.
PUBLIC_URL = (env_get("KAARIGAR_PUBLIC_URL") or cfg_get("listings.url_base", "https://kaarigar.in")).rstrip("/")

__all__ = ["cfg_get", "env_get", "load_config", "DATABASE_URL", "PUBLIC_URL", "REPO_ROOT"]
