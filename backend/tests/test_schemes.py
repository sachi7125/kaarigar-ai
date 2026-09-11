"""Scheme cards (Day 7): shown only for crafts that map to a scheme trade, and
worded as "seems to"/"may", never as a promise of eligibility."""
from __future__ import annotations

import csv

from app.api.schemes import schemes_for_artisan
from app.config import REPO_ROOT
from app.db.models import Artisan, Listing
from app.services.schemes import load_schemes


def _artisan_with(db, *categories: str) -> Artisan:
    a = Artisan(phone="+911234500030", verified=True)
    db.add(a)
    db.commit()
    for c in categories:
        db.add(Listing(artisan_id=a.id, category=c, material="", size_class="medium",
                       title_en="t", title_hi="t", description_en="d", description_hi="d", price_inr=500))
    db.commit()
    return a


def _cards(db, artisan):
    return schemes_for_artisan(artisan.id, db)["cards"]


def test_a_potter_gets_the_pm_vishwakarma_card(db_session):
    cards = _cards(db_session, _artisan_with(db_session, "clay pottery"))
    assert len(cards) == 1
    card = cards[0]
    assert card["id"] == "pm_vishwakarma"
    assert card["trade_en"] == "Potter (Kumhaar)" and card["match"] == "likely"
    assert "कुम्हार" in card["spoken_hi"] and "कॉमन सर्विस सेंटर" in card["spoken_hi"]


def test_uncertain_trades_are_worded_as_uncertain(db_session):
    card = _cards(db_session, _artisan_with(db_session, "dhokra figurine"))[0]
    assert card["match"] == "possible" and "शायद" in card["fit_hi"] and "may" in card["fit_en"]


def test_unmapped_crafts_get_no_card(db_session):
    a = _artisan_with(db_session, "banarasi silk saree", "madhubani painting", "jute bag")
    assert _cards(db_session, a) == []


def test_a_listing_saved_before_day7_with_free_text_still_matches(db_session):
    # the dev shop's real listings were stored as plain "pottery"
    assert _cards(db_session, _artisan_with(db_session, "pottery"))[0]["trade_en"] == "Potter (Kumhaar)"


def test_no_listings_no_card(db_session):
    assert _cards(db_session, _artisan_with(db_session)) == []


def test_her_most_listed_craft_decides_the_trade(db_session):
    a = _artisan_with(db_session, "silver jewellery", "clay pottery", "clay pottery")
    assert _cards(db_session, a)[0]["trade_en"] == "Potter (Kumhaar)"


def test_every_mapped_category_is_one_pricing_knows():
    path = REPO_ROOT / "data" / "reference" / "category_weight_overrides.csv"
    rows = csv.DictReader(l for l in path.read_text(encoding="utf-8").splitlines()
                          if l.strip() and not l.startswith("#"))
    known = {r["category"].strip().lower() for r in rows}
    for scheme in load_schemes():
        assert set(scheme["trades"]) <= known, set(scheme["trades"]) - known


def test_scheme_files_are_dated_and_sourced():
    for scheme in load_schemes():
        assert scheme["checked_on"]
        assert scheme["sources"] and all(s.startswith("https://") for s in scheme["sources"])
