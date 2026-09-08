"""Day 2 smoke test — steps 1-5: transcribe -> glossary -> PII -> listing -> read-back.

Round-trips through the shared TTS: synthesise a known Hindi sentence to audio,
then run it back through `transcribe()`, `glossary.correct()`, `pii_strip()`,
`translate()` (passthrough, D11), and `describe()` (Gemini bilingual listing, or
the offline template if no API key).
Proves the pipeline end to end without needing a real recording or a server.

Run:  python -m scripts.day2_smoke
(First run downloads the whisper model to ~/.cache/kaarigar/whisper/ — slow once.
 Needs GEMINI_API_KEY in .env for the real listing; falls back to a template.)
"""
from __future__ import annotations

from pathlib import Path

from pipelines.voice import tts
from pipelines.voice.transcribe import transcribe
from pipelines.voice.translate import translate
from pipelines.voice.describe import describe
from pipelines.voice.glossary import correct as glossary_correct
from pipelines.voice.pii_strip import strip_pii
from pipelines.voice.readback import readback_and_confirm, classify_answer

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

    g = glossary_correct(r.text or SENTENCE)
    print(f"\n[gloss] {len(g.corrections)} correction(s)")
    for c in g.corrections:
        print(f"[gloss]   {c.original!r} -> {c.corrected!r} ({c.how})")
    p = strip_pii(g.text)
    if p.changed:
        for red in p.redactions:
            print(f"[pii] removed {red.kind}: {red.original!r}")
    print(f"[pii] clean: {p.text!r}")

    tr = translate(p.text or SENTENCE, r.language or "hi")
    print(f"\n[mt] backend={tr.backend} model={tr.model or '-'} translated={tr.translated}")
    if tr.error:
        print(f"[mt] note: {tr.error}")
    print(f"[mt] english: {tr.text!r}")

    d = describe(p.text or SENTENCE, lang=r.language or "hi",
                 attributes={"category": "clay pottery", "materials": ["clay"]})
    print(f"\n[desc] source={d.source}")
    if d.error:
        print(f"[desc] note: {d.error}")
    print(f"[desc] EN title: {d.title_en!r}")
    print(f"[desc] HI title: {d.title_hi!r}")
    print(f"[desc] EN desc : {d.description_en!r}")
    print(f"[desc] HI desc : {d.description_hi!r}")
    print(f"[desc] keywords: {', '.join(d.seo_keywords)}")

    rb = readback_and_confirm(p.text, lang=r.language or "hi",
                              corrections=g.corrections, redactions=p.redactions,
                              category=d.category, materials=d.materials,
                              title=d.title_hi)
    print(f"\n[readback] script: {rb.script}")
    print(f"[readback] audio : {rb.audio_path or '(TTS unavailable)'}")
    if rb.error:
        print(f"[readback] note  : {rb.error}")
    # no mic in a smoke test: simulate the artisan saying yes, then check the gate
    print(f"[readback] simulated answer 'haan ji' -> "
          f"{classify_answer('haan ji', r.language or 'hi')}")
    print(f"[readback] may_publish now = {rb.may_publish} (no real voice answer yet)")

    ok = bool(r.text.strip()) and r.confidence > 0.0 and r.backend != "none"
    desc_ok = bool(d.title_en and d.title_hi and d.description_en and d.description_hi)
    print(f"\nDay 2 step-1 (transcription) gate: {'PASS' if ok else 'FAIL'}")
    print(f"Day 2 step-2 (translation): "
          f"{'translated (KAARIGAR_MT)' if tr.translated else 'passthrough — Gemini does MT in step 3 (D11)'}")
    print(f"Day 2 step-3 (bilingual listing): "
          f"{'OK' if desc_ok else 'FAIL'} (source={d.source})")
    rb_ok = bool(rb.script) and rb.audio_path is not None
    print(f"Day 2 step-4 (glossary + PII): {len(g.corrections)} correction(s), "
          f"{len(p.redactions)} redaction(s)")
    print(f"Day 2 step-5 (spoken read-back): {'OK' if rb_ok else 'FAIL'} "
          f"— publish gated on a spoken yes")
    return 0 if (ok and desc_ok and rb_ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
