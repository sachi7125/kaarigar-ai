"""Unit tests for storefront dashboard aggregates, follow/unsubscribe, and
the returning-buyer flag — called directly against a db_session, the same
pattern test_stock.py/test_offer_validation.py use (FastAPI endpoint
functions are plain Python functions when not routed through the app)."""
from __future__ import annotations

from app.api import offers, storefront
from app.api.offers import OfferRequest
from app.api.storefront import FollowRequest
from app.db.models import Artisan, Follower, Listing, Offer


def _make_artisan(db, verified=True):
    artisan = Artisan(phone="+910000000010", verified=verified)
    db.add(artisan)
    db.commit()
    db.refresh(artisan)
    return artisan


def _make_listing(db, artisan, price=1000, total=1, remaining=None, status="published"):
    listing = Listing(
        artisan_id=artisan.id, category="clay pottery", material="clay", size_class="medium",
        title_en="t", title_hi="t", description_en="d", description_hi="d",
        price_inr=price, stock_type="batch" if total > 1 else "unique",
        total_count=total, remaining_count=remaining if remaining is not None else total,
        status=status,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return listing


def test_dashboard_aggregates_are_real_not_placeholders(db_session):
    artisan = _make_artisan(db_session)
    l1 = _make_listing(db_session, artisan, price=500, total=3, remaining=1)
    l2 = _make_listing(db_session, artisan, price=1000, total=1, remaining=0, status="sold_out")
    db_session.add(Offer(listing_id=l1.id, buyer_name="a", buyer_contact="a@x.com",
                         price_inr=500, quantity=2, status="accepted"))
    db_session.add(Offer(listing_id=l1.id, buyer_name="b", buyer_contact="b@x.com",
                         price_inr=500, quantity=1, status="pending"))
    db_session.add(Follower(artisan_id=artisan.id, email="f1@x.com"))
    db_session.add(Follower(artisan_id=artisan.id, email="f2@x.com"))
    db_session.commit()

    d = storefront.storefront_dashboard(artisan.id, db_session, artisan)
    assert d["listings_count"] == 2
    assert d["published_count"] == 1
    assert d["sold_out_count"] == 1
    assert d["pending_offers_count"] == 1
    assert d["accepted_offers_count"] == 1
    assert d["total_earning_inr"] == 1000        # 500 * 2, accepted only
    assert d["remaining_stock_total"] == 1        # 1 + 0
    assert d["follower_count"] == 2


def test_dashboard_on_artisan_with_nothing_yet(db_session):
    artisan = _make_artisan(db_session)
    d = storefront.storefront_dashboard(artisan.id, db_session, artisan)
    assert d == {
        "listings_count": 0, "published_count": 0, "sold_out_count": 0,
        "pending_offers_count": 0, "accepted_offers_count": 0,
        "total_earning_inr": 0, "remaining_stock_total": 0, "follower_count": 0,
        "nudge": None,
    }


def test_follow_then_follow_again_is_idempotent(db_session):
    artisan = _make_artisan(db_session)
    first = storefront.follow_artisan(FollowRequest(artisan_id=artisan.id, email="buyer@x.com"), db_session)
    assert first["status"] == "following"
    second = storefront.follow_artisan(FollowRequest(artisan_id=artisan.id, email="buyer@x.com"), db_session)
    assert second["status"] == "already_following"
    assert second["unsubscribe_token"] == first["unsubscribe_token"]
    assert db_session.query(Follower).filter(Follower.artisan_id == artisan.id).count() == 1


def test_returning_buyer_flag_false_on_first_ever_offer(db_session):
    artisan = _make_artisan(db_session)
    listing = _make_listing(db_session, artisan)
    offers.submit_offer(
        OfferRequest(listing_id=listing.id, buyer_name="x", buyer_contact="new@x.com",
                    price_inr=1000, quantity=1),
        db_session,
    )
    offer = db_session.query(Offer).filter(Offer.buyer_contact == "new@x.com").first()
    assert offer.is_returning_buyer is False


def test_returning_buyer_flag_true_after_a_prior_accepted_offer(db_session):
    artisan = _make_artisan(db_session)
    listing_a = _make_listing(db_session, artisan)
    listing_b = _make_listing(db_session, artisan)
    # a prior offer from this buyer, already accepted, on a DIFFERENT listing
    # from the same artisan
    db_session.add(Offer(listing_id=listing_a.id, buyer_name="x", buyer_contact="regular@x.com",
                         price_inr=1000, quantity=1, status="accepted"))
    db_session.commit()

    offers.submit_offer(
        OfferRequest(listing_id=listing_b.id, buyer_name="x", buyer_contact="regular@x.com",
                    price_inr=1000, quantity=1),
        db_session,
    )
    new_offer = db_session.query(Offer).filter(
        Offer.buyer_contact == "regular@x.com", Offer.listing_id == listing_b.id).first()
    assert new_offer.is_returning_buyer is True


def test_returning_buyer_flag_not_set_by_a_merely_pending_prior_offer(db_session):
    artisan = _make_artisan(db_session)
    listing_a = _make_listing(db_session, artisan)
    listing_b = _make_listing(db_session, artisan)
    db_session.add(Offer(listing_id=listing_a.id, buyer_name="x", buyer_contact="maybe@x.com",
                         price_inr=1000, quantity=1, status="pending"))
    db_session.commit()

    offers.submit_offer(
        OfferRequest(listing_id=listing_b.id, buyer_name="x", buyer_contact="maybe@x.com",
                    price_inr=1000, quantity=1),
        db_session,
    )
    new_offer = db_session.query(Offer).filter(
        Offer.buyer_contact == "maybe@x.com", Offer.listing_id == listing_b.id).first()
    assert new_offer.is_returning_buyer is False
