"""Unit tests for the locked stock decrement — the actual mechanism behind
Day 5's "no double-accept" gate."""
from __future__ import annotations

from app.db.models import Artisan, Listing
from app.services.stock import accept_offer_and_decrement


def _make_listing(db, total=1, remaining=None):
    artisan = Artisan(phone="+910000000000", verified=True)
    db.add(artisan)
    db.commit()
    listing = Listing(
        artisan_id=artisan.id, category="clay pottery", material="clay", size_class="medium",
        title_en="t", title_hi="t", description_en="d", description_hi="d",
        price_inr=100, stock_type="batch" if total > 1 else "unique",
        total_count=total, remaining_count=remaining if remaining is not None else total,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def test_decrement_reduces_remaining_count(db_session):
    listing = _make_listing(db_session, total=12)
    ok = accept_offer_and_decrement(db_session, listing.id, 3)
    assert ok is True
    db_session.refresh(listing)
    assert listing.remaining_count == 9
    assert listing.status == "published"


def test_decrement_to_zero_marks_sold_out(db_session):
    listing = _make_listing(db_session, total=1)
    ok = accept_offer_and_decrement(db_session, listing.id, 1)
    assert ok is True
    db_session.refresh(listing)
    assert listing.remaining_count == 0
    assert listing.status == "sold_out"


def test_insufficient_stock_returns_false_without_writing(db_session):
    listing = _make_listing(db_session, total=5, remaining=2)
    ok = accept_offer_and_decrement(db_session, listing.id, 3)
    assert ok is False
    db_session.refresh(listing)
    assert listing.remaining_count == 2   # unchanged


def test_the_actual_no_double_accept_scenario(db_session):
    """Two offers on a unique (count=1) item: the first accept succeeds, the
    second must fail cleanly rather than taking stock negative."""
    listing = _make_listing(db_session, total=1)
    first = accept_offer_and_decrement(db_session, listing.id, 1)
    second = accept_offer_and_decrement(db_session, listing.id, 1)
    assert first is True
    assert second is False
    db_session.refresh(listing)
    assert listing.remaining_count == 0   # never negative
    assert listing.status == "sold_out"


def test_batch_never_goes_negative_across_many_offers(db_session):
    listing = _make_listing(db_session, total=10)
    results = [accept_offer_and_decrement(db_session, listing.id, 3) for _ in range(4)]
    db_session.refresh(listing)
    assert results == [True, True, True, False]   # 3+3+3=9 fits, the 4th (->12) doesn't
    assert listing.remaining_count == 1
    assert listing.remaining_count >= 0
