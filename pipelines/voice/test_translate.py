"""Unit tests for translation helpers that don't need the IndicTrans2 model."""
from __future__ import annotations

from pipelines.voice.translate import TranslationResult, translate


def test_english_passes_through():
    r = translate("A blue clay pot, handmade.", "en")
    assert r.translated is False
    assert r.backend == "passthrough"
    assert r.text == "A blue clay pot, handmade."


def test_empty_input():
    r = translate("   ", "hi")
    assert r.translated is False
    assert r.text == ""


def test_unknown_language_carried_through_with_note():
    r = translate("bonjour", "fr")
    assert r.translated is False
    assert r.error and "unknown source language" in r.error
    assert r.text == "bonjour"


def test_regional_text_passes_through_by_default():
    # Default (no KAARIGAR_MT): translation is deferred to the Gemini step.
    r = translate("यह नीली मिट्टी की मटकी है", "hi")
    assert isinstance(r, TranslationResult)
    assert r.translated is False
    assert r.backend == "passthrough"
    assert r.text == "यह नीली मिट्टी की मटकी है"
    assert r.source_lang == "hi"
    assert r.error and "Gemini" in r.error


def test_as_dict_roundtrips():
    r = translate("test", "en")
    d = r.as_dict()
    assert d["text"] == "test" and d["translated"] is False
