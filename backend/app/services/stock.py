"""Unique-vs-batch stock: locked decrement inside the acceptance transaction,
sold-out state, spoken restock. (Day 5)

`with_for_update()` is a real per-row lock on PostgreSQL (the architecture's
stated target — decision D17) but a no-op on SQLite (today's dev database):
SQLite has no row-level locking, only whole-database write locks. That still
serializes concurrent writers through the same engine/connection pool, which
is what actually prevents a double-accept at this dev/single-process scale —
but it is NOT the same guarantee as Postgres row locks under real concurrent
load (multiple worker processes, connection pooling across machines). Moving
to Postgres (config.DATABASE_URL) turns this into a real guarantee with no
code change here — that is the whole point of writing it this way now.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Listing


def accept_offer_and_decrement(db: Session, listing_id: str, quantity: int) -> bool:
    """Attempt to take `quantity` units off a listing's remaining stock as part
    of accepting one offer. Returns False (nothing written) if there isn't
    enough left — the caller must not mark the offer accepted in that case.
    Never raises for an ordinary "sold out" case; only a missing listing_id is
    a caller error.
    """
    listing = (
        db.query(Listing)
        .filter(Listing.id == listing_id)
        .with_for_update()
        .one()
    )
    if listing.remaining_count < quantity:
        return False

    listing.remaining_count -= quantity
    if listing.remaining_count == 0:
        listing.status = "sold_out"
    db.commit()
    return True
