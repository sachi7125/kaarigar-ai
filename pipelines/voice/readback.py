"""Spoken read-back confirmation — mandated feature 2, step 5 (Roadmap Day 2).

The exit gate for Day 2: **nothing publishes until she has heard it and said yes.**
For a low-literacy artisan the read-back is the only proofreading step that exists,
so it has to be spoken, in her own language, and honest about anything we changed.

What we read back is **what we heard**, not the generated marketing copy (D15):

    "I heard: <her cleaned transcript>."
    "I corrected बर्दन to बर्तन."          (only if the glossary changed something)
    "I removed a phone number."            (only if PII was stripped)
    "Category: clay pottery. Price: 400."  (only the facts we actually extracted)
    "Is this correct? Say yes or no."

Her transcript is already in her language, so this works for hi/bn/ta/mr/en without a
translation step — Gemini only gives us EN+HI. The generated Hindi title is read too,
but only when she actually spoke Hindi.

No microphone code lives here (same rule as `capture.py`, D14). The caller injects:

    recorder(prompt_audio_path: str, attempt: int) -> str | None

which plays the read-back and returns the path of her recorded yes/no answer.

CLI:  python -m pipelines.voice.readback "<transcript>" [lang]
"""
from __future__ import annotations

import difflib
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Optional

from pipelines.common import cfg_get
from pipelines.voice import tts
from pipelines.voice.transcribe import transcribe

Recorder = Callable[[str, int], Optional[str]]

_OUT_DIR = Path("results/readback")

# Spoken wrappers per language. Only the phrasing is templated — the content is her
# own words, which are already in her language.
_PHRASE = {
    "hi": {
        "heard": "मैंने यह सुना:",
        "corrected": "मैंने {a} को {b} किया।",
        "removed": "मैंने एक {what} हटा दिया।",
        "phone": "फ़ोन नंबर", "digits": "नंबर",
        "category": "श्रेणी: {v}।",
        "material": "सामग्री: {v}।",
        "price": "कीमत: {v} रुपये।",
        "ask": "क्या यह सही है? हाँ या नहीं बोलिए।",
        "unclear": "समझ नहीं आया। कृपया हाँ या नहीं बोलिए।",
    },
    "bn": {
        "heard": "আমি এটা শুনেছি:",
        "corrected": "আমি {a} কে {b} করেছি।",
        "removed": "আমি একটি {what} সরিয়ে দিয়েছি।",
        "phone": "ফোন নম্বর", "digits": "নম্বর",
        "category": "শ্রেণী: {v}।",
        "material": "উপকরণ: {v}।",
        "price": "দাম: {v} টাকা।",
        "ask": "এটা কি ঠিক? হ্যাঁ বা না বলুন।",
        "unclear": "বুঝতে পারিনি। হ্যাঁ বা না বলুন।",
    },
    "ta": {
        "heard": "நான் இதைக் கேட்டேன்:",
        "corrected": "நான் {a} ஐ {b} ஆக மாற்றினேன்.",
        "removed": "நான் ஒரு {what} நீக்கினேன்.",
        "phone": "தொலைபேசி எண்", "digits": "எண்",
        "category": "வகை: {v}.",
        "material": "பொருள்: {v}.",
        "price": "விலை: {v} ரூபாய்.",
        "ask": "இது சரியா? ஆம் அல்லது இல்லை என்று சொல்லுங்கள்.",
        "unclear": "புரியவில்லை. ஆம் அல்லது இல்லை என்று சொல்லுங்கள்.",
    },
    "mr": {
        "heard": "मी हे ऐकले:",
        "corrected": "मी {a} चे {b} केले.",
        "removed": "मी एक {what} काढून टाकला.",
        "phone": "फोन नंबर", "digits": "नंबर",
        "category": "प्रकार: {v}.",
        "material": "साहित्य: {v}.",
        "price": "किंमत: {v} रुपये.",
        "ask": "हे बरोबर आहे का? होय किंवा नाही बोला.",
        "unclear": "समजले नाही. कृपया होय किंवा नाही बोला.",
    },
    "en": {
        "heard": "I heard:",
        "corrected": "I corrected {a} to {b}.",
        "removed": "I removed a {what}.",
        "phone": "phone number", "digits": "long number",
        "category": "Category: {v}.",
        "material": "Material: {v}.",
        "price": "Price: {v} rupees.",
        "ask": "Is this correct? Say yes or no.",
        "unclear": "I did not catch that. Please say yes or no.",
    },
}

# Yes / no vocabulary per language. A one-word answer transcribes noisily, so these
# are matched fuzzily (see `classify_answer`).
_YES = {
    "hi": ["हाँ", "हां", "जी", "जी हाँ", "ठीक", "सही", "बिलकुल", "haan", "ha", "ji", "sahi", "theek"],
    "bn": ["হ্যাঁ", "হ্যা", "ঠিক", "হুম", "haan", "hyan", "thik"],
    "ta": ["ஆம்", "ஆமாம்", "சரி", "aam", "aamaam", "sari"],
    "mr": ["होय", "हो", "बरोबर", "ठीक", "hoy", "ho", "barobar"],
    "en": ["yes", "yeah", "yep", "correct", "right", "ok", "okay", "sure"],
}
_NO = {
    "hi": ["नहीं", "ना", "नही", "गलत", "nahi", "nahin", "na", "galat"],
    "bn": ["না", "নয়", "ভুল", "na", "noy", "bhul"],
    "ta": ["இல்லை", "இல்ல", "தவறு", "illai", "illa", "thavaru"],
    "mr": ["नाही", "ना", "चूक", "nahi", "na", "chuk"],
    "en": ["no", "nope", "wrong", "incorrect", "nah"],
}


@dataclass
class ReadbackResult:
    script: str                       # exactly what was spoken
    audio_path: str | None            # synthesised read-back, None if TTS unavailable
    confirmed: bool | None = None     # True=yes, False=no, None=no clear answer
    answer_text: str = ""             # what she actually said back
    attempts: int = 0                 # confirmation attempts made
    still_unclear: bool = False       # ran out of attempts without a yes/no
    error: str | None = None

    @property
    def may_publish(self) -> bool:
        """The Day-2 gate: publish ONLY on an explicit spoken yes."""
        return self.confirmed is True

    def as_dict(self) -> dict:
        d = asdict(self)
        d["may_publish"] = self.may_publish
        return d


def _phrases(lang: str | None) -> dict:
    return _PHRASE.get((lang or "hi").lower(), _PHRASE["en"])


def _price_from(transcript: str) -> str | None:
    """Any short number in her sentence is a price/size — we only echo it back."""
    m = re.search(r"\b(\d{2,6})\b", transcript or "")
    return m.group(1) if m else None


def build_script(transcript: str, lang: str = "hi", corrections=None,
                 redactions=None, category: str = "", materials=None,
                 title: str = "") -> str:
    """Compose the spoken read-back. Content is HER words; only wrappers are templated."""
    p = _phrases(lang)
    parts: list[str] = []

    said = (transcript or "").strip()
    if said:
        parts.append(f"{p['heard']} {said}")
    if title and (lang or "").lower() == "hi":
        parts.append(title.strip().rstrip(".") + "।")

    for c in (corrections or []):
        a = getattr(c, "original", None) or (c.get("original") if isinstance(c, dict) else "")
        b = getattr(c, "corrected", None) or (c.get("corrected") if isinstance(c, dict) else "")
        if a and b:
            parts.append(p["corrected"].format(a=a, b=b))

    for r in (redactions or []):
        kind = getattr(r, "kind", None) or (r.get("kind") if isinstance(r, dict) else "digits")
        parts.append(p["removed"].format(what=p.get(kind, p["digits"])))

    if category:
        parts.append(p["category"].format(v=category))
    mats = [m for m in (materials or []) if m]
    if mats:
        parts.append(p["material"].format(v=", ".join(mats)))
    price = _price_from(said)
    if price:
        parts.append(p["price"].format(v=price))

    parts.append(p["ask"])
    return " ".join(parts)


def speak_readback(script: str, lang: str = "hi",
                   out_path: str | None = None) -> str | None:
    """Synthesise the read-back. Returns the audio path, or None if TTS is unavailable."""
    code = (lang or "hi").lower()
    out = Path(out_path) if out_path else _OUT_DIR / f"readback_{code}.aiff"
    try:
        return tts.speak_to_file(script, str(out), lang=code)
    except Exception:
        return None


def classify_answer(text: str, lang: str = "hi", min_ratio: float = 0.8) -> bool | None:
    """True for yes, False for no, None if it is neither. Fuzzy — answers are noisy."""
    said = (text or "").strip().lower()
    if not said:
        return None
    code = (lang or "hi").lower()
    yes = [w.lower() for w in _YES.get(code, []) + _YES["en"]]
    no = [w.lower() for w in _NO.get(code, []) + _NO["en"]]

    words = re.findall(r"[^\s.,!?।]+", said)
    for w in words:
        if w in yes:
            return True
        if w in no:
            return False
    # nothing exact — fuzzy match the whole answer, closest of yes vs no wins
    y = difflib.get_close_matches(said, yes, n=1, cutoff=min_ratio)
    n = difflib.get_close_matches(said, no, n=1, cutoff=min_ratio)
    if y and not n:
        return True
    if n and not y:
        return False
    if y and n:
        ry = difflib.SequenceMatcher(None, said, y[0]).ratio()
        rn = difflib.SequenceMatcher(None, said, n[0]).ratio()
        return ry >= rn
    return None


def readback_and_confirm(transcript: str, lang: str = "hi", recorder: Recorder | None = None,
                         corrections=None, redactions=None, category: str = "",
                         materials=None, title: str = "",
                         max_attempts: int | None = None) -> ReadbackResult:
    """Speak the read-back and take a spoken yes/no. Publish only on `may_publish`.

    With no `recorder`, returns the script + audio so the caller can drive the answer.
    """
    if max_attempts is None:
        max_attempts = int(cfg_get("readback.max_confirm_attempts", 2))

    script = build_script(transcript, lang, corrections, redactions,
                          category, materials, title)
    audio = speak_readback(script, lang)
    res = ReadbackResult(script=script, audio_path=audio)
    if audio is None:
        res.error = "TTS unavailable; read-back not spoken"
    if recorder is None:
        return res

    p = _phrases(lang)
    prompt = audio or ""
    for attempt in range(1, max_attempts + 1):
        res.attempts = attempt
        answer_audio = recorder(prompt, attempt)
        if not answer_audio:
            break                                   # she walked away
        heard = transcribe(answer_audio, lang=lang)
        res.answer_text = heard.text
        verdict = classify_answer(heard.text, lang)
        if verdict is not None:
            res.confirmed = verdict
            return res
        # neither yes nor no — ask again, in her language
        prompt = speak_readback(p["unclear"], lang,
                                out_path=str(_OUT_DIR / f"unclear_{lang}.aiff")) or ""

    res.still_unclear = res.confirmed is None
    return res


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('usage: python -m pipelines.voice.readback "<transcript>" [lang]')
        raise SystemExit(2)
    lang_arg = sys.argv[2] if len(sys.argv) > 2 else "hi"
    r = readback_and_confirm(sys.argv[1], lang=lang_arg)
    print("script :", r.script)
    print("audio  :", r.audio_path or "(TTS unavailable)")
    print("publish:", r.may_publish, " (needs a spoken yes)")
