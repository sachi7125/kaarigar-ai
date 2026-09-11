"""Listing CRUD + publish. Permanent public listing page (Day 5).

Creating a listing IS publishing it here — there's no separate server-side
"draft" state, because the Day-3 on-device SQLite draft already covers "not
published yet". Publishing requires a **verified** artisan (deferred
verification, `onboarding.py`): she can capture, record, and see a price
estimate all the way through unverified; this is the one place that checks
`Artisan.verified`.

The listing's photo/audio are looked up by `client_id` from what `/api/sync`
(Day 3) already saved to `data/uploads/` — no third upload of the same files.

Day 7: publishing and renaming need her device token (app/auth.py). At
publish the photo is also copied, downscaled, into the database
(app/services/photos.py), so buyer pages can show it wherever the database
lives — including the Vercel deployment, which has no disk. The single
generic export bundle is replaced by one export per marketplace
(app/services/marketplace_export.py), built only when she taps it.
"""
from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path

import qrcode
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import ensure_owner, require_artisan
from app.config import PUBLIC_URL
from app.db.models import Artisan, Listing
from app.db.session import get_db
from app.services.marketplace_export import UnknownMarketplace, available_marketplaces, build_export
from app.services.photos import listing_photo_bytes, listing_texture_bytes, store_listing_photo
from pipelines.voice.transcribe import transcribe
from pipelines.voice.glossary import correct as glossary_correct
from pipelines.voice.pii_strip import strip_pii
from pipelines.voice.describe import describe

router = APIRouter()

_UPLOADS_DIR = Path("data/uploads")

# Common Devanagari-capable font paths, checked in order — macOS ships one,
# most Linux boxes with Noto installed have the other. Share cards degrade to
# English-only text (never a crash, never tofu boxes) if neither exists;
# see share_card()'s docstring.
_DEVANAGARI_FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Devanagari Sangam MN.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
]


def _find_upload(client_id: str, kind: str) -> str | None:
    matches = sorted(_UPLOADS_DIR.glob(f"{client_id}_{kind}_*"))
    return str(matches[0]) if matches else None


def _save_upload_tmp(f: UploadFile, suffix: str) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as out:
        out.write(f.file.read())
    return path


class PublishRequest(BaseModel):
    artisan_id: str
    client_id: str
    category: str
    material: str
    size_class: str
    title_en: str
    title_hi: str
    description_en: str
    description_hi: str
    price_inr: float
    band_low_inr: float | None = None
    band_high_inr: float | None = None
    stock_type: str = "unique"   # "unique" | "batch"
    total_count: int = 1
    # Day 7: for a batch, whether price_inr is for each piece or for all
    # total_count pieces together (sold as one lot).
    price_unit: str = "piece"    # "piece" | "set"


@router.post("/listings")
def publish_listing(req: PublishRequest, db: Session = Depends(get_db),
                    me: Artisan = Depends(require_artisan)):
    ensure_owner(me, req.artisan_id)
    if not me.verified:
        raise HTTPException(status_code=403,
                            detail="artisan not verified — publishing is blocked until phone verification")
    if req.stock_type not in ("unique", "batch"):
        raise HTTPException(status_code=400, detail="stock_type must be 'unique' or 'batch'")
    if req.price_unit not in ("piece", "set"):
        raise HTTPException(status_code=400, detail="price_unit must be 'piece' or 'set'")

    count = max(1, req.total_count)
    if req.price_unit == "set":
        # The whole batch at one price: one lot of `count` pieces.
        stock_type, pack_size, total = "unique", count, 1
    else:
        stock_type, pack_size = req.stock_type, 1
        total = 1 if stock_type == "unique" else count

    image_path = _find_upload(req.client_id, "image")
    listing = Listing(
        artisan_id=me.id,
        category=req.category, material=req.material, size_class=req.size_class,
        title_en=req.title_en, title_hi=req.title_hi,
        description_en=req.description_en, description_hi=req.description_hi,
        image_path=image_path,
        audio_path=_find_upload(req.client_id, "audio"),
        price_inr=req.price_inr, band_low_inr=req.band_low_inr, band_high_inr=req.band_high_inr,
        stock_type=stock_type, total_count=total, remaining_count=total,
        price_unit=req.price_unit, pack_size=pack_size,
    )
    db.add(listing)
    db.flush()  # assigns listing.id
    if image_path:
        store_listing_photo(db, listing.id, image_path)
    db.commit()
    db.refresh(listing)

    return {"listing_id": listing.id, "url": f"{PUBLIC_URL}/l/{listing.id}"}


@router.post("/listings/rename_by_voice")
async def rename_by_voice(audio: UploadFile = File(...), lang: str = Form("hi"),
                          _me: Artisan = Depends(require_artisan)):
    """A short voice note -> a bilingual title, for renaming a listing either
    before or after publish (raised by the user: 'allow user to edit name of
    the listing before listing and also after'). Reuses `describe()` — the
    same Day-2 pipeline a full listing description already goes through —
    and returns only its title_en/title_hi, discarding the rest; this stays a
    stateless suggestion, same as pricing/attributes.py's pattern, so it never
    writes anything itself. The caller (mobile) either holds the result
    locally (pre-publish) or sends it to PATCH /listings/{id} (post-publish)."""
    audio_path = _save_upload_tmp(audio, ".m4a")
    try:
        t = transcribe(audio_path, lang=lang)
        g = glossary_correct(t.text or "")
        p = strip_pii(g.text)
        d = describe(p.text, lang=lang)
        return {"title_en": d.title_en, "title_hi": d.title_hi, "transcript": p.text}
    finally:
        os.unlink(audio_path)


class RenameRequest(BaseModel):
    title_en: str
    title_hi: str


@router.patch("/listings/{listing_id}")
def rename_listing(listing_id: str, req: RenameRequest, db: Session = Depends(get_db),
                   me: Artisan = Depends(require_artisan)):
    """Post-publish rename — same two fields PublishRequest already carries,
    just editable afterwards too. Only on her own listings (Day 7)."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None or listing.artisan_id != me.id:
        raise HTTPException(status_code=404, detail="listing not found")
    title_en = req.title_en.strip()
    title_hi = req.title_hi.strip()
    if not title_en or not title_hi:
        raise HTTPException(status_code=400, detail="title cannot be empty")
    listing.title_en = title_en
    listing.title_hi = title_hi
    db.commit()
    return {"id": listing.id, "title_en": listing.title_en, "title_hi": listing.title_hi}


@router.get("/listings/{listing_id}")
def get_listing(listing_id: str, db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="listing not found")
    return {
        "id": listing.id, "category": listing.category, "material": listing.material,
        "size_class": listing.size_class,
        "title_en": listing.title_en, "title_hi": listing.title_hi,
        "description_en": listing.description_en, "description_hi": listing.description_hi,
        "price_inr": listing.price_inr,
        "band_low_inr": listing.band_low_inr, "band_high_inr": listing.band_high_inr,
        "stock_type": listing.stock_type, "total_count": listing.total_count,
        "remaining_count": listing.remaining_count, "status": listing.status,
        "price_unit": listing.price_unit, "pack_size": listing.pack_size,
        "artisan_verified": listing.artisan.verified,
    }


@router.get("/listings")
def list_artisan_listings(artisan_id: str, db: Session = Depends(get_db)):
    """For the mobile Home screen: this artisan's own published listings."""
    listings = db.query(Listing).filter(Listing.artisan_id == artisan_id).all()
    return [
        {"id": l.id, "title_en": l.title_en, "price_inr": l.price_inr,
         "remaining_count": l.remaining_count, "total_count": l.total_count, "status": l.status,
         "price_unit": l.price_unit, "pack_size": l.pack_size}
        for l in listings
    ]


def _devanagari_font(size: int) -> ImageFont.FreeTypeFont | None:
    for path in _DEVANAGARI_FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return None


@router.get("/listings/{listing_id}/share_card")
def share_card(listing_id: str, db: Session = Depends(get_db)):
    """One shareable image — "forwarded on WhatsApp" (roadmap) — combining the
    listing photo, price, and a QR code to the listing page. Text is English
    (title_en) plus, only if a Devanagari-capable font is available on this
    host, the Hindi title too — degrades gracefully rather than showing tofu
    boxes or crashing on a host without one (see _DEVANAGARI_FONT_CANDIDATES)."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="listing not found")

    W, H = 1080, 1080
    card = Image.new("RGB", (W, H), "#F3F4F6")

    photo_h = 780
    stored = listing_photo_bytes(db, listing)
    texture = listing_texture_bytes(db, listing)
    closeup_caption_at = None
    if stored is not None and texture is not None:
        # The enhanced pair (Day 7; the same two views scripts/try_photo.py
        # shows): the product cut out on white filling the left of the band,
        # and its surface close-up on the right. Both are square by
        # construction (pipelines.image.enhance crops them so).
        card.paste(Image.new("RGB", (W, photo_h), "white"), (0, 0))
        main = Image.open(io.BytesIO(stored[0])).convert("RGB").resize((photo_h - 20, photo_h - 20))
        card.paste(main, (10, 10))
        side = W - photo_h - 20
        close_y = (photo_h - side) // 2 - 20
        closeup = Image.open(io.BytesIO(texture)).convert("RGB").resize((side, side))
        card.paste(closeup, (photo_h + 10, close_y))
        closeup_caption_at = (photo_h + 10, close_y + side + 12)
    else:
        card.paste(Image.new("RGB", (W, photo_h), "#E5E7EB"), (0, 0))
    if stored is not None and texture is None:
        photo = Image.open(io.BytesIO(stored[0])).convert("RGB")
        # Contain-fit, not cover-fit: a real phone photo is usually portrait
        # (taller than wide) while this band is landscape-shaped, so a
        # center-crop-to-fill was cutting off the top/bottom of the actual
        # product (found live: a sandal's strap was cropped out). Scaling to
        # fit entirely inside the band, centered on the placeholder colour,
        # never loses part of the photo — the trade-off is a plain-colour
        # margin on one axis instead, which is the honest option here.
        scale = min(W / photo.width, photo_h / photo.height)
        new_w, new_h = int(photo.width * scale), int(photo.height * scale)
        photo = photo.resize((new_w, new_h))
        card.paste(photo, ((W - new_w) // 2, (photo_h - new_h) // 2))

    draw = ImageDraw.Draw(card)
    title_font = ImageFont.load_default(size=44)
    price_font = ImageFont.load_default(size=64)
    small_font = ImageFont.load_default(size=24)
    hi_font = _devanagari_font(38)
    if closeup_caption_at is not None:
        draw.text(closeup_caption_at, "Close-up", fill="#6B7280", font=small_font)

    text_y = photo_h + 40
    draw.text((40, text_y), listing.title_en, fill="#1F2937", font=title_font)
    if hi_font is not None:
        draw.text((40, text_y + 56), listing.title_hi, fill="#6B7280", font=hi_font)
    price_text = f"Rs. {round(listing.price_inr)}"
    draw.text((40, photo_h + 150), price_text, fill="#4F46E5", font=price_font)
    if listing.price_unit == "set":
        suffix_x = 40 + draw.textlength(price_text, font=price_font) + 16
        draw.text((suffix_x, photo_h + 172), f"for a set of {listing.pack_size}",
                  fill="#6B7280", font=small_font)

    qr_img = qrcode.make(f"{PUBLIC_URL}/l/{listing.id}")
    qr_img = qr_img.resize((180, 180))
    card.paste(qr_img, (W - 220, photo_h + 70))
    # Storefront address under the per-listing QR (roadmap: "Share card keeps a
    # per-listing QR + storefront address underneath") — so a forwarded card
    # still leads somewhere once this one listing sells out. Right-aligned to
    # the QR's own right edge; the id length varies, so measure rather than
    # assume a fixed x (a fixed one ran off the card).
    shop_url = f"{PUBLIC_URL}/s/{listing.artisan_id}".replace("https://", "").replace("http://", "")
    url_w = draw.textlength(shop_url, font=small_font)
    draw.text((W - 40 - url_w, photo_h + 262), shop_url, fill="#9CA3AF", font=small_font)

    buf = io.BytesIO()
    card.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")


@router.get("/exports/marketplaces")
def export_marketplaces():
    """The marketplaces she can export a listing for, from the profile files."""
    return available_marketplaces()


@router.get("/listings/{listing_id}/export/{marketplace}")
def export_listing(listing_id: str, marketplace: str, db: Session = Depends(get_db)):
    """One listing in one marketplace's format, built in memory when she taps
    it and streamed back — never generated ahead of time or kept on the server
    (raised by the user: "only create when user clicks"). Only public listing
    data goes in, so like the listing page itself it needs no sign-in."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="listing not found")
    try:
        body, media_type, filename = build_export(listing, marketplace)
    except UnknownMarketplace:
        raise HTTPException(status_code=404, detail=f"no export format for {marketplace!r}")
    return Response(
        content=body, media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"',
                 "Cache-Control": "no-store"},
    )
