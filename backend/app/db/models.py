"""SQLAlchemy models — the single system of record.

Tables: artisan, listing (unique|batch + remaining_count), offer (status, expiry),
issue_report, follower (Day 6: storefront follow/digest). Dashboard aggregates
are computed on the fly from these tables (COUNT/SUM queries) rather than a
separate `event` log table — a hackathon-scale prototype doesn't need
event-sourcing to answer "how many listings/offers/followers does she have".

The permanent listing/storefront URL id scheme is FROZEN once a stall QR is
printed (watchlist) — `generate_short_id()` is that decision, made once, here:
config.yaml's `listings.id_scheme: short_base32`, base32 (Crockford-ish,
lowercase, no padding) of random bytes. Don't change the alphabet or length
after any listing has been created for real.
"""
from __future__ import annotations

import base64
import datetime
import os
import secrets

from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import deferred, relationship

from app.db.session import Base


def generate_short_id(length: int = 6) -> str:
    """Short, URL-safe, base32 id — e.g. kaarigar.in/l/<id>. Collision odds at
    this length are low enough for a prototype's listing volume; a real launch
    would check-and-retry on insert, which callers already do (IntegrityError)."""
    raw = secrets.token_bytes(8)
    return base64.b32encode(raw).decode("ascii").rstrip("=").lower()[:length]


class Artisan(Base):
    __tablename__ = "artisans"

    id = Column(String, primary_key=True, default=lambda: generate_short_id(10))
    phone = Column(String, unique=True, nullable=False, index=True)
    language = Column(String, nullable=False, default="hi")
    # Deferred verification (D-onboarding, Day 5): she can capture/queue/draft
    # unverified; only PUBLISHING a listing requires verified=True.
    verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Maker story (Day 6): a short bilingual first-person bio, built from a
    # voice note the same way a listing description is (pipelines.voice.maker_story),
    # shown at the top of her storefront. Null until she records one — the
    # storefront renders a "record your story" prompt instead, never a blank.
    maker_story_text_en = Column(Text, nullable=True)
    maker_story_text_hi = Column(Text, nullable=True)
    maker_story_audio_path = Column(String, nullable=True)

    # Day 7, middleman guard (roadmap: "account & QR bound to her own number,
    # earnings only in her view"): SHA-256 of the one device token her phone
    # holds (app/auth.py). Issued when she first registers her number and
    # re-issued, replacing the old one, whenever she verifies by OTP. Offers,
    # buyer contacts and earnings all need it.
    auth_token_hash = Column(String, nullable=True)
    # Opens of her public storefront page (/s/<id>), for the no-offers nudge.
    storefront_views = Column(Integer, nullable=False, default=0, server_default="0")

    listings = relationship("Listing", back_populates="artisan")
    followers = relationship("Follower", back_populates="artisan")


class Listing(Base):
    __tablename__ = "listings"

    id = Column(String, primary_key=True, default=generate_short_id)  # public URL id
    artisan_id = Column(String, ForeignKey("artisans.id"), nullable=False, index=True)

    category = Column(String, nullable=False)
    material = Column(String, nullable=False)
    size_class = Column(String, nullable=False)

    title_en = Column(String, nullable=False)
    title_hi = Column(String, nullable=False)
    description_en = Column(Text, nullable=False)
    description_hi = Column(Text, nullable=False)

    image_path = Column(String, nullable=True)
    audio_path = Column(String, nullable=True)

    price_inr = Column(Float, nullable=False)          # the price she actually listed at
    band_low_inr = Column(Float, nullable=True)         # informational, shown on the public page
    band_high_inr = Column(Float, nullable=True)

    stock_type = Column(String, nullable=False, default="unique")  # "unique" | "batch"
    total_count = Column(Integer, nullable=False, default=1)
    remaining_count = Column(Integer, nullable=False, default=1)

    # Day 7, per-piece vs per-set (roadmap: "ask"): "set" means price_inr buys
    # all pack_size pieces together as one lot, so total/remaining count lots.
    price_unit = Column(String, nullable=False, default="piece", server_default="piece")
    pack_size = Column(Integer, nullable=False, default=1, server_default="1")
    # Opens of the buyer page (/l/<id>), for the no-offers nudge. Crawlers count too.
    view_count = Column(Integer, nullable=False, default=0, server_default="0")

    status = Column(String, nullable=False, default="published")  # "published" | "sold_out"
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    artisan = relationship("Artisan", back_populates="listings")
    offers = relationship("Offer", back_populates="listing")
    photo = relationship("ListingPhoto", uselist=False, back_populates="listing")


class ListingPhoto(Base):
    """The listing photo itself, downscaled, stored with the listing (Day 7).

    Buyer pages must work wherever the database is, including the Vercel
    deployment, which has no disk to serve backend/data/uploads/ from. At
    ~150 KB a photo this is fine for a prototype; a real launch would move
    it to object storage and keep only the URL here."""
    __tablename__ = "listing_photos"

    listing_id = Column(String, ForeignKey("listings.id"), primary_key=True)
    content_type = Column(String, nullable=False, default="image/jpeg")
    data = deferred(Column(LargeBinary, nullable=False))
    # "enhanced": the Day-1 pipeline's cut-out on white, square-cropped, colour
    # corrected (what scripts/try_photo.py shows). "original": the photo as
    # taken, kept when the cut-out failed its own sanity check — a plain photo
    # beats a broken cut-out.
    kind = Column(String, nullable=False, default="original", server_default="original")
    # The same pipeline's zoomed surface close-up; null for "original".
    texture_data = deferred(Column(LargeBinary, nullable=True))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    listing = relationship("Listing", back_populates="photo")


class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(String, ForeignKey("listings.id"), nullable=False, index=True)

    buyer_name = Column(String, nullable=False)
    buyer_contact = Column(String, nullable=False)  # only surfaced to the artisan after accept
    price_inr = Column(Float, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    message = Column(Text, nullable=True)
    # Day 6: true if buyer_contact has a prior ACCEPTED offer from this same
    # artisan (any listing), computed once at submission time — not a live
    # join, so it can't change retroactively once an offer exists. Spoken
    # alongside the offer in the artisan's inbox (roadmap: "returning-buyer
    # flag spoken with the offer").
    is_returning_buyer = Column(Boolean, nullable=False, default=False)

    # "pending" | "accepted" | "declined" | "auto_declined" | "expired"
    status = Column(String, nullable=False, default="pending")
    decline_reason = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    listing = relationship("Listing", back_populates="offers")


class IssueReport(Base):
    __tablename__ = "issue_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    listing_id = Column(String, ForeignKey("listings.id"), nullable=True, index=True)
    reporter_contact = Column(String, nullable=True)
    description = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class Follower(Base):
    """A buyer who asked to hear about new work (Day 6). Email only — no
    phone/SMS channel here, matching config.yaml's `storefront.follow_digest`.
    Actual weekly SEND is mocked (no SMTP provider budgeted, same disclosed-
    shortcut pattern as D18's OTP) but the digest CONTENT is assembled for
    real by `storefront.py`'s digest builder — see decisions.md."""
    __tablename__ = "followers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    artisan_id = Column(String, ForeignKey("artisans.id"), nullable=False, index=True)
    email = Column(String, nullable=False, index=True)
    # One-click unsubscribe token (roadmap: "one-click unsubscribe") — a random
    # value, not derivable from the email, so an unsubscribe link can't be
    # guessed or reused to unsubscribe someone else.
    unsubscribe_token = Column(String, unique=True, nullable=False,
                                default=lambda: secrets.token_urlsafe(24))
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    artisan = relationship("Artisan", back_populates="followers")
