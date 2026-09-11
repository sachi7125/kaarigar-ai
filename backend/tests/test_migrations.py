"""init_db() adds new columns to a database created before them (Day 7), so
the dev database and the shop already on the phone survive schema additions."""
from __future__ import annotations

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.models import Artisan, Listing
from app.db.session import add_missing_columns, init_db

# The two tables as Day 6 created them.
_DAY6_ARTISANS = """CREATE TABLE artisans (
    id VARCHAR PRIMARY KEY, phone VARCHAR NOT NULL UNIQUE, language VARCHAR NOT NULL,
    verified BOOLEAN NOT NULL, created_at DATETIME, maker_story_text_en TEXT,
    maker_story_text_hi TEXT, maker_story_audio_path VARCHAR)"""
_DAY6_LISTINGS = """CREATE TABLE listings (
    id VARCHAR PRIMARY KEY, artisan_id VARCHAR NOT NULL REFERENCES artisans(id),
    category VARCHAR NOT NULL, material VARCHAR NOT NULL, size_class VARCHAR NOT NULL,
    title_en VARCHAR NOT NULL, title_hi VARCHAR NOT NULL, description_en TEXT NOT NULL,
    description_hi TEXT NOT NULL, image_path VARCHAR, audio_path VARCHAR,
    price_inr FLOAT NOT NULL, band_low_inr FLOAT, band_high_inr FLOAT,
    stock_type VARCHAR NOT NULL, total_count INTEGER NOT NULL, remaining_count INTEGER NOT NULL,
    status VARCHAR NOT NULL, created_at DATETIME)"""


def test_a_day6_database_gains_the_day7_columns_and_keeps_its_rows():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with engine.begin() as conn:
        conn.execute(text(_DAY6_ARTISANS))
        conn.execute(text(_DAY6_LISTINGS))
        conn.execute(text("INSERT INTO artisans (id, phone, language, verified) "
                          "VALUES ('a1', '+910000000001', 'hi', 1)"))
        conn.execute(text(
            "INSERT INTO listings (id, artisan_id, category, material, size_class, title_en, title_hi, "
            "description_en, description_hi, price_inr, stock_type, total_count, remaining_count, status) "
            "VALUES ('l1', 'a1', 'clay pottery', 'clay', 'medium', 'Pot', 'मटका', 'd', 'd', 500, "
            "'unique', 1, 1, 'published')"))

    init_db(engine)

    inspector = inspect(engine)
    assert {"auth_token_hash", "storefront_views"} <= {c["name"] for c in inspector.get_columns("artisans")}
    assert "listing_photos" in inspector.get_table_names()
    with Session(engine) as db:
        listing = db.get(Listing, "l1")
        assert (listing.price_unit, listing.pack_size, listing.view_count) == ("piece", 1, 0)
        assert listing.title_hi == "मटका"
        assert db.get(Artisan, "a1").storefront_views == 0
    assert add_missing_columns(engine) == []  # a second start changes nothing
