"""Unit tests for the maker-story builder that don't call the Gemini API."""
from __future__ import annotations

import json

from pipelines.voice.maker_story import MakerStory, build_maker_story, _cache_key


def test_template_fallback_when_gemini_disabled():
    r = build_maker_story("मैं जयपुर में मिट्टी के बर्तन बनाती हूँ", lang="hi",
                          allow_gemini=False, use_cache=False)
    assert r.source == "template"
    assert r.error and "template" in r.error
    assert "मिट्टी के बर्तन" in r.text_hi


def test_english_input_mirrors_both_sides():
    r = build_maker_story("I make clay pots in Jaipur", lang="en",
                          allow_gemini=False, use_cache=False)
    assert r.text_en == r.text_hi == "I make clay pots in Jaipur"


def test_empty_transcript_never_invents_a_bio():
    r = build_maker_story("", lang="hi", allow_gemini=False, use_cache=False)
    assert isinstance(r, MakerStory)
    assert r.error
    # generic, honest fallback line — never a fabricated name/place/years
    assert r.text_hi == "एक हस्तशिल्प कारीगर।"


def test_cache_roundtrip(tmp_path, monkeypatch):
    import pipelines.voice.maker_story as mod

    monkeypatch.setattr(mod, "_CACHE_DIR", tmp_path / "cache")
    story = mod._story_template("test note", "hi")
    key = _cache_key("test note", "hi")
    mod._cache_write(key, story)
    hit = mod._cache_read(key)
    assert hit is not None
    assert hit.source == "cache"
    assert hit.text_hi == "test note"


def test_as_dict_is_json_serialisable():
    r = build_maker_story("test", lang="en", allow_gemini=False, use_cache=False)
    json.dumps(r.as_dict())  # must not raise
