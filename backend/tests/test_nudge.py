"""The no-offers-for-a-week nudge (Day 7): only after a quiet week, and every
reason read off her own data."""
from __future__ import annotations

import datetime

from app.db.models import Artisan, Listing, ListingPhoto, Offer
from app.services.nudge import no_offers_nudge

NOW = datetime.datetime(2026, 9, 11, 12, 0)


def _days_ago(n: float) -> datetime.datetime:
    return NOW - datetime.timedelta(days=n)


def _artisan(db, story: bool = False) -> Artisan:
    a = Artisan(phone="+911234500020", verified=True, maker_story_text_hi="कहानी" if story else None)
    db.add(a)
    db.commit()
    return a


def _listing(db, artisan, age_days=10, photo=False, **overrides) -> Listing:
    fields = dict(artisan_id=artisan.id, category="clay pottery", material="clay", size_class="medium",
                  title_en="Pot", title_hi="मटका", description_en="d", description_hi="d",
                  price_inr=1000, created_at=_days_ago(age_days))
    fields.update(overrides)
    listing = Listing(**fields)
    db.add(listing)
    db.commit()
    if photo:
        db.add(ListingPhoto(listing_id=listing.id, data=b"jpeg"))
        db.commit()
    return listing


def _offer(db, listing, price, days_ago, status="pending"):
    db.add(Offer(listing_id=listing.id, buyer_name="b", buyer_contact="b@x.com", price_inr=price,
                 status=status, created_at=_days_ago(days_ago)))
    db.commit()


def _codes(nudge) -> list[str]:
    return [r["code"] for r in nudge["reasons"]]


def test_quiet_until_a_listing_has_been_up_a_week(db_session):
    a = _artisan(db_session)
    _listing(db_session, a, age_days=3)
    assert no_offers_nudge(db_session, a, NOW) is None


def test_quiet_when_a_real_offer_came_this_week(db_session):
    a = _artisan(db_session)
    _offer(db_session, _listing(db_session, a), 1000, days_ago=2)
    assert no_offers_nudge(db_session, a, NOW) is None


def test_reasons_come_from_her_own_data(db_session):
    a = _artisan(db_session)
    _listing(db_session, a, price_inr=1500, band_low_inr=800, band_high_inr=1200)
    nudge = no_offers_nudge(db_session, a, NOW)
    assert _codes(nudge) == ["no_views", "above_band", "no_photo", "no_story"]
    assert "₹1500" in nudge["spoken_hi"] and "₹800–₹1200" in nudge["spoken_hi"]


def test_turned_away_offers_are_reported_with_the_best_price(db_session):
    a = _artisan(db_session, story=True)
    listing = _listing(db_session, a, photo=True, view_count=9)
    _offer(db_session, listing, 300, days_ago=1, status="auto_declined")
    _offer(db_session, listing, 450, days_ago=2, status="auto_declined")
    nudge = no_offers_nudge(db_session, a, NOW)
    assert _codes(nudge) == ["auto_declined"]
    assert "2 ऑफ़र" in nudge["reasons"][0]["text_hi"] and "₹450" in nudge["reasons"][0]["text_hi"]


def test_page_opens_without_offers(db_session):
    a = _artisan(db_session, story=True)
    _listing(db_session, a, photo=True, view_count=5)
    a.storefront_views = 2
    db_session.commit()
    nudge = no_offers_nudge(db_session, a, NOW)
    assert _codes(nudge) == ["views_no_offers"]
    assert "7 बार" in nudge["reasons"][0]["text_hi"]


def test_an_offer_older_than_a_week_does_not_count(db_session):
    a = _artisan(db_session)
    _offer(db_session, _listing(db_session, a, age_days=20), 1000, days_ago=9)
    assert no_offers_nudge(db_session, a, NOW) is not None
