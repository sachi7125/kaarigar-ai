"""Server-rendered public pages: single listing (Day 5) and per-artisan
storefront + unsubscribe confirmation (Day 6).

Both listing and storefront URLs are permanent: `{listings.url_base}/l/{id}`
and `{listings.url_base}/s/{artisan_id}` — the id format itself is frozen in
`db/models.generate_short_id` (watchlist). The stall QR poster (Day 6) points
at the storefront URL, not a single listing (decision D5).

The "only screen where reading is assumed" (wireframe) — buyers are boutique
owners, exporters, procurement staff, so this is plain and ordinary on
purpose, no low-literacy accommodations needed here.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.db.models import Artisan, Follower, Listing
from app.db.session import get_db

router = APIRouter()
_templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@router.get("/l/{listing_id}", response_class=HTMLResponse)
def view_listing(listing_id: str, request: Request, db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
        return HTMLResponse("<h1>Listing not found</h1>", status_code=404)
    # Starlette 0.29+ wants `request` as its own positional argument, not a
    # "request" key inside the context dict (the older calling convention
    # raises a confusing "unhashable type: dict" from deep in Jinja2's cache).
    return _templates.TemplateResponse(request, "listing.html", {"listing": listing})


@router.get("/s/{artisan_id}", response_class=HTMLResponse)
def view_storefront(artisan_id: str, request: Request, db: Session = Depends(get_db)):
    artisan = db.query(Artisan).filter(Artisan.id == artisan_id).first()
    if artisan is None:
        return HTMLResponse("<h1>Storefront not found</h1>", status_code=404)
    listings = (
        db.query(Listing).filter(Listing.artisan_id == artisan_id)
        .order_by(Listing.created_at.desc()).all()
    )
    return _templates.TemplateResponse(
        request, "storefront.html", {"artisan": artisan, "listings": listings})


@router.get("/unsubscribe/{token}", response_class=HTMLResponse)
def unsubscribe(token: str, db: Session = Depends(get_db)):
    """One-click unsubscribe (roadmap: "one-click unsubscribe") — a plain GET
    so it works from any email client with no JS and no login. The token is
    unguessable (secrets.token_urlsafe(24) — models.Follower), so this can't
    be used to unsubscribe someone else's email."""
    follower = db.query(Follower).filter(Follower.unsubscribe_token == token).first()
    if follower is None:
        return HTMLResponse(
            "<!doctype html><meta charset='utf-8'><meta name='color-scheme' content='light'>"
            "<style>:root{color-scheme:light}</style>"
            "<body style='font-family:-apple-system,sans-serif;background:#F9FAFB;color:#1F2937'>"
            "<h1>This link has already been used or is invalid.</h1></body>",
            status_code=404,
        )
    db.delete(follower)
    db.commit()
    return HTMLResponse(
        "<!doctype html><meta charset='utf-8'><meta name='color-scheme' content='light'>"
        "<style>:root{color-scheme:light}</style>"
        "<body style='font-family:-apple-system,sans-serif;max-width:480px;margin:80px auto;"
        "text-align:center;color:#1F2937;background:#F9FAFB'>"
        "<h2>You've been unsubscribed.</h2>"
        "<p style='color:#6B7280'>You won't get any more emails from this maker.</p>"
        "</body>"
    )
