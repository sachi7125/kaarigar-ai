"""Asking-price tolerance + quantity checks. (Day 5)

Three independent reasons an offer gets auto-declined, per config.yaml's
`offers` section: below the asking-price tolerance, more than what's left in
stock, or too many offers from the same contact in an hour (anti lowball-
flooding). An auto-declined offer is still stored (status="auto_declined") but
never shown to the artisan — she only sees that the shield worked (the count),
matching the wireframe's "3 offers auto-declined — you were not shown them."
"""
from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from app.config import cfg_get
from app.db.models import Listing, Offer


def validate_offer(db: Session, listing: Listing, price_inr: float, quantity: int,
                   buyer_contact: str) -> tuple[bool, str]:
    if quantity <= 0:
        return False, "invalid quantity"
    if quantity > listing.remaining_count:
        return False, "quantity exceeds remaining stock"

    tolerance = float(cfg_get("offers.asking_price_tolerance_frac", 0.05))
    floor_price = listing.price_inr * (1 - tolerance)
    if price_inr < floor_price:
        return False, "below asking price"

    limit = int(cfg_get("offers.rate_limit_per_phone_per_hour", 5))
    since = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    recent = (
        db.query(Offer)
        .filter(Offer.buyer_contact == buyer_contact, Offer.created_at >= since)
        .count()
    )
    if recent >= limit:
        return False, "rate limited"

    return True, ""
