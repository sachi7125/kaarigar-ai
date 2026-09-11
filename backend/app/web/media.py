"""Listing photos (Day 7): GET /media/listing/<id> is the main photo (the
product cut out on white, when the cut-out worked) and
GET /media/listing/<id>/texture is its surface close-up.

Replaces the old StaticFiles mount of backend/data/uploads/, which also
served the artisans' voice recordings to anyone who could guess a filename.
Only listing photos are reachable now, looked up by listing id.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.models import Listing
from app.db.session import get_db
from app.services.photos import listing_photo_bytes, listing_texture_bytes

router = APIRouter()

# An hour, not a day: a listing's photo can be re-made (scripts/backfill_listing_photos.py).
_CACHE = {"Cache-Control": "public, max-age=3600"}


def _listing(db: Session, listing_id: str) -> Listing | None:
    return db.query(Listing).filter(Listing.id == listing_id).first()


@router.get("/media/listing/{listing_id}")
def listing_photo(listing_id: str, db: Session = Depends(get_db)):
    listing = _listing(db, listing_id)
    photo = listing_photo_bytes(db, listing) if listing is not None else None
    if photo is None:
        raise HTTPException(status_code=404, detail="no photo")
    data, content_type = photo
    return Response(content=data, media_type=content_type, headers=_CACHE)


@router.get("/media/listing/{listing_id}/texture")
def listing_texture(listing_id: str, db: Session = Depends(get_db)):
    listing = _listing(db, listing_id)
    data = listing_texture_bytes(db, listing) if listing is not None else None
    if data is None:
        raise HTTPException(status_code=404, detail="no close-up")
    return Response(content=data, media_type="image/jpeg", headers=_CACHE)
