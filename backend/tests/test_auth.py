"""Device-token checks on the artisan-only endpoints (Day 7, middleman guard)."""
from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import offers, onboarding
from app.auth import require_artisan
from app.db.models import Artisan, Listing, Offer
from app.db.session import Base, get_db

PHONE = "+911234500001"


def _register(db, phone=PHONE):
    return onboarding.register(phone=phone, language="hi", db=db)


def _verify(db, phone=PHONE):
    otp = onboarding.send_otp(phone=phone)["otp"]
    return onboarding.verify_otp(phone=phone, otp=otp, db=db)


def test_new_number_gets_a_token_but_an_existing_one_must_verify(db_session):
    first = _register(db_session)
    assert first["auth_token"] and first["needs_otp"] is False
    again = _register(db_session)
    assert again["artisan_id"] == first["artisan_id"]
    assert again["auth_token"] is None and again["needs_otp"] is True


def test_verifying_issues_a_new_token_and_signs_the_old_phone_out(db_session):
    old = _register(db_session)["auth_token"]
    new = _verify(db_session)["auth_token"]
    assert new and new != old
    assert require_artisan(f"Bearer {new}", db_session).phone == PHONE
    with pytest.raises(HTTPException) as e:
        require_artisan(f"Bearer {old}", db_session)
    assert e.value.status_code == 401


@pytest.mark.parametrize("header", [None, "", "Bearer", "Bearer   ", "Token abc", "abc"])
def test_missing_or_malformed_header_is_401(db_session, header):
    with pytest.raises(HTTPException) as e:
        require_artisan(header, db_session)
    assert e.value.status_code == 401


def test_only_a_hash_of_the_token_is_stored(db_session):
    token = _register(db_session)["auth_token"]
    artisan = db_session.query(Artisan).filter(Artisan.phone == PHONE).one()
    assert artisan.auth_token_hash and token not in artisan.auth_token_hash


def _shop_with_offer(db):
    owner = Artisan(phone="+911234500002", verified=True)
    stranger = Artisan(phone="+911234500003", verified=True)
    db.add_all([owner, stranger])
    db.commit()
    listing = Listing(artisan_id=owner.id, category="clay pottery", material="clay", size_class="medium",
                      title_en="Pot", title_hi="मटका", description_en="d", description_hi="d",
                      price_inr=500)
    db.add(listing)
    db.commit()
    offer = Offer(listing_id=listing.id, buyer_name="B", buyer_contact="buyer@x.com",
                  price_inr=500, quantity=1)
    db.add(offer)
    db.commit()
    return owner, stranger, offer


def test_someone_elses_offer_looks_like_a_missing_one(db_session):
    owner, stranger, offer = _shop_with_offer(db_session)
    for action in (offers.accept_offer, offers.decline_offer):
        with pytest.raises(HTTPException) as e:
            action(offer.id, db_session, stranger)
        assert e.value.status_code == 404
    db_session.refresh(offer)
    assert offer.status == "pending"
    assert offers.accept_offer(offer.id, db_session, owner)["buyer_contact"] == "buyer@x.com"


def test_offer_inbox_is_only_her_own(db_session):
    owner, stranger, _ = _shop_with_offer(db_session)
    assert len(offers.list_offers_for_artisan(None, db_session, owner)) == 1
    assert offers.list_offers_for_artisan(None, db_session, stranger) == []
    with pytest.raises(HTTPException) as e:
        offers.list_offers_for_artisan(owner.id, db_session, stranger)
    assert e.value.status_code == 403


def test_routes_really_require_the_token():
    """The tests above call the functions directly; this one goes through HTTP,
    so a route that lost its Depends(require_artisan) fails here."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    owner, _, offer = _shop_with_offer(db)
    token = onboarding.register(phone="+911234500004", language="hi", db=db)["auth_token"]

    app = FastAPI()
    app.include_router(offers.router)

    def _db():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _db
    client = TestClient(app)
    assert client.get(f"/offers?artisan_id={owner.id}").status_code == 401
    assert client.post(f"/offers/{offer.id}/accept").status_code == 401
    assert client.post(f"/offers/{offer.id}/decline").status_code == 401
    # a valid token for a different artisan still can't touch her offer
    other = {"Authorization": f"Bearer {token}"}
    assert client.post(f"/offers/{offer.id}/accept", headers=other).status_code == 404
    assert client.get("/offers", headers=other).json() == []
    db.close()
