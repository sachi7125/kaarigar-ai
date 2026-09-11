"""Day 7 offline readiness check, and the pre-cache step.

    .venv/bin/python scripts/offline_check.py              check only; the speech model is
                                                            loaded with the Hugging Face hub
                                                            forced offline
    .venv/bin/python scripts/offline_check.py --precache   also send each demo recording's
                                                            transcript to Gemini once and
                                                            cache the listing (needs internet)

"Offline" for the demo means: the Mac serves everything over its own Wi-Fi or
hotspot (scripts/run_server.sh lan), the artisan's phone and the buyer's phone
talk only to it, and nothing reaches the internet. So every model the server
uses must already be on disk, and every step that normally calls Gemini needs
a usable offline answer.

What the pre-cache can and can't do: describe()'s cache is keyed by the exact
transcript, so it serves a replay of the same recording (these files, the
playground) — not a fresh live recording of the same words, which transcribes
slightly differently. A live take offline goes through the template listing,
which is why this script also shows what the template makes of each demo item.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(REPO), str(REPO / "backend")]

OK, FAIL = "✓", "✗"


def _line(ok: bool, label: str, detail: str = "") -> bool:
    print(f"  {OK if ok else FAIL} {label}" + (f" — {detail}" if detail else ""))
    return ok


def check_assets() -> bool:
    from pipelines.common import cfg_get
    from pipelines.image import enhance
    from pipelines.voice import transcribe as tr

    print("Models and files on disk")
    size = tr._FW_SIZE.get(cfg_get("models.transcribe.on_device"), "tiny")
    whisper_dir = tr._MODEL_DIR / f"models--Systran--faster-whisper-{size}"
    results = [
        _line(whisper_dir.is_dir(), f"speech model (faster-whisper {size})", str(whisper_dir)),
        _line(enhance._MODEL_PATH.is_file(), "background-removal model (u2netp)", str(enhance._MODEL_PATH)),
        _line((REPO / "ml" / "models" / "pricing_xgb.json").is_file(), "pricing model", "ml/models/pricing_xgb.json"),
    ]
    from app.api.listings import _DEVANAGARI_FONT_CANDIDATES
    font = next((p for p in _DEVANAGARI_FONT_CANDIDATES if Path(p).is_file()), None)
    results.append(_line(font is not None, "Devanagari font for share cards", font or "none found — cards fall back to English only"))
    ip = subprocess.run(["ipconfig", "getifaddr", "en0"], capture_output=True, text=True).stdout.strip()
    results.append(_line(bool(ip), "Wi-Fi address for QR codes", f"http://{ip}:8000" if ip else "not on Wi-Fi/hotspot"))
    return all(results)


def check_demo_items(audio_files: list[Path], precache: bool) -> bool:
    from pipelines.voice.describe import describe
    from pipelines.voice.glossary import correct as glossary_correct
    from pipelines.voice.pii_strip import strip_pii
    from pipelines.voice.transcribe import transcribe

    print("\nDemo recordings" + (" (pre-caching with Gemini)" if precache else " (offline)"))
    all_ok = True
    for audio in audio_files:
        t = transcribe(str(audio), lang="hi")
        text = strip_pii(glossary_correct(t.text or "").text).text
        if not text:
            all_ok &= _line(False, audio.name, f"no transcript ({t.error or 'empty'})")
            continue
        live = describe(text, lang="hi", allow_gemini=False, use_cache=False)
        cached = describe(text, lang="hi", allow_gemini=precache)
        # No category is an allowed outcome (an object we have no category for
        # gets a wider price band, never a guessed one); no transcript, or a
        # pre-cache that didn't reach Gemini, is not.
        ok = cached.source in ("gemini", "cache") if precache else True
        category = live.category or "none — wider price band"
        all_ok &= _line(ok, audio.name,
                        f"heard {text!r} · offline: {live.title_en!r}, category {category}"
                        f" · replay answer from {cached.source}")
    return all_ok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--precache", action="store_true", help="call Gemini once per demo recording and cache it")
    ap.add_argument("audio", nargs="*", type=Path, help="recordings to check (default: the repo's *.m4a demo notes)")
    args = ap.parse_args()
    if not args.precache:
        # Prove the speech model loads from disk: the hub may not touch the network.
        os.environ["HF_HUB_OFFLINE"] = "1"

    audio_files = args.audio or sorted(REPO.glob("*.m4a"))
    ok = check_assets()
    ok &= check_demo_items(audio_files, args.precache) if audio_files else _line(False, "no demo recordings found")
    print("\n" + ("Ready for the offline demo." if ok else "Not ready — fix the ✗ lines above."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
