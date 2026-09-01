"""Unit tests for the re-record loop (transcribe + tts are stubbed out)."""
from __future__ import annotations

import pipelines.voice.capture as cap
from pipelines.voice.transcribe import TranscriptResult


def _tr(conf: float, text: str = "x") -> TranscriptResult:
    return TranscriptResult(text=text, language="hi", language_prob=1.0,
                            confidence=conf, needs_rerecord=conf < 0.55,
                            backend="stub", model="stub", duration=1.0)


def _patch(monkeypatch, results):
    """Feed `results` to successive transcribe() calls; stub TTS to a fake path."""
    seq = list(results)
    monkeypatch.setattr(cap, "transcribe", lambda p, **k: seq.pop(0))
    monkeypatch.setattr(cap, "_prompt_audio", lambda lang: "/tmp/prompt.aiff")


def test_good_first_take_no_retry(monkeypatch):
    _patch(monkeypatch, [_tr(0.80)])
    r = cap.capture("a.m4a", lang="hi", recorder=lambda p, n: "never.m4a")
    assert r.attempts == 1 and r.still_low is False
    assert r.prompt_audio is None


def test_retries_until_confident(monkeypatch):
    _patch(monkeypatch, [_tr(0.30), _tr(0.72, "good")])
    r = cap.capture("a.m4a", lang="hi", recorder=lambda p, n: "b.m4a")
    assert r.attempts == 2 and r.still_low is False
    assert r.transcript.text == "good" and r.audio_used == "b.m4a"


def test_keeps_best_not_last(monkeypatch):
    # retry came out WORSE — we must not hand back the worse transcript
    _patch(monkeypatch, [_tr(0.50, "first"), _tr(0.20, "worse")])
    r = cap.capture("a.m4a", lang="hi", recorder=lambda p, n: "b.m4a", max_retries=1)
    assert r.transcript.text == "first"
    assert r.audio_used == "a.m4a"
    assert r.still_low is True


def test_respects_max_retries(monkeypatch):
    _patch(monkeypatch, [_tr(0.1), _tr(0.1), _tr(0.1)])
    r = cap.capture("a.m4a", lang="hi", recorder=lambda p, n: "b.m4a", max_retries=2)
    assert r.attempts == 3 and r.still_low is True
    assert r.history == [0.1, 0.1, 0.1]


def test_recorder_declining_stops_loop(monkeypatch):
    _patch(monkeypatch, [_tr(0.2)])
    r = cap.capture("a.m4a", lang="hi", recorder=lambda p, n: None)
    assert r.attempts == 1 and r.still_low is True


def test_no_recorder_returns_prompt_for_caller(monkeypatch):
    _patch(monkeypatch, [_tr(0.2)])
    r = cap.capture("a.m4a", lang="hi", recorder=None)
    assert r.attempts == 1 and r.still_low is True
    assert r.prompt_audio == "/tmp/prompt.aiff"


def test_prompt_text_per_language():
    assert "दोबारा" in cap.rerecord_prompt_text("hi")
    assert cap.rerecord_prompt_text("zz") == cap.rerecord_prompt_text("en")
