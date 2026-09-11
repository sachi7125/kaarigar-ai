"""The no-offers-for-a-week nudge (Day 7; roadmap: "no offers for a week →
reasoned nudge").

"Reasoned" means every line is read off her own data: page opens, offers the
price shield turned away, her price against the suggested band, missing
photos, a missing maker story. Nothing generic like "try harder", and no
guess about why buyers stayed away beyond what the numbers show.

Page-open counts start from Day 7, when counting was added.
"""
from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from app.db.models import Artisan, Listing, Offer
from app.services.photos import ids_with_photos

QUIET_DAYS = 7
_MAX_TITLE = 40


def _reason(code: str, text_hi: str, text_en: str) -> dict:
    return {"code": code, "text_hi": text_hi, "text_en": text_en}


def _short(title: str) -> str:
    title = (title or "").strip()
    return title if len(title) <= _MAX_TITLE else title[:_MAX_TITLE - 1] + "…"


def no_offers_nudge(db: Session, artisan: Artisan, now: datetime.datetime | None = None) -> dict | None:
    """None unless she has had a listing up for a full week and no offer has
    reached her in that week. Otherwise the reasons, most useful first."""
    now = now or datetime.datetime.utcnow()
    since = now - datetime.timedelta(days=QUIET_DAYS)

    all_listings = db.query(Listing).filter(Listing.artisan_id == artisan.id).all()
    live = [l for l in all_listings if l.status == "published"]
    if not live or min(l.created_at for l in live) > since:
        return None

    recent = (db.query(Offer)
              .filter(Offer.listing_id.in_([l.id for l in all_listings]), Offer.created_at >= since)
              .all())
    if any(o.status != "auto_declined" for o in recent):
        return None

    reasons: list[dict] = []
    if recent:
        best = round(max(o.price_inr for o in recent))
        reasons.append(_reason(
            "auto_declined",
            f"{len(recent)} ऑफ़र आए, पर आपकी कीमत से कम थे या स्टॉक से ज़्यादा माँग रहे थे, "
            f"इसलिए अपने-आप मना हो गए। सबसे ऊँचा ऑफ़र ₹{best} का था।",
            f"{len(recent)} offers came in but were below your price or asked for more than "
            f"your stock, so they were declined automatically. The highest was ₹{best}.",
        ))

    views = sum(l.view_count or 0 for l in live) + (artisan.storefront_views or 0)
    if views == 0:
        reasons.append(_reason(
            "no_views",
            "अभी तक किसी ने आपकी दुकान या लिस्टिंग का पेज नहीं खोला। अपना QR और दुकान का लिंक शेयर कीजिए।",
            "Nobody has opened your shop or listing pages yet. Share your QR code and shop link.",
        ))
    elif not recent:
        reasons.append(_reason(
            "views_no_offers",
            f"आपके पेज {views} बार खोले गए, पर ऑफ़र नहीं आया।",
            f"Your pages were opened {views} times, but no offer came.",
        ))

    above = [l for l in live if l.band_high_inr and l.price_unit != "set" and l.price_inr > l.band_high_inr]
    if above:
        l = above[0]
        low, high = round(l.band_low_inr or 0), round(l.band_high_inr)
        reasons.append(_reason(
            "above_band",
            f"'{_short(l.title_hi)}' की कीमत ₹{round(l.price_inr)} है, सुझाई गई सीमा ₹{low}–₹{high} से ज़्यादा।",
            f"'{_short(l.title_en)}' is priced at ₹{round(l.price_inr)}, above the suggested ₹{low}–₹{high}.",
        ))

    no_photo = len(live) - len(ids_with_photos(db, live))
    if no_photo:
        reasons.append(_reason(
            "no_photo",
            f"{no_photo} लिस्टिंग में फ़ोटो नहीं है।",
            f"{no_photo} listing{'s' if no_photo > 1 else ''} without a photo.",
        ))

    if not artisan.maker_story_text_hi:
        reasons.append(_reason(
            "no_story",
            "आपकी दुकान पर अभी आपकी कहानी नहीं है। एक छोटा वॉइस नोट रिकॉर्ड कर सकती हैं।",
            "Your shop doesn't show your story yet. You can record a short voice note.",
        ))

    heading_hi = f"पिछले {QUIET_DAYS} दिनों में आप तक कोई ऑफ़र नहीं पहुँचा।"
    return {
        "quiet_days": QUIET_DAYS,
        "heading_hi": heading_hi,
        "heading_en": f"No offer has reached you in the last {QUIET_DAYS} days.",
        "reasons": reasons,
        "spoken_hi": " ".join([heading_hi, *(r["text_hi"] for r in reasons)]),
    }
