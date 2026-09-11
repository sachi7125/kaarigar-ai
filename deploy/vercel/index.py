"""Vercel entrypoint: the buyer-facing app (backend/app/public_main.py).

scripts/build_vercel.sh copies this file next to a whitelisted copy of
backend/app, pipelines/common.py and config/, keeping the repo's own layout
so the imports work unchanged.
"""
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
for _p in (_ROOT, _ROOT / "backend"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from app.public_main import app  # noqa: E402,F401
