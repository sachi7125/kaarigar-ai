"""Listing CRUD + publish. Permanent public listing page (Day 5).

Creating a listing IS publishing it here — there's no separate server-side
"draft" state, because the Day-3 on-device SQLite draft already covers "not
published yet". Publishing requires a **verified** artisan (deferred
verification, `onboarding.py`): she can capture, record, and see a price
estimate all the way through unverified; this is the one place that checks
`Artisan.verified`.

The listing's photo/audio are looked up by `client_id` from what `/api/sync`
(Day 3) already saved to `data/uploads/` — no third upload of the same files.
"""
from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path

import qrcode
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from openpyxl import Workbook
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import cfg_get
from app.db.models import Artisan, Listing
from app.db.session import get_db
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


@router.post("/listings")
def publish_listing(req: PublishRequest, db: Session = Depends(get_db)):
    artisan = db.query(Artisan).filter(Artisan.id == req.artisan_id).first()
    if artisan is None:
        raise HTTPException(status_code=404, detail="unknown artisan")
    if not artisan.verified:
        raise HTTPException(status_code=403,
                            detail="artisan not verified — publishing is blocked until phone verification")
    if req.stock_type not in ("unique", "batch"):
        raise HTTPException(status_code=400, detail="stock_type must be 'unique' or 'batch'")

    total = 1 if req.stock_type == "unique" else max(1, req.total_count)
    listing = Listing(
        artisan_id=artisan.id,
        category=req.category, material=req.material, size_class=req.size_class,
        title_en=req.title_en, title_hi=req.title_hi,
        description_en=req.description_en, description_hi=req.description_hi,
        image_path=_find_upload(req.client_id, "image"),
        audio_path=_find_upload(req.client_id, "audio"),
        price_inr=req.price_inr, band_low_inr=req.band_low_inr, band_high_inr=req.band_high_inr,
        stock_type=req.stock_type, total_count=total, remaining_count=total,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)

    url_base = cfg_get("listings.url_base", "https://kaarigar.in")
    return {"listing_id": listing.id, "url": f"{url_base}/l/{listing.id}"}


@router.post("/listings/rename_by_voice")
async def rename_by_voice(audio: UploadFile = File(...), lang: str = Form("hi")):
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
def rename_listing(listing_id: str, req: RenameRequest, db: Session = Depends(get_db)):
    """Post-publish rename — same two fields PublishRequest already carries,
    just editable afterwards too. No ownership check beyond the listing
    existing (matches the rest of this prototype's auth model — see D-onboarding:
    deferred verification, no session tokens)."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
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
        "artisan_verified": listing.artisan.verified,
    }


@router.get("/listings")
def list_artisan_listings(artisan_id: str, db: Session = Depends(get_db)):
    """For the mobile Home screen: this artisan's own published listings."""
    listings = db.query(Listing).filter(Listing.artisan_id == artisan_id).all()
    return [
        {"id": l.id, "title_en": l.title_en, "price_inr": l.price_inr,
         "remaining_count": l.remaining_count, "total_count": l.total_count, "status": l.status}
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
    placeholder = Image.new("RGB", (W, photo_h), "#E5E7EB")
    card.paste(placeholder, (0, 0))
    if listing.image_path and Path(listing.image_path).exists():
        photo = Image.open(listing.image_path).convert("RGB")
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
    url_base = cfg_get("listings.url_base", "https://kaarigar.in")

    text_y = photo_h + 40
    draw.text((40, text_y), listing.title_en, fill="#1F2937", font=title_font)
    if hi_font is not None:
        draw.text((40, text_y + 56), listing.title_hi, fill="#6B7280", font=hi_font)
    draw.text((40, photo_h + 150), f"Rs. {round(listing.price_inr)}", fill="#4F46E5", font=price_font)

    qr_img = qrcode.make(f"{url_base}/l/{listing.id}")
    qr_img = qr_img.resize((180, 180))
    card.paste(qr_img, (W - 220, photo_h + 70))
    # Storefront address under the per-listing QR (roadmap: "Share card keeps a
    # per-listing QR + storefront address underneath") — so a forwarded card
    # still leads somewhere once this one listing sells out. Right-aligned to
    # the QR's own right edge; the id length varies, so measure rather than
    # assume a fixed x (a fixed one ran off the card).
    shop_url = f"{url_base}/s/{listing.artisan_id}".replace("https://", "").replace("http://", "")
    url_w = draw.textlength(shop_url, font=small_font)
    draw.text((W - 40 - url_w, photo_h + 262), shop_url, fill="#9CA3AF", font=small_font)

    buf = io.BytesIO()
    card.save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")


@router.get("/listings/{listing_id}/export_bundle")
def export_bundle(listing_id: str, db: Session = Depends(get_db)):
    """Structured catalog data for GeM/ONDC/Amazon Karigar/ODOP-style onboarding
    (decision D1) — a downloadable spreadsheet an artisan or an NGO facilitator
    can hand to whichever of those programs she's pursuing, since none of them
    expose a self-serve API a hackathon prototype could integrate live (they
    need an already-KYC'd, approved seller account). This is a data HANDOFF,
    not a live marketplace listing — see D1 and the session's own discussion
    of why "just sell on Amazon" isn't buildable here.

    Fields left genuinely uncollected by this prototype (GST number, HSN
    code, bank account) are marked "not collected" rather than left blank
    with no explanation, so the sheet is honest about what still needs
    filling in by hand."""
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="listing not found")
    artisan = listing.artisan
    url_base = cfg_get("listings.url_base", "https://kaarigar.in")

    wb = Workbook()
    ws = wb.active
    ws.title = "Catalog"
    headers = [
        "Listing ID", "Title (EN)", "Title (HI)", "Description (EN)", "Description (HI)",
        "Category", "Material", "Size", "Price (INR)", "Stock type", "Available quantity",
        "Product image URL", "Listing page URL", "Artisan ID", "Artisan phone verified",
        "GSTIN", "HSN code", "Bank account for payout",
    ]
    ws.append(headers)
    image_url = f"{url_base}/media/{Path(listing.image_path).name}" if listing.image_path else "not collected"
    ws.append([
        listing.id, listing.title_en, listing.title_hi,
        listing.description_en, listing.description_hi,
        listing.category, listing.material, listing.size_class,
        listing.price_inr, listing.stock_type, listing.remaining_count,
        image_url, f"{url_base}/l/{listing.id}",
        artisan.id, "yes" if artisan.verified else "no",
        "not collected — this prototype does not capture GST registration",
        "not collected — assign per marketplace's own category taxonomy",
        "not collected — no payment/payout flow in this prototype (out of scope, decisions.md)",
    ])
    for col in ws.columns:
        width = max(len(str(c.value)) for c in col if c.value is not None)
        ws.column_dimensions[col[0].column_letter].width = min(max(width + 2, 12), 60)

    buf = io.BytesIO()
    wb.save(buf)
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="kaarigar_export_{listing.id}.xlsx"'},
    )
