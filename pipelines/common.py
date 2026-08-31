"""Shared helpers for the AI pipelines: config loading, small utilities.

Pipelines are independent of the backend, so config is loaded directly from
config/config.yaml rather than through the FastAPI app.
"""
from __future__ import annotations

import functools
from pathlib import Path

import yaml

# repo root = two levels up from this file (pipelines/common.py -> repo/)
REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "config" / "config.yaml"


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
