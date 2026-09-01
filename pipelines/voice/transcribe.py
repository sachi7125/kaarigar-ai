"""Speech-to-text — mandated feature 2, step 1 (Roadmap Day 2).

A regional-language voice note -> text + a confidence the rest of the pipeline can
trust. Two backends, same return type:

  1. server (default when online): a whisper.cpp `server` HTTP endpoint. Set
     KAARIGAR_WHISPER_SERVER=http://host:port (whisper.cpp's ./server, OpenAI-ish
     /inference route). Fastest + most accurate; used when reachable.
  2. on-device fallback: faster-whisper (CTranslate2 whisper) running locally on
     CPU. Small/tiny models, int8 — the weak-hardware path and the offline path.

Both imports are lazy: nothing whisper-related is imported at module load (same
rule as the image pipeline's onnxruntime / the rembg lesson).

Confidence: mean of exp(avg_logprob) over segments (duration-weighted), knocked
down by no-speech probability. Below config `models.transcribe.min_confidence`
(0.55) the caller should ask for a re-record.

CLI:  python -m pipelines.voice.transcribe <audio_file> [lang]
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

from pipelines.common import cfg_get

# faster-whisper model cache (kept beside the image model cache).
_MODEL_DIR = Path(os.path.expanduser("~/.cache/kaarigar/whisper"))

# our language codes -> whisper's ISO-639-1 (whisper uses the same for these four).
_WHISPER_LANG = {"hi": "hi", "bn": "bn", "ta": "ta", "mr": "mr", "en": "en"}

# faster-whisper size names for the config's logical model ids.
_FW_SIZE = {
    "whisper-small": "small",
    "whisper-tiny-q": "tiny",
    "whisper-base": "base",
    "whisper-medium": "medium",
}

_MODEL_CACHE: dict[str, object] = {}


@dataclass
class Segment:
    start: float
    end: float
    text: str
    confidence: float          # 0..1, exp(avg_logprob)
    no_speech_prob: float


@dataclass
class TranscriptResult:
    text: str
    language: str              # detected (our code if known, else whisper's)
    language_prob: float
    confidence: float          # 0..1 overall
    needs_rerecord: bool       # confidence < min_confidence
    backend: str               # "server" | "faster-whisper" | "none"
    model: str
    duration: float
    segments: list[Segment] = field(default_factory=list)
    error: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def _min_confidence() -> float:
    return float(cfg_get("models.transcribe.min_confidence", 0.55))


def _overall_confidence(segments: list[Segment]) -> float:
    if not segments:
        return 0.0
    total = sum(max(s.end - s.start, 1e-3) for s in segments)
    conf = sum(s.confidence * (1.0 - s.no_speech_prob) * max(s.end - s.start, 1e-3)
               for s in segments) / total
    return float(max(0.0, min(1.0, conf)))


# --------------------------------------------------------------------------- #
# Backend 1: whisper.cpp server                                               #
# --------------------------------------------------------------------------- #
def _server_url() -> str | None:
    url = os.environ.get("KAARIGAR_WHISPER_SERVER", "").strip()
    return url.rstrip("/") or None


def _transcribe_server(audio: Path, lang: str | None) -> TranscriptResult:
    import requests  # lazy

    base = _server_url()
    data = {"response_format": "verbose_json", "temperature": "0.0"}
    if lang:
        data["language"] = _WHISPER_LANG.get(lang, lang)
    with open(audio, "rb") as fh:
        resp = requests.post(f"{base}/inference", files={"file": (audio.name, fh)},
                             data=data, timeout=120)
    resp.raise_for_status()
    body = resp.json()

    raw_segs = body.get("segments") or []
    segments: list[Segment] = []
    for s in raw_segs:
        alp = s.get("avg_logprob")
        conf = math.exp(alp) if isinstance(alp, (int, float)) else 0.6
        segments.append(Segment(
            start=float(s.get("start", 0.0)), end=float(s.get("end", 0.0)),
            text=(s.get("text") or "").strip(),
            confidence=float(max(0.0, min(1.0, conf))),
            no_speech_prob=float(s.get("no_speech_prob", 0.0)),
        ))
    text = (body.get("text") or " ".join(s.text for s in segments)).strip()
    detected = body.get("language") or lang or "hi"
    our_code = next((k for k, v in _WHISPER_LANG.items() if v == detected), detected)
    conf = _overall_confidence(segments) if segments else 0.6
    dur = segments[-1].end if segments else 0.0
    return TranscriptResult(
        text=text, language=our_code, language_prob=1.0, confidence=conf,
        needs_rerecord=conf < _min_confidence(), backend="server",
        model="whisper.cpp-server", duration=dur, segments=segments,
    )


# --------------------------------------------------------------------------- #
# Backend 2: faster-whisper (on-device / offline fallback)                     #
# --------------------------------------------------------------------------- #
def _load_fw(size: str):
    if size in _MODEL_CACHE:
        return _MODEL_CACHE[size]
    from faster_whisper import WhisperModel  # lazy — heavy import

    _MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model = WhisperModel(size, device="cpu", compute_type="int8",
                         download_root=str(_MODEL_DIR))
    _MODEL_CACHE[size] = model
    return model


def _transcribe_fw(audio: Path, lang: str | None, size: str) -> TranscriptResult:
    model = _load_fw(size)
    seg_iter, info = model.transcribe(
        str(audio),
        language=_WHISPER_LANG.get(lang) if lang else None,
        vad_filter=True,
        beam_size=5,
    )
    segments: list[Segment] = []
    for s in seg_iter:
        conf = math.exp(s.avg_logprob) if s.avg_logprob is not None else 0.6
        segments.append(Segment(
            start=float(s.start), end=float(s.end), text=s.text.strip(),
            confidence=float(max(0.0, min(1.0, conf))),
            no_speech_prob=float(getattr(s, "no_speech_prob", 0.0) or 0.0),
        ))
    text = " ".join(s.text for s in segments).strip()
    detected = info.language
    our_code = next((k for k, v in _WHISPER_LANG.items() if v == detected), detected)
    conf = _overall_confidence(segments)
    return TranscriptResult(
        text=text, language=our_code,
        language_prob=float(getattr(info, "language_probability", 0.0) or 0.0),
        confidence=conf, needs_rerecord=conf < _min_confidence(),
        backend="faster-whisper", model=f"faster-whisper/{size}",
        duration=float(getattr(info, "duration", segments[-1].end if segments else 0.0)),
        segments=segments,
    )


# --------------------------------------------------------------------------- #
# Public entry point                                                          #
# --------------------------------------------------------------------------- #
def transcribe(audio_path: str, lang: str | None = None,
               prefer_server: bool = True) -> TranscriptResult:
    """Transcribe a voice note.

    lang: one of hi/bn/ta/mr/en, or None to let whisper detect.
    prefer_server: try the whisper.cpp server first if configured; on any failure
    fall back to local faster-whisper. Set False to force on-device.
    """
    audio = Path(audio_path)
    if not audio.exists():
        return TranscriptResult(text="", language=lang or "", language_prob=0.0,
                                confidence=0.0, needs_rerecord=True, backend="none",
                                model="", duration=0.0,
                                error=f"audio not found: {audio}")

    server_cfg = _server_url()
    if prefer_server and server_cfg:
        try:
            return _transcribe_server(audio, lang)
        except Exception as e:  # server down / slow / bad response -> fall back
            fallback_note = f"server failed ({e.__class__.__name__}: {e}); used on-device"
        else:
            fallback_note = None
    else:
        fallback_note = None

    online = bool(server_cfg) and prefer_server
    size = _FW_SIZE.get(
        cfg_get("models.transcribe.server" if online else "models.transcribe.on_device"),
        "small" if online else "tiny",
    )
    try:
        res = _transcribe_fw(audio, lang, size)
    except Exception as e:
        return TranscriptResult(text="", language=lang or "", language_prob=0.0,
                                confidence=0.0, needs_rerecord=True, backend="none",
                                model=f"faster-whisper/{size}", duration=0.0,
                                error=f"{e.__class__.__name__}: {e}")
    if fallback_note:
        res.error = fallback_note
    return res


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python -m pipelines.voice.transcribe <audio_file> [lang]")
        raise SystemExit(2)
    lang_arg = sys.argv[2] if len(sys.argv) > 2 else None
    r = transcribe(sys.argv[1], lang=lang_arg)
    print(f"backend    : {r.backend}  ({r.model})")
    print(f"language   : {r.language}  (p={r.language_prob:.2f})")
    print(f"confidence : {r.confidence:.3f}   needs_rerecord={r.needs_rerecord}")
    if r.error:
        print(f"note       : {r.error}")
    print(f"duration   : {r.duration:.1f}s   segments={len(r.segments)}")
    print("-" * 60)
    print(r.text)
