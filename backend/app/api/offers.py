"""Offer inbox: structured offer, asking-price auto-decline, quantity vs stock,
voice accept/decline, report-an-issue. (Day 5)

Buyer contact is deliberately withheld from `GET /offers` (the artisan-facing
pending list) and only returned by `POST /offers/{id}/accept` — "contact
details are exchanged only after the artisan accepts" (wireframe screen 6).
Auto-declined offers are stored (for the count) but never appear in the
pending list — she sees that the shield worked, not the offers themselves.

Day 7: listing, accepting and declining offers need her device token
(app/auth.py), and only work on offers for her own listings. Submitting an
offer and reporting an issue stay open to any buyer; those two are also what
the public Vercel app serves (app/public_main.py).
"""
from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import ensure_owner, require_artisan
from app.config import cfg_get
from app.db.models import Artisan, Listing, Offer, IssueReport
from app.db.session import get_db
from app.services.offer_validation import validate_offer
from app.services.stock import accept_offer_and_decrement

router = APIRouter()


class OfferRequest(BaseModel):
    listing_id: str
    buyer_name: str
    buyer_contact: str
    price_inr: float
    quantity: int = 1
    message: str | None = None


@router.post("/offers")
def submit_offer(req: OfferRequest, db: Session = Depends(get_db)):
    listing = db.query(Listing).filter(Listing.id == req.listing_id).first()
    if listing is None:
        raise HTTPException(status_code=404, detail="listing not found")
    if listing.status == "sold_out":
        raise HTTPException(status_code=409, detail="listing is sold out")

    ok, reason = validate_offer(db, listing, req.price_inr, req.quantity, req.buyer_contact)
    expiry_hours = int(cfg_get("offers.expiry_hours", 48))

    # Returning-buyer flag (Day 6, config: storefront.returning_buyer_flag):
    # has this contact ever had an offer ACCEPTED by this same artisan before,
    # on any listing? Computed once here, not a live join later, so it can't
    # silently change after the offer exists.
    artisan_listing_ids = [
        l.id for l in db.query(Listing).filter(Listing.artisan_id == listing.artisan_id).all()
    ]
    is_returning = db.query(Offer).filter(
        Offer.listing_id.in_(artisan_listing_ids),
        Offer.buyer_contact == req.buyer_contact,
        Offer.status == "accepted",
    ).first() is not None

    offer = Offer(
        listing_id=listing.id, buyer_name=req.buyer_name, buyer_contact=req.buyer_contact,
        price_inr=req.price_inr, quantity=req.quantity, message=req.message,
        status="pending" if ok else "auto_declined",
        decline_reason=None if ok else reason,
        is_returning_buyer=is_returning,
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(hours=expiry_hours),
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)

    if not ok:
        # Same message regardless of *why* — a buyer probing the tolerance
        # shouldn't learn the exact threshold from the error text.
        return {"status": "declined",
               "message": "This offer was below the asking price or exceeded available stock."}
    return {"status": "submitted", "offer_id": offer.id}


@router.get("/offers")
def list_offers_for_artisan(
    artisan_id: str | None = None,
    db: Session = Depends(get_db),
    me: Artisan = Depends(require_artisan),
):
    if artisan_id is not None:
        ensure_owner(me, artisan_id)
    listings = db.query(Listing).filter(Listing.artisan_id == me.id).all()
    listing_ids = [l.id for l in listings]
    by_listing = {l.id: l for l in listings}
    offers = (
        db.query(Offer)
        .filter(Offer.listing_id.in_(listing_ids), Offer.status == "pending")
        .order_by(Offer.created_at.desc())
        .all()
    )
    return [
        {
            "id": o.id, "listing_id": o.listing_id,
            "listing_title": by_listing[o.listing_id].title_en,
            "price_inr": o.price_inr, "quantity": o.quantity,
            "is_returning_buyer": o.is_returning_buyer,
            "created_at": o.created_at.isoformat(),
        }
        for o in offers
    ]


def _own_offer(db: Session, offer_id: int, me: Artisan) -> Offer:
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    # Someone else's offer answers exactly like a missing one, so offer ids
    # can't be probed.
    if offer is None or offer.listing.artisan_id != me.id:
        raise HTTPException(status_code=404, detail="offer not found")
    return offer


@router.post("/offers/{offer_id}/accept")
def accept_offer(offer_id: int, db: Session = Depends(get_db), me: Artisan = Depends(require_artisan)):
    offer = _own_offer(db, offer_id, me)
    if offer.status != "pending":
        raise HTTPException(status_code=409, detail=f"offer is already {offer.status}")

    ok = accept_offer_and_decrement(db, offer.listing_id, offer.quantity)
    if not ok:
        # Someone else's offer already consumed the remaining stock — the
        # double-accept case. Never silently double-decrement.
        offer.status = "declined"
        offer.decline_reason = "sold out before this offer was accepted"
        db.commit()
        raise HTTPException(status_code=409,
                            detail="not enough stock remaining — this offer could not be accepted")

    offer.status = "accepted"
    db.commit()
    db.refresh(offer)
    return {"status": "accepted", "buyer_contact": offer.buyer_contact, "buyer_name": offer.buyer_name}


@router.post("/offers/{offer_id}/decline")
def decline_offer(offer_id: int, db: Session = Depends(get_db), me: Artisan = Depends(require_artisan)):
    offer = _own_offer(db, offer_id, me)
    if offer.status != "pending":
        raise HTTPException(status_code=409, detail=f"offer is already {offer.status}")
    offer.status = "declined"
    offer.decline_reason = "declined by artisan"
    db.commit()
    return {"status": "declined"}


class IssueRequest(BaseModel):
    listing_id: str | None = None
    reporter_contact: str | None = None
    description: str


@router.post("/issues")
def report_issue(req: IssueRequest, db: Session = Depends(get_db)):
    """Logs only — no adjudication, refund, or delist (decision D6)."""
    issue = IssueReport(listing_id=req.listing_id, reporter_contact=req.reporter_contact,
                        description=req.description)
    db.add(issue)
    db.commit()
    return {"status": "logged", "id": issue.id}
