"""Day 2 smoke test — steps 1-2: transcription + translation.

Round-trips through the shared TTS: synthesise a known Hindi sentence to audio,
then run it back through `transcribe()` (non-empty text + usable confidence) and
`translate()` (Hindi -> English pivot). Proves the on-device path end to end
without needing a real recording or a server.

Translation is a passthrough by design (Gemini does the real MT in step 3, see
D11) — the [mt] line just shows the transcript flowing through with its language.

Run:  python -m scripts.day2_smoke
(First run downloads the whisper model to ~/.cache/kaarigar/whisper/ — slow once.)
"""
from __future__ import annotations

from pathlib import Path

from pipelines.voice import tts
from pipelines.voice.transcribe import transcribe
from pipelines.voice.translate import translate

OUT = Path("results/day2")
OUT.mkdir(parents=True, exist_ok=True)

SENTENCE = "Yeh haath se bani neeli mitti ki matki hai. Iski keemat char sau rupaye."


def main() -> int:
    audio = OUT / "sample_hi.aiff"
    try:
        tts.speak_to_file(SENTENCE, str(audio), lang="hi")
    except tts.TTSUnavailable as e:
        print(f"[tts] unavailable, cannot build a sample: {e}")
        return 1
    print(f"[tts] wrote {audio} ({audio.stat().st_size} bytes)")

    r = transcribe(str(audio), lang="hi", prefer_server=False)
    print(f"[stt] backend={r.backend} model={r.model}")
    print(f"[stt] language={r.language} p={r.language_prob:.2f} "
          f"confidence={r.confidence:.3f} needs_rerecord={r.needs_rerecord}")
    if r.error:
        print(f"[stt] note: {r.error}")
    print(f"[stt] text: {r.text!r}")

    tr = translate(r.text or SENTENCE, r.language or "hi")
    print(f"\n[mt] backend={tr.backend} model={tr.model or '-'} translated={tr.translated}")
    if tr.error:
        print(f"[mt] note: {tr.error}")
    print(f"[mt] english: {tr.text!r}")

    ok = bool(r.text.strip()) and r.confidence > 0.0 and r.backend != "none"
    print(f"\nDay 2 step-1 (transcription) gate: {'PASS' if ok else 'FAIL'}")
    print(f"Day 2 step-2 (translation): "
          f"{'translated (KAARIGAR_MT)' if tr.translated else 'passthrough — Gemini does MT in step 3 (D11)'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
