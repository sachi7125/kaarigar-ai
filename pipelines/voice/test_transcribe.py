"""Unit tests for transcription helpers that don't need a whisper model."""
from __future__ import annotations

from pipelines.voice.transcribe import (
    Segment, TranscriptResult, _overall_confidence, transcribe,
)


def _seg(start, end, conf, no_speech=0.0):
    return Segment(start=start, end=end, text="x", confidence=conf,
                   no_speech_prob=no_speech)


def test_overall_confidence_empty():
    assert _overall_confidence([]) == 0.0


def test_overall_confidence_duration_weighted():
    segs = [_seg(0, 1, 0.9), _seg(1, 10, 0.5)]  # long low-conf segment dominates
    c = _overall_confidence(segs)
    assert 0.5 <= c < 0.6


def test_overall_confidence_penalised_by_no_speech():
    clean = _overall_confidence([_seg(0, 2, 0.8, no_speech=0.0)])
    noisy = _overall_confidence([_seg(0, 2, 0.8, no_speech=0.7)])
    assert noisy < clean


def test_missing_audio_returns_rerecord():
    r = transcribe("does/not/exist.wav")
    assert isinstance(r, TranscriptResult)
    assert r.backend == "none"
    assert r.needs_rerecord is True
    assert r.error and "not found" in r.error


def test_as_dict_roundtrips():
    r = TranscriptResult(text="hi", language="hi", language_prob=0.9,
                         confidence=0.8, needs_rerecord=False, backend="server",
                         model="m", duration=1.0)
    d = r.as_dict()
    assert d["text"] == "hi" and d["segments"] == []
