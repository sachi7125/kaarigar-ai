"""Re-make the photos of listings published before the enhanced pair existed (Day 7).

    .venv/bin/python scripts/backfill_listing_photos.py          # listings without the enhanced pair
    .venv/bin/python scripts/backfill_listing_photos.py --redo   # every listing, e.g. after the pipeline changed

Runs listings through the same pipeline publish now uses (app/services/photos.py). Uses DATABASE_URL like
the server does, so it updates whichever database the server is pointed at.
Only listings whose original upload is still on this machine can be redone;
the rest are left exactly as they are.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(REPO), str(REPO / "backend")]
os.chdir(REPO / "backend")  # Listing.image_path is relative to backend/, the server's cwd

from app.db.models import Listing, ListingPhoto  # noqa: E402
from app.db.session import SessionLocal, init_db  # noqa: E402
from app.services.photos import store_listing_photo  # noqa: E402


def main() -> int:
    redo = "--redo" in sys.argv[1:]
    init_db()
    db = SessionLocal()
    try:
        for listing in db.query(Listing).order_by(Listing.created_at).all():
            row = db.get(ListingPhoto, listing.id)
            if row is not None and row.kind == "enhanced" and not redo:
                print(f"  = {listing.id}: already enhanced")
                continue
            if not listing.image_path or not Path(listing.image_path).is_file():
                print(f"  - {listing.id}: no original photo on this machine")
                continue
            kind = store_listing_photo(db, listing.id, listing.image_path)
            db.commit()
            print(f"  ✓ {listing.id}: {kind or 'unreadable, left as it was'}")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
