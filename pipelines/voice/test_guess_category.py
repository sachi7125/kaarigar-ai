"""Tests for describe.py's category guess and normalisation (Day 7).

Covers the real 7 Sep sandal transcript, the six cases the first version of the
fallback got wrong, and the two glossary rewrites ("सारी" -> साड़ी, "दिया" ->
दीया) that corrupted ordinary sentences."""
from __future__ import annotations

import pytest

from pipelines.voice.describe import _guess_category, describe, normalize_category
from pipelines.voice.glossary import correct as glossary_correct

REAL_SANDAL_TRANSCRIPT = "ये एक चपल है, जसि पे लेदर का मुत्रलि लगाया हूँ है"


def _guess(text: str, materials: list[str] | None = None) -> str:
    # same order as the real pipeline: glossary correction first, then describe()
    return _guess_category(glossary_correct(text).text, materials or [])


@pytest.mark.parametrize("text, want", [
    (REAL_SANDAL_TRANSCRIPT, "leather footwear"),
    ("यह चमड़े की चप्पल है", "leather footwear"),
    ("यह मिट्टी का मटका है", "clay pottery"),
    ("a clay matka", "clay pottery"),
    ("लेदर का बैग", "leather bag"),
    ("a copper vessel", "copper vessel"),
])
def test_basic_categories(text, want):
    assert _guess(text) == want


@pytest.mark.parametrize("text, want", [
    ("यह पीतल की मूर्ति ढोकरा शैली की है", "dhokra figurine"),
    ("ढोकरा मूर्ति", "dhokra figurine"),
    ("यह रेशम की साड़ी है कांजीवरम", "kanjivaram silk saree"),
    ("कांजीवरम साड़ी", "kanjivaram silk saree"),
])
def test_specific_craft_word_wins_wherever_it_appears(text, want):
    assert _guess(text) == want


@pytest.mark.parametrize("text, want", [
    ("यह तांबे का बर्तन है", "copper vessel"),
    ("यह पीतल का बर्तन है", "copper vessel"),
    ("यह मिट्टी का बर्तन है", "clay pottery"),
    ("रेशमी साड़ी", "banarasi silk saree"),
    ("सूती साड़ी", "handloom cotton saree"),
])
def test_hindi_material_words_disambiguate(text, want):
    assert _guess(text) == want


def test_confirmed_material_attribute_also_disambiguates():
    assert _guess("यह बर्तन है", materials=["copper"]) == "copper vessel"


@pytest.mark.parametrize("text", [
    "यह फूलों का हार है",   # a flower garland, not silver jewellery
    "मैं हार गई",           # "I lost"
    "मैंने उसे दिया",        # "I gave it to her", not a lamp
    "यह एक सुंदर चीज़ है",
])
def test_ordinary_words_do_not_become_a_category(text):
    assert _guess(text) == ""


def test_haar_with_silver_is_jewellery():
    assert _guess("चांदी का हार") == "silver jewellery"


def test_a_word_that_resolves_to_nothing_does_not_stop_the_scan():
    assert _guess("फूलों का हार और मिट्टी का दीया") == "terracotta diya"


def test_glossary_no_longer_rewrites_saari_or_diya():
    # "सारी" ("all") used to be "corrected" to साड़ी, misfiling this as a saree
    assert glossary_correct("मेरी सारी चप्पलें हाथ से बनी हैं").text.startswith("मेरी सारी")
    assert _guess("मेरी सारी चप्पलें हाथ से बनी हैं") == "leather footwear"
    assert "दिया" in glossary_correct("मैंने उसे दिया").text


@pytest.mark.parametrize("raw, transcript, want", [
    ("silver jewelry", "", "silver jewellery"),        # Gemini's US spelling, 6 Sep log
    ("leather sandals", "", "leather footwear"),
    ("copper pot", "", "copper vessel"),
    ("clay pottery", "", "clay pottery"),              # already a known category
    ("handmade craft", "यह मिट्टी का मटका है", "clay pottery"),
    ("wind chime", "", "wind chime"),                  # unknown: keep Gemini's words
])
def test_normalize_category(raw, transcript, want):
    assert normalize_category(raw, transcript, []) == want


@pytest.mark.parametrize("heard, category, materials", [
    # the three demo recordings as Whisper actually transcribed them (offline_check.py, 11 Sep)
    ("ये एक कले का बर्तन है", "clay pottery", ["clay"]),
    ("ये एक बांस का पतीला है", "", ["bamboo"]),       # no bamboo-vessel category: none, not a guess
    ("ये नीली मत्की है", "clay pottery", []),
    ("यह पीतल का पतीला है", "copper vessel", ["brass"]),
])
def test_demo_recordings_offline(heard, category, materials):
    d = describe(glossary_correct(heard).text, lang="hi", allow_gemini=False, use_cache=False)
    assert d.category == category
    assert d.materials == materials


def test_real_sandal_transcript_end_to_end_offline():
    d = describe(glossary_correct(REAL_SANDAL_TRANSCRIPT).text, lang="hi",
                 allow_gemini=False, use_cache=False)
    assert d.category == "leather footwear"
