"""Unit tests for the listing builder that don't call the Gemini API."""
from __future__ import annotations

import json

from pipelines.voice.describe import ListingDraft, describe, _cache_key


def test_template_fallback_when_gemini_disabled():
    r = describe("यह नीली मिट्टी की मटकी है", lang="hi", allow_gemini=False,
                 use_cache=False, attributes={"category": "clay pottery",
                                              "materials": ["clay"]})
    assert r.source == "template"
    assert r.error and "template" in r.error
    assert "clay pottery" in r.title_en.lower()
    assert r.category == "clay pottery"
    assert "clay" in r.materials
    # Hindi side keeps the maker's own words rather than risk a bad offline translation
    assert r.title_hi.startswith("यह नीली")


def test_template_keeps_transcript_in_hindi_desc():
    r = describe("हाथ से बुनी सूती साड़ी", lang="hi", allow_gemini=False, use_cache=False)
    assert "हाथ से बुनी सूती साड़ी" in r.description_hi


def test_english_input_not_duplicated_into_hindi_verbatim():
    r = describe("a hand-thrown clay pot", lang="en", allow_gemini=False, use_cache=False)
    assert r.title_hi == r.title_en  # en input: hi side mirrors en, not a raw copy path


def test_empty_input_returns_draft_with_error():
    r = describe("", lang="hi", allow_gemini=False, use_cache=False)
    assert isinstance(r, ListingDraft)
    assert r.error


def test_cache_roundtrip(tmp_path, monkeypatch):
    import pipelines.voice.describe as mod

    monkeypatch.setattr(mod, "_CACHE_DIR", tmp_path / "cache")
    draft = mod._describe_template("test note", "hi", {"category": "toys"})
    key = _cache_key("test note", "hi", {"category": "toys"})
    mod._cache_write(key, draft)
    hit = mod._cache_read(key)
    assert hit is not None
    assert hit.source == "cache"
    assert hit.category == "toys"


def test_as_dict_is_json_serialisable():
    r = describe("test", lang="en", allow_gemini=False, use_cache=False)
    json.dumps(r.as_dict())  # must not raise
