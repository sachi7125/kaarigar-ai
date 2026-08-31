"""Shared offline text-to-speech — BUILT DAY 1.

Read-back confirmation, voice-first onboarding, spoken alerts and quality nudges
all depend on this, so it is the first shared component. Offline by design.

On device this is `flutter_tts`; server-side we use an offline engine here. Order of
preference: pyttsx3 (cross-platform), then the macOS `say` binary, both offline. The
public surface is one function so callers never care which engine ran.

CLI:  python -m pipelines.voice.tts "text to speak" <out_path.aiff> [lang]
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# macOS voices that ship offline, keyed by our language codes.
_MAC_VOICE = {"en": "Samantha", "hi": "Lekha", "bn": None, "ta": None, "mr": None}

try:
    import pyttsx3  # noqa
    HAVE_PYTTSX3 = True
except Exception:  # pragma: no cover
    HAVE_PYTTSX3 = False


class TTSUnavailable(RuntimeError):
    pass


def _via_pyttsx3(text: str, out_path: Path) -> bool:
    try:
        engine = pyttsx3.init()
        engine.save_to_file(text, str(out_path))
        engine.runAndWait()
        return out_path.exists() and out_path.stat().st_size > 0
    except Exception:
        return False


def _via_macos_say(text: str, out_path: Path, lang: str) -> bool:
    say = shutil.which("say")
    if not say:
        return False
    cmd = [say, "-o", str(out_path)]
    voice = _MAC_VOICE.get(lang)
    if voice:
        cmd += ["-v", voice]
    cmd += [text]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return out_path.exists() and out_path.stat().st_size > 0
    except Exception:
        return False


def speak_to_file(text: str, out_path: str, lang: str = "en") -> str:
    """Synthesise `text` to an audio file at out_path. Returns the path.

    Raises TTSUnavailable if no offline engine could produce audio.
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if HAVE_PYTTSX3 and _via_pyttsx3(text, out):
        return str(out)
    if _via_macos_say(text, out, lang):
        return str(out)
    raise TTSUnavailable("no offline TTS engine available (tried pyttsx3, macOS say)")


def available() -> bool:
    return HAVE_PYTTSX3 or shutil.which("say") is not None


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('usage: python -m pipelines.voice.tts "text" <out_path> [lang]')
        raise SystemExit(2)
    text, out_path = sys.argv[1], sys.argv[2]
    lang = sys.argv[3] if len(sys.argv) > 3 else "en"
    print(speak_to_file(text, out_path, lang))
