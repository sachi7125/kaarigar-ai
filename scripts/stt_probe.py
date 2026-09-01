"""STT diagnostic — find out why transcription is bad on a real voice note.

Runs one audio file through several faster-whisper model sizes and decode settings
and prints a comparison table (detected language, confidence, no-speech, the text).
Use this to pick the on-device model + settings from evidence, not guesswork.

Usage:
    python -m scripts.stt_probe <audio_file> [lang]
    python -m scripts.stt_probe recordings/hindi_note.m4a hi

Notes:
- Downloads each model on first use (tiny ~75MB, base ~145MB, small ~465MB) to
  ~/.cache/kaarigar/whisper/. Slow once, then cached.
- `lang` is optional; omit it to also see whether language detection is the problem.
- Prints audio metadata first (duration, sample rate, channels) — a too-quiet, too-
  short, or wrongly-decoded file is a common cause and shows up here.
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

WHISPER_LANG = {"hi": "hi", "bn": "bn", "ta": "ta", "mr": "mr", "en": "en"}

# (label, model_size, kwargs) — kwargs passed straight to WhisperModel.transcribe
TRIALS = [
    ("tiny  / vad+beam5",  "tiny",  dict(vad_filter=True,  beam_size=5)),
    ("base  / vad+beam5",  "base",  dict(vad_filter=True,  beam_size=5)),
    ("base  / NO-vad",     "base",  dict(vad_filter=False, beam_size=5)),
    ("small / vad+beam5",  "small", dict(vad_filter=True,  beam_size=5)),
    ("small / NO-vad + noprev", "small",
     dict(vad_filter=False, beam_size=5, condition_on_previous_text=False)),
]


def _audio_info(path: str) -> None:
    try:
        import av  # faster-whisper's decoder

        with av.open(path) as c:
            st = next(s for s in c.streams if s.type == "audio")
            dur = float(c.duration) / 1_000_000 if c.duration else None
            print(f"  codec={st.codec_context.name} rate={st.codec_context.sample_rate}Hz "
                  f"channels={st.codec_context.channels} "
                  f"duration={dur:.1f}s" if dur else "duration=?")
    except Exception as e:
        print(f"  (could not read audio metadata: {e.__class__.__name__}: {e})")


def _run(model, audio: str, lang: str | None, kwargs: dict):
    seg_iter, info = model.transcribe(
        audio, language=WHISPER_LANG.get(lang) if lang else None, **kwargs)
    segs = list(seg_iter)
    if not segs:
        return info, "", 0.0, 1.0
    total = sum(max(s.end - s.start, 1e-3) for s in segs)
    conf = sum(math.exp(s.avg_logprob) * (1 - (s.no_speech_prob or 0.0))
               * max(s.end - s.start, 1e-3) for s in segs) / total
    nsp = sum((s.no_speech_prob or 0.0) for s in segs) / len(segs)
    text = " ".join(s.text.strip() for s in segs).strip()
    return info, text, max(0.0, min(1.0, conf)), nsp


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m scripts.stt_probe <audio_file> [lang]")
        return 2
    audio = sys.argv[1]
    lang = sys.argv[2] if len(sys.argv) > 2 else None
    if not Path(audio).exists():
        print(f"not found: {audio}")
        return 2

    print(f"\nAUDIO: {audio}   (lang hint: {lang or 'auto-detect'})")
    _audio_info(audio)

    from faster_whisper import WhisperModel

    cache: dict[str, WhisperModel] = {}
    print(f"\n{'trial':<26} {'det-lang':<10} {'conf':>6} {'nosp':>6}  text")
    print("-" * 100)
    for label, size, kwargs in TRIALS:
        if size not in cache:
            print(f"[loading {size} ...]", flush=True)
            cache[size] = WhisperModel(size, device="cpu", compute_type="int8",
                                       download_root=str(Path("~/.cache/kaarigar/whisper").expanduser()))
        t0 = time.time()
        try:
            info, text, conf, nsp = _run(cache[size], audio, lang, kwargs)
        except Exception as e:
            print(f"{label:<26} ERROR {e.__class__.__name__}: {e}")
            continue
        dl = f"{info.language}/{info.language_probability:.2f}"
        show = (text[:70] + "…") if len(text) > 71 else text
        print(f"{label:<26} {dl:<10} {conf:>6.3f} {nsp:>6.3f}  {show}   ({time.time()-t0:.1f}s)")

    print("\nPick the smallest model whose text is actually correct and conf is comfortably")
    print("above the 0.55 gate. Then set config.yaml models.transcribe.on_device accordingly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
