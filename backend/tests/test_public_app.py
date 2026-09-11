"""The Vercel app (app/public_main.py): buyer pages and buyer actions only,
without the ML stack and without any artisan-only endpoint."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Artisan, Listing, ListingPhoto
from app.db.session import Base, get_db

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
HEAVY_MODULES = ("cv2", "faster_whisper", "ctranslate2", "onnxruntime", "xgboost", "sklearn",
                 "numpy", "pandas", "PIL", "openpyxl", "qrcode")


def test_public_app_imports_without_the_ai_stack():
    code = ("import sys, app.public_main; "
            f"heavy = [m for m in {HEAVY_MODULES!r} if m in sys.modules]; "
            "print(heavy); sys.exit(1 if heavy else 0)")
    env = {**os.environ, "PYTHONPATH": os.pathsep.join([str(BACKEND), str(REPO)])}
    r = subprocess.run([sys.executable, "-c", code], cwd=BACKEND, env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.fixture()
def client():
    from app.public_main import app

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _db
    try:
        yield TestClient(app), Session
    finally:
        app.dependency_overrides.clear()


def _seed(Session) -> tuple[str, str]:
    db = Session()
    artisan = Artisan(phone="+911234500010", verified=True,
                      maker_story_text_en="I make pots.", maker_story_text_hi="मैं मटके बनाती हूँ।")
    db.add(artisan)
    db.commit()
    # image_path points at the Mac's disk, which the Vercel app doesn't have:
    # the page must use the photo stored in the database instead.
    listing = Listing(artisan_id=artisan.id, category="clay pottery", material="clay",
                      size_class="medium", title_en="Blue clay matki", title_hi="नीली मटकी",
                      description_en="d", description_hi="d", price_inr=450,
                      image_path="/not/on/this/machine.jpg")
    db.add(listing)
    db.commit()
    db.add(ListingPhoto(listing_id=listing.id, kind="enhanced", data=b"\xff\xd8\xff not really a jpeg",
                        texture_data=b"\xff\xd8\xff a close-up"))
    db.commit()
    ids = artisan.id, listing.id
    db.close()
    return ids


def test_buyer_pages_render_and_count_opens(client):
    c, Session = client
    artisan_id, listing_id = _seed(Session)

    shop = c.get(f"/s/{artisan_id}")
    assert shop.status_code == 200
    assert "Blue clay matki" in shop.text and f"/media/listing/{listing_id}" in shop.text
    assert f"testserver/s/{artisan_id}" in shop.text  # the host the buyer actually reached

    page = c.get(f"/l/{listing_id}")
    assert page.status_code == 200 and "नीली मटकी" in page.text
    assert f"/media/listing/{listing_id}/texture" in page.text
    closeup = c.get(f"/media/listing/{listing_id}/texture")
    assert closeup.status_code == 200 and closeup.content == b"\xff\xd8\xff a close-up"

    photo = c.get(f"/media/listing/{listing_id}")
    assert photo.status_code == 200 and photo.content.startswith(b"\xff\xd8")
    assert photo.headers["content-type"] == "image/jpeg"

    db = Session()
    assert db.get(Listing, listing_id).view_count == 1
    assert db.get(Artisan, artisan_id).storefront_views == 1
    db.close()

    assert c.get("/").status_code == 200
    assert c.get("/s/nope").status_code == 404
    assert c.get("/media/listing/nope").status_code == 404


def test_buyer_actions_work(client):
    c, Session = client
    artisan_id, listing_id = _seed(Session)
    r = c.post("/api/offers", json={"listing_id": listing_id, "buyer_name": "Asha",
                                    "buyer_contact": "asha@x.com", "price_inr": 450, "quantity": 1})
    assert r.json()["status"] == "submitted"
    r = c.post("/api/storefront/follow", json={"artisan_id": artisan_id, "email": "Asha@X.com"})
    assert r.json()["status"] == "following"
    r = c.post("/api/issues", json={"listing_id": listing_id, "description": "arrived cracked"})
    assert r.json()["status"] == "logged"


@pytest.mark.parametrize("method, path", [
    ("get", "/api/offers?artisan_id=x"),
    ("post", "/api/offers/1/accept"),
    ("post", "/api/offers/1/decline"),
    ("get", "/api/storefront/x/dashboard"),
    ("get", "/api/storefront/x/digest_preview"),
    ("post", "/api/storefront/maker_story"),
    ("post", "/api/listings"),
    ("get", "/api/listings/x/export/amazon"),
    ("post", "/api/onboarding/send_otp"),
    ("post", "/api/sync"),
    ("get", "/docs"),
    ("get", "/openapi.json"),
])
def test_artisan_side_is_not_deployed(client, method, path):
    c, _ = client
    assert getattr(c, method)(path).status_code in (404, 405)
