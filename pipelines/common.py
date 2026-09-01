"""Shared helpers for the AI pipelines: config loading, small utilities.

Pipelines are independent of the backend, so config is loaded directly from
config/config.yaml rather than through the FastAPI app.
"""
from __future__ import annotations

import functools
import os
from pathlib import Path

import yaml

# repo root = two levels up from this file (pipelines/common.py -> repo/)
REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "config.yaml"
ENV_PATH = REPO_ROOT / ".env"


@functools.lru_cache(maxsize=1)
def load_env() -> None:
    """Load repo-root .env into os.environ once (no-op if the file / dotenv is absent).

    Secrets (GEMINI_API_KEY etc.) live in .env, never in config.yaml or git.
    """
    if not ENV_PATH.exists():
        return
    try:
        from dotenv import load_dotenv
    except Exception:
        # minimal parser so a missing python-dotenv doesn't break key lookup
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip("'\""))
        return
    load_dotenv(ENV_PATH)


def env_get(key: str, default: str | None = None) -> str | None:
    """Read an env var, loading .env first. Returns default if unset/empty."""
    load_env()
    return os.environ.get(key) or default


@functools.lru_cache(maxsize=1)
def load_config() -> dict:
    """Load config/config.yaml once. Returns {} if the file is missing."""
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def cfg_get(path: str, default=None):
    """Dotted lookup into the config, e.g. cfg_get('image.failure_contrast_min')."""
    node = load_config()
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node
