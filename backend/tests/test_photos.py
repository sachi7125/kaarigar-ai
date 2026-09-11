"""Listing photos (Day 7): the enhanced pair (product on white + surface
close-up) when the cut-out works, the photo as taken when it doesn't."""
from __future__ import annotations

import io

from PIL import Image, ImageDraw

from app.db.models import Artisan, Listing, ListingPhoto
from app.services import photos


def _photo(tmp_path, name: str = "pot.jpg"):
    # an orange pot on a dark green background, 900×700 like a landscape phone shot
    img = Image.new("RGB", (900, 700), (40, 90, 50))
    ImageDraw.Draw(img).ellipse((300, 180, 600, 520), fill=(205, 110, 50))
    path = tmp_path / name
    img.save(path, quality=95)
    return path


def _listing(db) -> Listing:
    artisan = Artisan(phone="+911234500040", verified=True)
    db.add(artisan)
    db.commit()
    listing = Listing(artisan_id=artisan.id, category="clay pottery", material="clay",
                      size_class="medium", title_en="Pot", title_hi="मटका",
                      description_en="d", description_hi="d", price_inr=500)
    db.add(listing)
    db.commit()
    return listing


def test_a_clean_cutout_is_stored_as_the_enhanced_pair(db_session, tmp_path):
    listing = _listing(db_session)
    assert photos.store_listing_photo(db_session, listing.id, str(_photo(tmp_path))) == "enhanced"
    db_session.commit()

    data, content_type = photos.listing_photo_bytes(db_session, listing)
    main = Image.open(io.BytesIO(data)).convert("L")
    assert content_type == "image/jpeg" and main.width == main.height          # square
    corners = [main.getpixel(p) for p in ((4, 4), (main.width - 5, 4), (4, main.height - 5))]
    assert min(corners) > 245                                                  # on white
    assert photos.listing_texture_bytes(db_session, listing) is not None
    assert photos.ids_with_textures(db_session, [listing]) == {listing.id}


def test_a_failed_cutout_keeps_the_photo_as_taken(db_session, tmp_path, monkeypatch):
    monkeypatch.setattr(photos, "_enhanced_pair", lambda path: None)
    listing = _listing(db_session)
    assert photos.store_listing_photo(db_session, listing.id, str(_photo(tmp_path))) == "original"
    db_session.commit()
    main = Image.open(io.BytesIO(photos.listing_photo_bytes(db_session, listing)[0]))
    assert main.size == (900, 700)                   # uncropped, not squared
    assert photos.listing_texture_bytes(db_session, listing) is None
    assert photos.ids_with_textures(db_session, [listing]) == set()


def test_an_unreadable_file_stores_nothing(db_session, tmp_path):
    listing = _listing(db_session)
    bad = tmp_path / "broken.jpg"
    bad.write_bytes(b"not an image")
    assert photos.store_listing_photo(db_session, listing.id, str(bad)) == ""
    assert db_session.get(ListingPhoto, listing.id) is None
