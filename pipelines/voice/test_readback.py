"""Unit tests for the spoken read-back + voice confirmation (no audio needed)."""
from __future__ import annotations

import pipelines.voice.readback as rb
from pipelines.voice.glossary import Correction
from pipelines.voice.pii_strip import Redaction
from pipelines.voice.transcribe import TranscriptResult


# ---------------------------------------------------------------- build_script
def test_script_reads_back_her_own_words():
    s = rb.build_script("ये एक मिट्टी का बर्तन है", "hi")
    assert "ये एक मिट्टी का बर्तन है" in s
    assert "मैंने यह सुना" in s
    assert "हाँ या नहीं" in s          # always ends by asking


def test_script_announces_glossary_corrections():
    s = rb.build_script("ये बर्तन है", "hi",
                        corrections=[Correction("बर्दन", "बर्तन", "exact", 1.0)])
    assert "बर्दन" in s and "बर्तन" in s


def test_script_announces_pii_removal():
    s = rb.build_script("नंबर [removed]", "hi",
                        redactions=[Redaction("9876543210", "phone", 10)])
    assert "फ़ोन नंबर" in s and "हटा" in s


def test_script_echoes_extracted_facts_and_price():
    s = rb.build_script("मटकी कीमत 400", "hi", category="clay pottery",
                        materials=["clay"])
    assert "clay pottery" in s and "400" in s


def test_script_uses_her_language_not_english():
    ta = rb.build_script("இது ஒரு களிமண் பானை", "ta")
    assert "நான் இதைக் கேட்டேன்" in ta
    assert "I heard" not in ta


def test_generated_hindi_title_only_read_for_hindi_speakers():
    with_hi = rb.build_script("x", "hi", title="हाथ से बना बर्तन")
    with_ta = rb.build_script("x", "ta", title="हाथ से बना बर्तन")
    assert "हाथ से बना बर्तन" in with_hi
    assert "हाथ से बना बर्तन" not in with_ta


def test_unknown_language_falls_back_to_english():
    assert "I heard" in rb.build_script("a pot", "zz")


# ------------------------------------------------------------ classify_answer
def test_yes_and_no_in_each_language():
    assert rb.classify_answer("हाँ", "hi") is True
    assert rb.classify_answer("नहीं", "hi") is False
    assert rb.classify_answer("হ্যাঁ", "bn") is True
    assert rb.classify_answer("இல்லை", "ta") is False
    assert rb.classify_answer("होय", "mr") is True
    assert rb.classify_answer("yes", "en") is True


def test_romanised_answers_work():
    assert rb.classify_answer("haan ji", "hi") is True
    assert rb.classify_answer("nahi", "hi") is False


def test_answer_inside_a_sentence():
    assert rb.classify_answer("हाँ यह सही है", "hi") is True


def test_unrelated_answer_is_none():
    assert rb.classify_answer("मटकी नीली है", "hi") is None
    assert rb.classify_answer("", "hi") is None


# ------------------------------------------------------ readback_and_confirm
def _patch(monkeypatch, answers):
    seq = list(answers)
    monkeypatch.setattr(rb, "speak_readback", lambda *a, **k: "/tmp/rb.aiff")
    monkeypatch.setattr(rb, "transcribe", lambda p, **k: TranscriptResult(
        text=seq.pop(0), language="hi", language_prob=1.0, confidence=0.9,
        needs_rerecord=False, backend="stub", model="stub", duration=1.0))


def test_spoken_yes_allows_publish(monkeypatch):
    _patch(monkeypatch, ["हाँ"])
    r = rb.readback_and_confirm("x", "hi", recorder=lambda p, n: "ans.m4a")
    assert r.confirmed is True and r.may_publish is True


def test_spoken_no_blocks_publish(monkeypatch):
    _patch(monkeypatch, ["नहीं"])
    r = rb.readback_and_confirm("x", "hi", recorder=lambda p, n: "ans.m4a")
    assert r.confirmed is False and r.may_publish is False


def test_unclear_then_yes(monkeypatch):
    _patch(monkeypatch, ["मटकी", "हाँ"])
    r = rb.readback_and_confirm("x", "hi", recorder=lambda p, n: "ans.m4a")
    assert r.attempts == 2 and r.may_publish is True


def test_exhausted_attempts_never_publishes(monkeypatch):
    _patch(monkeypatch, ["मटकी", "नीली"])
    r = rb.readback_and_confirm("x", "hi", recorder=lambda p, n: "ans.m4a",
                                max_attempts=2)
    assert r.confirmed is None and r.still_unclear is True
    assert r.may_publish is False


def test_no_answer_never_publishes(monkeypatch):
    _patch(monkeypatch, [])
    r = rb.readback_and_confirm("x", "hi", recorder=lambda p, n: None)
    assert r.may_publish is False


def test_no_recorder_returns_script_for_caller(monkeypatch):
    _patch(monkeypatch, [])
    r = rb.readback_and_confirm("x", "hi", recorder=None)
    assert r.script and r.audio_path == "/tmp/rb.aiff"
    assert r.may_publish is False          # silence is never consent
