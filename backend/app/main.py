"""KaarigarAI backend — FastAPI entrypoint (stateless).

Serves the JSON API for the mobile app AND renders the public storefront and
listing pages. AI work is dispatched to workers behind a job queue, never inline.
Roadmap: Days 1-6 done (onboarding, listing page, offers, storefront + market linkage).
"""
import os
import sys
from pathlib import Path

# pricing.py (Day 4) imports the top-level `pipelines` package, which lives at
# the repo root, a sibling of `backend/` — not on sys.path when this app is
# run the documented way (`cd backend && uvicorn app.main:app`). Add it here,
# once, so that command keeps working unmodified rather than requiring every
# future run instruction (and everyone's memory) to carry a PYTHONPATH prefix.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db.session import init_db
from app.api.sync import router as sync_router
from app.api.pricing import router as pricing_router
from app.api.onboarding import router as onboarding_router
from app.api.listings import router as listings_router
from app.api.offers import router as offers_router
from app.api.storefront import router as storefront_api_router
from app.web.storefront_page import router as storefront_router

app = FastAPI(title="KaarigarAI API")


@app.on_event("startup")
def _startup() -> None:
    init_db()


# Mount API routers
app.include_router(sync_router, prefix="/api")
app.include_router(pricing_router, prefix="/api")
app.include_router(onboarding_router, prefix="/api")
app.include_router(listings_router, prefix="/api")
app.include_router(offers_router, prefix="/api")
app.include_router(storefront_api_router, prefix="/api")

# Public web pages (permanent URLs, no /api prefix — e.g. GET /l/<listing_id>)
app.include_router(storefront_router)

# Listing photos, served directly from local disk. The architecture doc calls
# for real object storage ("never from the app host") — none is configured
# (no S3/GCS credentials), so this is a disclosed prototype substitute, not a
# silent one. Swapping in real object storage only changes Listing.image_path
# to a full URL and removes this mount.
_UPLOADS_DIR = _REPO_ROOT / "backend" / "data" / "uploads"
os.makedirs(_UPLOADS_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_UPLOADS_DIR)), name="media")
