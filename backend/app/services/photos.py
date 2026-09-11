"""Listing photos kept in the database (Day 7) — see models.ListingPhoto.

At publish the uploaded photo goes through the Day-1 image pipeline
(pipelines.image.enhance, the same one scripts/try_photo.py runs): the product
cut out onto white, square-cropped, colour and lighting corrected, plus a
zoomed close-up of its surface. That pair is what buyers see, what goes on the
share card, and what marketplace exports point to — Amazon and GeM both want
the main image on a white background. When the cut-out fails the pipeline's
own sanity check, the photo as taken is stored instead.

OpenCV, onnxruntime and Pillow are imported only inside the functions that
make photos: the public Vercel app (app/public_main.py) serves them, never
makes them, and doesn't ship those packages.
"""
from __future__ import annotations

import io
import mimetypes
import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import Listing, ListingPhoto

MAX_EDGE_PX = 1280       # sharp on a phone, ~100-200 KB as JPEG
JPEG_QUALITY = 88


def _jpeg(path: str) -> bytes:
    from PIL import Image, ImageOps

    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        img.thumbnail((MAX_EDGE_PX, MAX_EDGE_PX))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue()


def _enhanced_pair(image_path: str) -> tuple[bytes, bytes] | None:
    """(product on white, surface close-up) as JPEG bytes, or None when the
    cut-out failed its check. Runs in a temporary folder, so nothing it writes
    stays on disk."""
    from pipelines.image.enhance import enhance

    with tempfile.TemporaryDirectory() as tmp:
        result = enhance(image_path, tmp)
        if result.status != "ok":
            return None
        return _jpeg(result.outputs["enhanced"]), _jpeg(result.outputs["texture"])


def store_listing_photo(db: Session, listing_id: str, image_path: str) -> str:
    """Save the listing's photos with it. Returns "enhanced", "original", or
    "" if the file can't be read as an image at all (nothing stored). The
    caller commits, so the photos land in the same transaction as the listing."""
    try:
        pair = _enhanced_pair(image_path)
    except Exception:
        pair = None  # any failure inside the pipeline: fall back to the photo as taken
    try:
        if pair is not None:
            row = ListingPhoto(listing_id=listing_id, kind="enhanced", content_type="image/jpeg",
                               data=pair[0], texture_data=pair[1])
        else:
            row = ListingPhoto(listing_id=listing_id, kind="original", content_type="image/jpeg",
                               data=_jpeg(image_path), texture_data=None)
    except (OSError, ValueError):
        return ""
    db.merge(row)
    return row.kind


def _disk_photo(listing: Listing) -> Path | None:
    # Listings published before Day 7 only have the upload on this machine's disk.
    if listing.image_path and Path(listing.image_path).is_file():
        return Path(listing.image_path)
    return None


def listing_photo_bytes(db: Session, listing: Listing) -> tuple[bytes, str] | None:
    row = db.get(ListingPhoto, listing.id)
    if row is not None:
        return row.data, row.content_type
    path = _disk_photo(listing)
    if path is not None:
        return path.read_bytes(), mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return None


def listing_texture_bytes(db: Session, listing: Listing) -> bytes | None:
    row = db.get(ListingPhoto, listing.id)
    return row.texture_data if row is not None else None


def ids_with_photos(db: Session, listings: list[Listing]) -> set[str]:
    ids = [l.id for l in listings]
    if not ids:
        return set()
    stored = {pid for (pid,) in db.query(ListingPhoto.listing_id).filter(ListingPhoto.listing_id.in_(ids))}
    return stored | {l.id for l in listings if _disk_photo(l) is not None}


def ids_with_textures(db: Session, listings: list[Listing]) -> set[str]:
    ids = [l.id for l in listings]
    if not ids:
        return set()
    return {pid for (pid,) in db.query(ListingPhoto.listing_id)
            .filter(ListingPhoto.listing_id.in_(ids), ListingPhoto.texture_data.isnot(None))}
