"""Unit tests for vision size/finish suggestion + voice material extraction +
attribute-only spoken confirmation (no real audio/camera needed)."""
from __future__ import annotations

import numpy as np

import pipelines.pricing.attributes as attrs
from pipelines.voice.transcribe import TranscriptResult


# --------------------------------------------------------------------- vision
def test_size_class_buckets():
    assert attrs.suggest_size_class(0.05) == "small"
    assert attrs.suggest_size_class(0.14) == "small"
    assert attrs.suggest_size_class(0.15) == "medium"
    assert attrs.suggest_size_class(0.30) == "medium"
    assert attrs.suggest_size_class(0.45) == "large"
    assert attrs.suggest_size_class(0.90) == "large"


def test_finish_glossy_vs_matte():
    # matte: uniform mid-brightness inside the mask
    matte = np.full((100, 100, 3), 140, dtype=np.uint8)
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[20:80, 20:80] = 255
    assert attrs.suggest_finish(matte, mask) == "matte"

    # glossy: uniform base + a sharp bright specular patch inside the mask
    glossy = matte.copy()
    glossy[40:50, 40:50] = 255
    assert attrs.suggest_finish(glossy, mask) == "glossy"


def test_finish_unknown_when_mask_empty():
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    mask = np.zeros((100, 100), dtype=np.uint8)
    assert attrs.suggest_finish(img, mask) == "unknown"


# --------------------------------------------------------------------- voice
def test_extract_material_latin():
    assert attrs.extract_material("this is a copper bartan") == "copper"
    assert attrs.extract_material("handmade brass idol") == "brass"


def test_extract_material_devanagari():
    assert attrs.extract_material("ये एक पीतल का बर्तन है") == "brass"
    assert attrs.extract_material("यह चांदी की अंगूठी है") == "silver"


def test_extract_material_none_found():
    assert attrs.extract_material("यह बहुत सुंदर है") == ""
    assert attrs.extract_material("") == ""


# ------------------------------------------------------------- confirm loop
def _patch(monkeypatch, answers):
    seq = list(answers)
    monkeypatch.setattr(attrs.tts, "speak_to_file", lambda *a, **k: "/tmp/attr.aiff")
    monkeypatch.setattr(attrs, "transcribe", lambda p, **k: TranscriptResult(
        text=seq.pop(0), language="hi", language_prob=1.0, confidence=0.9,
        needs_rerecord=False, backend="stub", model="stub", duration=1.0))


def test_no_recorder_returns_unconfirmed_suggestions(monkeypatch):
    monkeypatch.setattr(attrs, "_vision_suggestions", lambda p: ("medium", 0.30, "matte"))
    r = attrs.suggest_attributes("fake.png", "ये एक पीतल का बर्तन है", "hi", recorder=None)
    assert r.material == "brass" and r.material_source == "voice"
    assert r.size_class == "medium"
    assert r.size_score == 0.30
    assert r.questions_asked == []


def test_size_score_survives_size_confirmation(monkeypatch):
    monkeypatch.setattr(attrs, "_vision_suggestions", lambda p: ("medium", 0.30, "matte"))
    _patch(monkeypatch, ["हाँ", "हाँ"])
    r = attrs.suggest_attributes("fake.png", "ये एक पीतल का बर्तन है", "hi",
                                 recorder=lambda p, n: "ans.m4a")
    assert r.size_score == 0.30


def test_size_score_cleared_alongside_a_rejected_size(monkeypatch):
    monkeypatch.setattr(attrs, "_vision_suggestions", lambda p: ("medium", 0.30, "matte"))
    _patch(monkeypatch, ["हाँ", "नहीं"])
    r = attrs.suggest_attributes("fake.png", "ये एक पीतल का बर्तन है", "hi",
                                 recorder=lambda p, n: "ans.m4a")
    assert r.size_class == "" and r.size_score is None


def test_size_bounds_and_representative_points_are_consistent():
    for size_class, (lo, hi) in attrs.SIZE_BOUNDS.items():
        rep = attrs.SIZE_REPRESENTATIVE[size_class]
        assert lo <= rep <= hi


def test_confirm_yes_keeps_both(monkeypatch):
    monkeypatch.setattr(attrs, "_vision_suggestions", lambda p: ("medium", 0.30, "matte"))
    _patch(monkeypatch, ["हाँ", "हाँ"])
    r = attrs.suggest_attributes("fake.png", "ये एक पीतल का बर्तन है", "hi",
                                 recorder=lambda p, n: "ans.m4a")
    assert r.material == "brass" and r.material_source == "confirmed"
    assert r.size_class == "medium" and r.size_source == "confirmed"
    assert len(r.questions_asked) == 2


def test_confirm_no_clears_the_field_never_reguesses(monkeypatch):
    monkeypatch.setattr(attrs, "_vision_suggestions", lambda p: ("medium", 0.30, "matte"))
    _patch(monkeypatch, ["नहीं", "नहीं"])
    r = attrs.suggest_attributes("fake.png", "ये एक पीतल का बर्तन है", "hi",
                                 recorder=lambda p, n: "ans.m4a")
    assert r.material == "" and r.material_source == "unconfirmed"
    assert r.size_class == "" and r.size_source == "unconfirmed"


def test_no_material_in_transcript_skips_that_question(monkeypatch):
    monkeypatch.setattr(attrs, "_vision_suggestions", lambda p: ("small", 0.08, "glossy"))
    _patch(monkeypatch, ["हाँ"])   # only ONE answer needed: size only
    r = attrs.suggest_attributes("fake.png", "यह बहुत सुंदर है", "hi",
                                 recorder=lambda p, n: "ans.m4a")
    assert r.material == "" and r.material_source == "none"
    assert len(r.questions_asked) == 1
    assert r.size_class == "small" and r.size_source == "confirmed"


def test_never_asks_about_price_or_cost(monkeypatch):
    monkeypatch.setattr(attrs, "_vision_suggestions", lambda p: ("medium", 0.30, "matte"))
    _patch(monkeypatch, ["हाँ", "हाँ"])
    r = attrs.suggest_attributes("fake.png", "ये एक पीतल का बर्तन है, कीमत चार सौ रुपये", "hi",
                                 recorder=lambda p, n: "ans.m4a")
    for q in r.questions_asked:
        assert "कीमत" not in q and "रुपये" not in q and "price" not in q.lower()
