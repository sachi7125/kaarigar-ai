"""GET /schemes?artisan_id=… — scheme cards matched to her listings (Day 7).
Public information, derived only from her public listing categories."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.models import Listing
from app.db.session import get_db
from app.services.schemes import scheme_cards

router = APIRouter()


@router.get("/schemes")
def schemes_for_artisan(artisan_id: str, db: Session = Depends(get_db)):
    categories = [c for (c,) in db.query(Listing.category).filter(Listing.artisan_id == artisan_id)]
    return {"cards": scheme_cards(categories)}
