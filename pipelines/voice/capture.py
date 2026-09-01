"""Low-confidence re-record loop — step 4 (Roadmap Day 2).

`transcribe()` returns `needs_rerecord=True` when its confidence falls below
`models.transcribe.min_confidence`. Something has to *act* on that, or a garbled
transcript walks straight into a published listing. This is that something.

The loop is deliberately I/O-free: it never opens a microphone. The caller (the
Flutter app, or a CLI harness) supplies a `recorder` callable:

    recorder(prompt_audio_path: str, attempt: int) -> str | None

It should play `prompt_audio_path` to the artisan, record her again, and return the
path of the new audio — or `None` to give up. The spoken prompt itself is synthesised
here with the shared Day-1 TTS, so the artisan is always *told* why she is being asked
again, in her own language.

With no `recorder`, `capture()` degrades to a single transcription plus the prompt
audio, so a caller can drive the retry itself.

CLI:  python -m pipelines.voice.capture <audio_file> [lang]
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Optional

from pipelines.common import cfg_get
from pipelines.voice import tts
from pipelines.voice.transcribe import transcribe, TranscriptResult

Recorder = Callable[[str, int], Optional[str]]

# Spoken re-record prompts, per input language. Kept short — she is being interrupted.
_PROMPT = {
    "hi": "आवाज़ साफ़ नहीं आई। कृपया दोबारा बोलिए।",
    "bn": "আওয়াজ পরিষ্কার শোনা যায়নি। আবার বলুন।",
    "ta": "குரல் தெளிவாக இல்லை. மீண்டும் சொல்லுங்கள்.",
    "mr": "आवाज स्पष्ट आला नाही. कृपया पुन्हा बोला.",
    "en": "I could not hear that clearly. Please say it again.",
}
_PROMPT_DIR = Path("results/prompts")


@dataclass
class CaptureResult:
    transcript: TranscriptResult          # the best attempt we got
    attempts: int                         # transcriptions run (1 = no retry needed)
    still_low: bool                       # exhausted retries and confidence is still low
    prompt_audio: str | None = None       # spoken "say it again", if one was produced
    audio_used: str = ""                  # path of the audio the transcript came from
    history: list[float] = field(default_factory=list)   # confidence per attempt

    def as_dict(self) -> dict:
        d = asdict(self)
        d["transcript"] = self.transcript.as_dict()
        return d


def rerecord_prompt_text(lang: str | None) -> str:
    return _PROMPT.get((lang or "hi").lower(), _PROMPT["en"])


def _prompt_audio(lang: str | None) -> str | None:
    """Synthesise the 'say it again' prompt. Returns None if TTS is unavailable."""
    code = (lang or "hi").lower()
    out = _PROMPT_DIR / f"rerecord_{code}.aiff"
    if out.exists() and out.stat().st_size > 0:
        return str(out)
    try:
        return tts.speak_to_file(rerecord_prompt_text(code), str(out), lang=code)
    except Exception:
        return None


def capture(audio_path: str, lang: str | None = None, recorder: Recorder | None = None,
            max_retries: int | None = None, prefer_server: bool = True) -> CaptureResult:
    """Transcribe, and re-record while confidence is too low.

    Keeps the BEST attempt, not the last — a retry can come out worse (she may
    speak louder and clip the mic), and we should never hand back a worse transcript
    than we already had.
    """
    if max_retries is None:
        max_retries = int(cfg_get("models.transcribe.max_rerecords", 2))

    current = audio_path
    best = transcribe(current, lang=lang, prefer_server=prefer_server)
    best_audio = current
    history = [best.confidence]
    attempts = 1
    prompt_path: str | None = None

    while best.needs_rerecord and attempts <= max_retries:
        prompt_path = _prompt_audio(lang or best.language)
        if recorder is None:
            break                                  # caller drives the retry itself
        nxt = recorder(prompt_path or "", attempts)
        if not nxt:
            break                                  # she declined / no more audio
        attempts += 1
        res = transcribe(nxt, lang=lang, prefer_server=prefer_server)
        history.append(res.confidence)
        if res.confidence > best.confidence:
            best, best_audio = res, nxt

    return CaptureResult(
        transcript=best, attempts=attempts, still_low=best.needs_rerecord,
        prompt_audio=prompt_path, audio_used=best_audio, history=history,
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python -m pipelines.voice.capture <audio_file> [lang]")
        raise SystemExit(2)
    lang_arg = sys.argv[2] if len(sys.argv) > 2 else None
    r = capture(sys.argv[1], lang=lang_arg)
    t = r.transcript
    print(f"attempts   : {r.attempts}   still_low={r.still_low}")
    print(f"confidence : {t.confidence:.3f}   (history: {[round(c,3) for c in r.history]})")
    if r.prompt_audio:
        print(f"re-record prompt spoken to: {r.prompt_audio}")
        print(f"  \"{rerecord_prompt_text(lang_arg or t.language)}\"")
    print("-" * 60)
    print(t.text)
