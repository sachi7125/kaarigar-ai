"""Unit tests for the PII digit-run stripper."""
from __future__ import annotations

from pipelines.voice.pii_strip import strip_pii


def test_strips_bare_mobile():
    r = strip_pii("call karo 9876543210 par")
    assert "9876543210" not in r.text
    assert r.changed and r.redactions[0].kind == "phone"


def test_strips_spaced_mobile_and_aadhaar():
    r = strip_pii("+91 98765 43210 aur 1234 5678 9012")
    assert "98765" not in r.text and "5678" not in r.text
    assert len(r.redactions) == 2


def test_keeps_price_and_dimensions():
    r = strip_pii("400 rupaye, 12 inch, 6 diye")
    assert r.text == "400 rupaye, 12 inch, 6 diye"
    assert not r.changed


def test_keeps_year():
    assert strip_pii("2024 se bana rahi hoon").changed is False


def test_devanagari_digits_stripped():
    r = strip_pii("नंबर ९८७६५४३२१० है")
    assert "९८७६५४३२१०" not in r.text and r.changed


def test_no_double_space_left_behind():
    r = strip_pii("number +91 98765 43210 hai")
    assert "  " not in r.text
    assert r.text.endswith("hai")


def test_threshold_is_configurable():
    assert strip_pii("123456", min_digits=7).changed is False
    assert strip_pii("123456", min_digits=6).changed is True


def test_empty_input():
    assert strip_pii("").text == ""
