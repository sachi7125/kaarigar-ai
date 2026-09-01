"""Unit tests for the craft-vocabulary fuzzy-correct."""
from __future__ import annotations

from pipelines.voice.glossary import correct, terms


def test_exact_variant_latin():
    r = correct("ye ek dokra murti hai")
    assert "dhokra" in r.text
    assert any(c.original == "dokra" and c.corrected == "dhokra" for c in r.corrections)


def test_exact_variant_devanagari():
    r = correct("ये एक क्ले का बर्दन है")
    assert "बर्तन" in r.text and "बर्दन" not in r.text


def test_devanagari_matras_survive_tokenising():
    # `\w` drops matras/virama; a naive tokeniser shredded "मिट्टी" into pieces
    r = correct("मिट्टी की मटकी")
    assert r.text == "मिट्टी की मटकी"
    assert r.corrections == []


def test_fuzzy_match_near_miss():
    r = correct("bandhanee dupatta")
    assert "bandhani" in r.text


def test_script_never_switches():
    r = correct("ये बर्दन है")
    assert all(not c.corrected.isascii() for c in r.corrections)


def test_short_tokens_and_digits_untouched():
    r = correct("400 ka hai ye")
    assert r.text == "400 ka hai ye"
    assert r.corrections == []


def test_unknown_words_left_alone():
    r = correct("this is a completely unrelated sentence")
    assert r.text == "this is a completely unrelated sentence"


def test_empty_input():
    assert correct("").text == ""


def test_terms_loads_glossary():
    t = terms()
    assert "dhokra" in t and "बर्तन" in t
