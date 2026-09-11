"""Per-artisan storefront + follow (email digest) + returning-buyer flag + stall
QR + dashboard aggregates. (Day 6)

Five stateless endpoints, same style as pricing.py/listings.py — no server-side
session, each call self-contained:

  - POST /storefront/maker_story — audio -> transcribe -> glossary_correct ->
    strip_pii -> build_maker_story (pipelines.voice.maker_story, reusing the
    Day-2 pipeline as the roadmap specifies) -> saved on the Artisan.
  - GET  /storefront/{artisan_id} — artisan info + maker story + every listing
    (sold-out marked, never hidden — "maker story + every listing" per the
    roadmap) + follower_count. Backs both the mobile app's own preview and the
    public storefront web page (web/storefront_page.py).
  - POST /storefront/follow — email only (config: storefront.follow_digest).
    Actual weekly SMTP send is mocked (no provider budgeted, same disclosed
    shortcut as D18's OTP) but /storefront/{id}/digest_preview assembles the
    real content a send would use, so the data path is genuine even though
    delivery isn't wired up.
  - GET  /storefront/{artisan_id}/qr — a PNG QR code encoding the permanent
    storefront URL, for the stall poster.
  - GET  /storefront/{artisan_id}/dashboard — real aggregates: listing/offer
    counts, total accepted-offer earnings, remaining stock, follower count,
    and (Day 7) the no-offers-for-a-week nudge.

Day 7: maker story, digest preview and dashboard need her device token
(app/auth.py) — earnings are "only in her view". Follow is also served by the
public Vercel app (app/public_main.py), so this module keeps its speech and
QR imports inside the functions that use them.
"""
from __future__ import annotations

import datetime
import io
import os
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.auth import ensure_owner, require_artisan
from app.config import PUBLIC_URL
from app.db.models import Artisan, Follower, Listing, Offer
from app.db.session import get_db
from app.services.nudge import no_offers_nudge

router = APIRouter()


def _save_upload(f: UploadFile, suffix: str) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as out:
        out.write(f.file.read())
    return path


def _storefront_url(artisan_id: str) -> str:
    return f"{PUBLIC_URL}/s/{artisan_id}"


def _one_week_ago() -> datetime.datetime:
    return datetime.datetime.utcnow() - datetime.timedelta(days=7)


@router.post("/storefront/maker_story")
async def record_maker_story(
    artisan_id: str = Form(...),
    audio: UploadFile = File(...),
    lang: str = Form("hi"),
    db: Session = Depends(get_db),
    me: Artisan = Depends(require_artisan),
):
    ensure_owner(me, artisan_id)
    from pipelines.voice.glossary import correct as glossary_correct
    from pipelines.voice.maker_story import build_maker_story
    from pipelines.voice.pii_strip import strip_pii
    from pipelines.voice.transcribe import transcribe

    audio_path = _save_upload(audio, ".m4a")
    try:
        t = transcribe(audio_path, lang=lang)
        g = glossary_correct(t.text or "")
        p = strip_pii(g.text)
        story = build_maker_story(p.text, lang=lang)
    finally:
        os.unlink(audio_path)

    me.maker_story_text_en = story.text_en
    me.maker_story_text_hi = story.text_hi
    db.commit()
    return {"text_en": story.text_en, "text_hi": story.text_hi, "source": story.source}


def _listing_dict(l: Listing) -> dict:
    return {
        "id": l.id, "title_en": l.title_en, "title_hi": l.title_hi,
        "price_inr": l.price_inr, "status": l.status,
        "stock_type": l.stock_type, "total_count": l.total_count,
        "remaining_count": l.remaining_count,
        "price_unit": l.price_unit, "pack_size": l.pack_size,
    }


@router.get("/storefront/{artisan_id}")
def get_storefront(artisan_id: str, db: Session = Depends(get_db)):
    artisan = db.query(Artisan).filter(Artisan.id == artisan_id).first()
    if artisan is None:
        raise HTTPException(status_code=404, detail="unknown artisan")

    listings = (
        db.query(Listing).filter(Listing.artisan_id == artisan_id)
        .order_by(Listing.created_at.desc()).all()
    )
    follower_count = db.query(Follower).filter(Follower.artisan_id == artisan_id).count()

    return {
        "artisan_id": artisan.id,
        "verified": artisan.verified,
        "maker_story_text_en": artisan.maker_story_text_en,
        "maker_story_text_hi": artisan.maker_story_text_hi,
        "has_maker_story": artisan.maker_story_text_hi is not None,
        "follower_count": follower_count,
        "storefront_url": _storefront_url(artisan_id),
        "listings": [_listing_dict(l) for l in listings],
    }


class FollowRequest(BaseModel):
    artisan_id: str
    email: EmailStr


@router.post("/storefront/follow")
def follow_artisan(req: FollowRequest, db: Session = Depends(get_db)):
    artisan = db.query(Artisan).filter(Artisan.id == req.artisan_id).first()
    if artisan is None:
        raise HTTPException(status_code=404, detail="unknown artisan")

    # Emails are case-insensitive in practice — normalise before storing or
    # comparing, so Alice@Example.com and alice@example.com don't create two
    # Follower rows (and two weekly emails, and a half-working unsubscribe).
    email = req.email.strip().lower()

    existing = db.query(Follower).filter(
        Follower.artisan_id == req.artisan_id, Follower.email == email,
    ).first()
    if existing is not None:
        return {"status": "already_following", "unsubscribe_token": existing.unsubscribe_token}

    follower = Follower(artisan_id=req.artisan_id, email=email)
    db.add(follower)
    db.commit()
    db.refresh(follower)
    return {"status": "following", "unsubscribe_token": follower.unsubscribe_token}


@router.get("/storefront/{artisan_id}/digest_preview")
def digest_preview(artisan_id: str, db: Session = Depends(get_db),
                   me: Artisan = Depends(require_artisan)):
    """The content a weekly follower digest email WOULD contain — real data,
    genuinely assembled, even though actual SMTP dispatch is mocked (no
    provider budgeted; same disclosed-shortcut pattern as D18's OTP). Lets a
    demo show "here is what she gets sent" honestly, without claiming email
    delivery that isn't wired up."""
    ensure_owner(me, artisan_id)

    since = _one_week_ago()
    new_listings = (
        db.query(Listing)
        .filter(Listing.artisan_id == artisan_id, Listing.created_at >= since,
                Listing.status == "published")
        .order_by(Listing.created_at.desc()).all()
    )
    follower_count = db.query(Follower).filter(Follower.artisan_id == artisan_id).count()

    return {
        "storefront_url": _storefront_url(artisan_id),
        "recipient_count": follower_count,
        "new_listings": [_listing_dict(l) for l in new_listings],
        "would_send": follower_count > 0 and len(new_listings) > 0,
        "note": "no SMTP provider configured; this is the content a real weekly send would use",
    }


@router.get("/storefront/{artisan_id}/qr")
def storefront_qr(artisan_id: str, db: Session = Depends(get_db)):
    import qrcode

    artisan = db.query(Artisan).filter(Artisan.id == artisan_id).first()
    if artisan is None:
        raise HTTPException(status_code=404, detail="unknown artisan")

    img = qrcode.make(_storefront_url(artisan_id))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")


@router.get("/storefront/{artisan_id}/dashboard")
def storefront_dashboard(artisan_id: str, db: Session = Depends(get_db),
                         me: Artisan = Depends(require_artisan)):
    ensure_owner(me, artisan_id)

    listings = db.query(Listing).filter(Listing.artisan_id == artisan_id).all()
    listing_ids = [l.id for l in listings]
    accepted_offers = (
        db.query(Offer).filter(Offer.listing_id.in_(listing_ids), Offer.status == "accepted").all()
        if listing_ids else []
    )
    pending_offers_count = (
        db.query(Offer).filter(Offer.listing_id.in_(listing_ids), Offer.status == "pending").count()
        if listing_ids else 0
    )
    follower_count = db.query(Follower).filter(Follower.artisan_id == artisan_id).count()

    return {
        "listings_count": len(listings),
        "published_count": sum(1 for l in listings if l.status == "published"),
        "sold_out_count": sum(1 for l in listings if l.status == "sold_out"),
        "pending_offers_count": pending_offers_count,
        "accepted_offers_count": len(accepted_offers),
        "total_earning_inr": sum(o.price_inr * o.quantity for o in accepted_offers),
        "remaining_stock_total": sum(l.remaining_count for l in listings),
        "follower_count": follower_count,
        "nudge": no_offers_nudge(db, me),
    }
