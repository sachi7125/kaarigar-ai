"""Unit tests for asking-price tolerance + quantity + rate-limit checks."""
from __future__ import annotations

import datetime

from app.db.models import Artisan, Listing, Offer
from app.services import offer_validation


def _make_listing(db, price=1000, remaining=5):
    artisan = Artisan(phone="+910000000001", verified=True)
    db.add(artisan)
    db.commit()
    listing = Listing(
        artisan_id=artisan.id, category="clay pottery", material="clay", size_class="medium",
        title_en="t", title_hi="t", description_en="d", description_hi="d",
        price_inr=price, stock_type="batch", total_count=remaining, remaining_count=remaining,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def test_valid_offer_at_full_price_passes(db_session):
    listing = _make_listing(db_session)
    ok, reason = offer_validation.validate_offer(db_session, listing, 1000, 1, "buyer@x.com")
    assert ok is True and reason == ""


def test_offer_within_tolerance_passes(db_session, monkeypatch):
    monkeypatch.setattr(offer_validation, "cfg_get",
                        lambda path, default=None: 0.05 if "tolerance" in path else default)
    listing = _make_listing(db_session, price=1000)
    ok, _ = offer_validation.validate_offer(db_session, listing, 960, 1, "buyer@x.com")  # -4%
    assert ok is True


def test_offer_below_tolerance_auto_declines(db_session, monkeypatch):
    monkeypatch.setattr(offer_validation, "cfg_get",
                        lambda path, default=None: 0.05 if "tolerance" in path else default)
    listing = _make_listing(db_session, price=1000)
    ok, reason = offer_validation.validate_offer(db_session, listing, 900, 1, "buyer@x.com")  # -10%
    assert ok is False and "asking price" in reason


def test_quantity_exceeding_stock_declines(db_session):
    listing = _make_listing(db_session, remaining=3)
    ok, reason = offer_validation.validate_offer(db_session, listing, 1000, 5, "buyer@x.com")
    assert ok is False and "stock" in reason


def test_invalid_quantity_declines(db_session):
    listing = _make_listing(db_session)
    ok, reason = offer_validation.validate_offer(db_session, listing, 1000, 0, "buyer@x.com")
    assert ok is False and "quantity" in reason


def test_rate_limit_declines_after_threshold(db_session, monkeypatch):
    monkeypatch.setattr(offer_validation, "cfg_get",
                        lambda path, default=None: 2 if "rate_limit" in path else default)
    listing = _make_listing(db_session, remaining=100)
    for _ in range(2):
        db_session.add(Offer(listing_id=listing.id, buyer_name="x", buyer_contact="spammer@x.com",
                             price_inr=1000, quantity=1, status="pending",
                             created_at=datetime.datetime.utcnow()))
    db_session.commit()
    ok, reason = offer_validation.validate_offer(db_session, listing, 1000, 1, "spammer@x.com")
    assert ok is False and "rate limited" in reason


def test_rate_limit_only_counts_the_last_hour(db_session, monkeypatch):
    monkeypatch.setattr(offer_validation, "cfg_get",
                        lambda path, default=None: 1 if "rate_limit" in path else default)
    listing = _make_listing(db_session, remaining=100)
    old = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
    db_session.add(Offer(listing_id=listing.id, buyer_name="x", buyer_contact="buyer@x.com",
                         price_inr=1000, quantity=1, status="pending", created_at=old))
    db_session.commit()
    ok, _ = offer_validation.validate_offer(db_session, listing, 1000, 1, "buyer@x.com")
    assert ok is True   # the old offer is outside the 1-hour window
