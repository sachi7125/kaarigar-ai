"""Attribute suggestion — mandated feature 3, step 1 (Roadmap Day 4, decisions D2/D13).

Two independent, honest signals, never a trained classifier for either:

  - **Vision suggests size class and finish** from cheap, real pixel signals already
    available from the Day-1 enhancer: the subject's bounding-box coverage of the
    frame (size class) and the specular-highlight spread inside the subject mask
    (finish — glossy glaze/metal vs. matte textile/wood). Both are heuristics, not a
    trained model, and both are *suggestions* the artisan can reject.
  - **Material TYPE comes from the voice note, never the photo** (D2) — a plain
    keyword match of the (already glossary-corrected) transcript against a materials
    vocabulary. This is text matching, not image inference, so it is not the banned
    "material classifier".

Vision does NOT suggest a category name (e.g. "clay pot"): naming a specific object
from shape alone with no trained model would be a guess dressed up as a finding,
which is exactly the kind of fabricated-capability the project has avoided elsewhere
(D2's material-classifier refusal, the D11/D12 heavy-import refusals). Category comes
from the voice transcript via `pipelines.voice.describe` instead, which already reads
it from what she actually said. See decision D16.

Size is reported at TWO granularities from the same measurement: `size_class`
("small"/"medium"/"large") is what gets spoken and confirmed — a low-literacy artisan
can say yes/no to "is this medium-sized?", not to "is this 0.37 size units?". But
bucketing throws away real information: a photo at 16% frame coverage and one at 44%
both confirm as "medium" today, and were priced identically. `size_score` (the raw
0-1 coverage fraction) rides alongside `size_class` so `floor.py` and the pricing
model can use the finer number for whoever consumes it, without changing the spoken
interaction at all. If she rejects the size confirmation, BOTH size_class and
size_score are cleared — the continuous number is exactly as vision-derived and
exactly as untrustworthy as the bucket built from it.

0-2 spoken confirmations, attribute-only, never about price or cost (D13):
  1. Confirm the voice-extracted material, if one was found — never a vision guess,
     because offering a vision-based material guess to confirm would just be the
     banned classifier one step removed.
  2. Confirm the vision-suggested size class.
A "no" answer clears that field to unknown/unconfirmed rather than guessing again —
the same "state low confidence rather than fabricate" rule as the image pipeline's
failure-aware retake and the pricing model's out-of-range honesty.

No microphone code lives here (same rule as `capture.py` / `readback.py`, D14): the
caller injects `recorder(prompt_audio_path, attempt) -> str | None`.

CLI:  python -m pipelines.pricing.attributes <image_path> "<transcript>" [lang]
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Optional

import cv2
import numpy as np

from pipelines.common import cfg_get
from pipelines.image.enhance import subject_mask, cutout_metrics
from pipelines.voice import tts
from pipelines.voice.readback import classify_answer
from pipelines.voice.transcribe import transcribe

Recorder = Callable[[str, int], Optional[str]]

_OUT_DIR = Path("results/attributes")

# canonical (glossary-corrected) term -> data/reference/material_rates.csv key.
# Deliberately independent of craft_glossary.csv's file structure (that file mixes
# techniques/objects/materials under comments, not a machine-readable type column) —
# this is the pricing side's own small, explicit vocabulary.
MATERIAL_TERMS: dict[str, str] = {
    "clay": "clay", "terracotta clay": "terracotta", "terracotta": "terracotta",
    "brass": "brass", "copper": "copper", "silver": "silver",
    "cotton": "cotton", "silk": "silk", "wool": "wool", "jute": "jute",
    "bamboo": "bamboo", "sandalwood": "sandalwood", "wood": "wood",
    "leather": "leather",
    "मिट्टी": "clay", "पीतल": "brass", "तांबा": "copper", "चांदी": "silver",
    "सूती": "cotton", "रेशम": "silk", "बांस": "bamboo", "लकड़ी": "wood",
    # "चमड़ा"/"चमड़े" (the plain Hindi word, inflected form "of leather") and
    # "लेदर" (the common English-loanword transliteration) — found missing
    # live 7 Sep: a real leather-sandal voice note said "लेदर" clearly, but
    # nothing in this dict recognised it, so material silently came back
    # empty. Leather goods (chappals, bags, belts) are a major Indian craft
    # category this vocabulary had no entry for at all.
    "चमड़ा": "leather", "चमड़े": "leather", "लेदर": "leather",
}

# Spelled out (not \w) for the same reason as glossary.py: \w excludes Devanagari
# matras/virama (they are Mn marks), which would shred a word like "मिट्टी".
_DEVA_RANGE = "ऀ-ॿ"
_WORD_RE = re.compile(rf"[\w{_DEVA_RANGE}]+", re.UNICODE)

_SIZE_SMALL_MAX = 0.15
_SIZE_MEDIUM_MAX = 0.45
_SIZE_LARGE_CEILING = 0.85   # practical soft ceiling for "fills almost the whole frame"

# (low, high) coverage range each spoken bucket covers, and a representative point
# within that range used as the interpolation anchor in floor.py/model.py. Exposed
# publicly so those modules never hardcode a copy of these boundaries.
SIZE_BOUNDS: dict[str, tuple[float, float]] = {
    "small": (0.0, _SIZE_SMALL_MAX),
    "medium": (_SIZE_SMALL_MAX, _SIZE_MEDIUM_MAX),
    "large": (_SIZE_MEDIUM_MAX, _SIZE_LARGE_CEILING),
}
SIZE_REPRESENTATIVE: dict[str, float] = {
    k: round((lo + hi) / 2, 4) for k, (lo, hi) in SIZE_BOUNDS.items()
}

# Attribute-only spoken confirms. Only the wrapper phrasing is templated.
_PHRASE = {
    "hi": {"material": "मैंने सुना: सामग्री {v}। क्या यह सही है? हाँ या नहीं बोलिए।",
           "size": "मैंने अंदाज़ा लगाया: यह आकार में {v} है। क्या यह सही है? हाँ या नहीं बोलिए।",
           "unclear": "समझ नहीं आया। कृपया हाँ या नहीं बोलिए।"},
    "bn": {"material": "আমি শুনেছি: উপকরণ {v}। এটা কি ঠিক? হ্যাঁ বা না বলুন।",
           "size": "আমার অনুমান: এটি আকারে {v}। এটা কি ঠিক? হ্যাঁ বা না বলুন।",
           "unclear": "বুঝতে পারিনি। হ্যাঁ বা না বলুন।"},
    "ta": {"material": "நான் கேட்டது: பொருள் {v}. இது சரியா? ஆம் அல்லது இல்லை என்று சொல்லுங்கள்.",
           "size": "என் யூகம்: இது அளவில் {v}. இது சரியா? ஆம் அல்லது இல்லை என்று சொல்லுங்கள்.",
           "unclear": "புரியவில்லை. ஆம் அல்லது இல்லை என்று சொல்லுங்கள்."},
    "mr": {"material": "मी ऐकले: साहित्य {v}. हे बरोबर आहे का? होय किंवा नाही बोला.",
           "size": "माझा अंदाज: हे आकाराने {v} आहे. हे बरोबर आहे का? होय किंवा नाही बोला.",
           "unclear": "समजले नाही. कृपया होय किंवा नाही बोला."},
    "en": {"material": "I heard: material {v}. Is this correct? Say yes or no.",
           "size": "My guess: this is {v} sized. Is this correct? Say yes or no.",
           "unclear": "I did not catch that. Please say yes or no."},
}

_SIZE_WORD = {
    "hi": {"small": "छोटे", "medium": "मध्यम", "large": "बड़े"},
    "bn": {"small": "ছোট", "medium": "মাঝারি", "large": "বড়"},
    "ta": {"small": "சிறிய", "medium": "நடுத்தர", "large": "பெரிய"},
    "mr": {"small": "लहान", "medium": "मध्यम", "large": "मोठ्या"},
    "en": {"small": "small", "medium": "medium", "large": "large"},
}


@dataclass
class AttributeResult:
    material: str = ""                    # material_rates.csv key, "" if none found/confirmed
    material_source: str = "none"         # "voice" | "unconfirmed" | "none"
    size_class: str = ""                  # "small" | "medium" | "large" | "" if unconfirmed
    size_score: float | None = None       # raw 0-1 frame-coverage fraction behind size_class;
                                           # cleared alongside size_class on a spoken "no"
    size_source: str = "vision-suggested"  # "vision-suggested" | "confirmed" | "unconfirmed"
    finish: str = "unknown"               # "glossy" | "matte" | "unknown" — display-only, not spoken-confirmed
    questions_asked: list[str] = field(default_factory=list)
    error: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- vision
def suggest_size_class(coverage: float) -> str:
    """Rough size suggestion from how much of the frame the subject fills. This is
    NOT a physical measurement (no scale reference in shot) — it is a starting guess
    the spoken confirmation step exists specifically to correct."""
    if coverage < _SIZE_SMALL_MAX:
        return "small"
    if coverage < _SIZE_MEDIUM_MAX:
        return "medium"
    return "large"


def suggest_finish(bgr: np.ndarray, alpha: np.ndarray) -> str:
    """Glossy (fired glaze, metal, lacquer) vs matte (textile, unglazed clay, wood),
    via the gap between the subject's top-1%-brightest pixels and its median
    brightness: a glossy surface throws a small, sharp specular highlight (top 1%
    far brighter than the median); a matte surface reflects light diffusely (top 1%
    close to the median). The 99th percentile (not the raw max) is used so a single
    noisy pixel can't flip the result. Heuristic, display-only."""
    mask = alpha > 127
    if mask.sum() < 50:
        return "unknown"
    l_channel = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)[:, :, 0]
    vals = l_channel[mask].astype(np.float32)
    spread = float(np.percentile(vals, 99) - np.median(vals))
    return "glossy" if spread > 50.0 else "matte"


def _vision_suggestions(image_path: str) -> tuple[str, float, str]:
    bgr = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if bgr is None:
        return "", 0.0, "unknown"
    alpha = subject_mask(bgr)
    coverage, _subject_frac = cutout_metrics(alpha)
    return suggest_size_class(coverage), coverage, suggest_finish(bgr, alpha)


# --------------------------------------------------------------------------- voice
def extract_material(transcript: str) -> str:
    """First materials-vocabulary word found in the (glossary-corrected) transcript.
    Plain keyword match — the material TYPE comes from her words, never the photo.
    .lower() is a no-op on Devanagari, so one pass covers both scripts."""
    for word in _WORD_RE.findall((transcript or "").lower()):
        if word in MATERIAL_TERMS:
            return MATERIAL_TERMS[word]
    return ""


# --------------------------------------------------------------------- confirm loop
def _speak(text: str, lang: str, name: str) -> str | None:
    try:
        return tts.speak_to_file(text, str(_OUT_DIR / f"{name}_{lang}.aiff"), lang=lang)
    except Exception:
        return None


def _confirm(prompt_text: str, lang: str, recorder: Recorder, name: str) -> bool | None:
    """One spoken yes/no confirmation. Returns True/False/None (unclear/no answer)."""
    p = _PHRASE.get(lang, _PHRASE["en"])
    prompt_audio = _speak(prompt_text, lang, name)
    max_attempts = int(cfg_get("readback.max_confirm_attempts", 2))
    for attempt in range(1, max_attempts + 1):
        answer_audio = recorder(prompt_audio or "", attempt)
        if not answer_audio:
            return None
        heard = transcribe(answer_audio, lang=lang)
        verdict = classify_answer(heard.text, lang)
        if verdict is not None:
            return verdict
        prompt_audio = _speak(p["unclear"], lang, f"{name}_unclear")
    return None


def suggest_attributes(image_path: str, transcript: str, lang: str = "hi",
                       recorder: Recorder | None = None) -> AttributeResult:
    """Vision suggests size_class + finish; voice supplies material; up to 2 spoken,
    attribute-only confirmations (material if found, size always) when a `recorder`
    is given. With no `recorder`, returns the unconfirmed suggestions for the caller
    to confirm through its own UI instead."""
    lang = (lang or "hi").lower()
    res = AttributeResult()

    try:
        size_guess, size_score, finish_guess = _vision_suggestions(image_path)
    except Exception as e:
        res.error = f"vision suggestion failed: {e}"
        size_guess, size_score, finish_guess = "", 0.0, "unknown"
    res.size_class = size_guess
    res.size_score = size_score if size_guess else None
    res.finish = finish_guess

    material_guess = extract_material(transcript)
    if material_guess:
        res.material = material_guess
        res.material_source = "voice"

    if recorder is None:
        if res.size_class:
            res.size_source = "vision-suggested"
        return res

    p = _PHRASE.get(lang, _PHRASE["en"])
    size_words = _SIZE_WORD.get(lang, _SIZE_WORD["en"])

    if material_guess:
        q = p["material"].format(v=material_guess)
        res.questions_asked.append(q)
        verdict = _confirm(q, lang, recorder, "material")
        if verdict is True:
            res.material_source = "confirmed"
        else:
            res.material, res.material_source = "", "unconfirmed"

    if size_guess:
        q = p["size"].format(v=size_words.get(size_guess, size_guess))
        res.questions_asked.append(q)
        verdict = _confirm(q, lang, recorder, "size")
        if verdict is True:
            res.size_source = "confirmed"
        else:
            res.size_class, res.size_score, res.size_source = "", None, "unconfirmed"

    return res


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print('usage: python -m pipelines.pricing.attributes <image_path> "<transcript>" [lang]')
        raise SystemExit(2)
    lang_arg = sys.argv[3] if len(sys.argv) > 3 else "hi"
    r = suggest_attributes(sys.argv[1], sys.argv[2], lang=lang_arg)
    print(f"material : {r.material or '(none)'}  ({r.material_source})")
    score_str = f"{r.size_score:.3f}" if r.size_score is not None else "(none)"
    print(f"size     : {r.size_class or '(unknown)'}  ({r.size_source}, score={score_str})")
    print(f"finish   : {r.finish}")
    if r.questions_asked:
        print("asked    :", " / ".join(r.questions_asked))
    if r.error:
        print("note     :", r.error)
