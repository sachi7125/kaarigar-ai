"""Maker story — a short bilingual first-person bio from a voice note (Day 6).

Reuses the Day-2 voice pipeline exactly as the roadmap says ("Maker story
pipeline (reuses Day-2 voice pipeline)"): the caller runs transcribe ->
glossary_correct -> strip_pii first (same as a listing description), then
hands the cleaned transcript here. This module only does the bilingual
text generation step — deliberately a separate function from
`describe.py`'s `describe()`, because a maker story is a different kind of
text (a personal narrative, not a product listing) and needs its own prompt;
sharing describe()'s prompt would either produce a listing-shaped bio or
require overloading one prompt with two purposes.

Same two backends, same honesty rule as describe.py: Gemini REST (`requests`,
no SDK — see D12) with a disk cache, falling back to a template that never
invents anything not in the transcript. Never raises; inspect `.source`.

CLI:  python -m pipelines.voice.maker_story "<transcript>" [lang]
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

from pipelines.common import cfg_get, env_get, REPO_ROOT

_CACHE_DIR = REPO_ROOT / "data" / "processed" / "maker_story_cache"

_MODEL = {
    "gemini-free": "gemini-3.6-flash",
    "gemini-flash": "gemini-3.6-flash",
    "gemini-flash-latest": "gemini-flash-latest",
    "gemini-2.5-flash": "gemini-2.5-flash",
    "gemini-pro": "gemini-3.6-pro",
}
_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
_LANG_NAME = {"hi": "Hindi", "bn": "Bengali", "ta": "Tamil", "mr": "Marathi", "en": "English"}


@dataclass
class MakerStory:
    text_en: str
    text_hi: str
    source: str = "template"   # "gemini" | "cache" | "template"
    error: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def _cache_key(transcript: str, lang: str) -> str:
    blob = json.dumps({"t": transcript.strip(), "l": lang}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


def _cache_read(key: str) -> MakerStory | None:
    fp = _CACHE_DIR / f"{key}.json"
    if not fp.exists():
        return None
    try:
        d = json.loads(fp.read_text(encoding="utf-8"))
        d["source"] = "cache"
        return MakerStory(**d)
    except Exception:
        return None


def _cache_write(key: str, story: MakerStory) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (_CACHE_DIR / f"{key}.json").write_text(
            json.dumps(story.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


_PROMPT = """You write short maker-story bios for artisan storefronts on a handmade-crafts
platform. The artisan is a low-literacy person who recorded a short voice note in
{lang_name}, talking about herself, her craft, or her work. That transcript is the ONLY
source of truth — do not invent a name, place, years of experience, or any biographical
fact that isn't in it.

TRANSCRIPT ({lang_name}):
\"\"\"{transcript}\"\"\"

Rules:
- First person ("I ..."), warm and plain, 2-3 sentences, no marketing language.
- If the transcript has almost no biographical content, write a short honest sentence
  about the craft itself rather than padding with invented personal details.
- Produce it in BOTH English and Hindi (natural Hindi, not transliteration).

Return ONLY minified JSON, no markdown, with exactly these keys: {{"text_en","text_hi"}}"""


def _story_gemini(transcript: str, lang: str) -> MakerStory:
    import requests  # lazy; already a project dependency

    api_key = env_get("GEMINI_API_KEY") or env_get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("no GEMINI_API_KEY in .env")

    model_name = _MODEL.get(cfg_get("models.describe", "gemini-free"), "gemini-3.6-flash")
    prompt = _PROMPT.format(
        lang_name=_LANG_NAME.get(lang, lang or "the local language"),
        transcript=transcript.strip(),
    )
    resp = requests.post(
        _GEMINI_URL.format(model=model_name),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4, "responseMimeType": "application/json"},
        },
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Gemini HTTP {resp.status_code}: {resp.text[:200]}")
    body = resp.json()
    try:
        raw = body["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError):
        raise ValueError(f"unexpected Gemini response shape: {json.dumps(body)[:200]}")
    data = _parse_json(raw)
    if data is None:
        raise ValueError(f"Gemini returned non-JSON: {raw[:200]!r}")

    return MakerStory(
        text_en=str(data.get("text_en", "")).strip(),
        text_hi=str(data.get("text_hi", "")).strip(),
        source="gemini",
    )


def _parse_json(raw: str):
    for candidate in (raw, _strip_fence(raw)):
        try:
            return json.loads(candidate)
        except Exception:
            continue
    i, j = raw.find("{"), raw.rfind("}")
    if 0 <= i < j:
        try:
            return json.loads(raw[i:j + 1])
        except Exception:
            return None
    return None


def _strip_fence(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[-1]
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    return s.strip()


def _story_template(transcript: str, lang: str) -> MakerStory:
    t = transcript.strip()
    # Offline / no key: her own words, verbatim, are already the most honest
    # bio available — same reasoning describe.py's template uses for the
    # non-English title/description (D11: no risky offline MT).
    if lang == "en":
        text_en = t or "A handmade-craft artisan."
        text_hi = t or "A handmade-craft artisan."
    else:
        text_hi = t or "एक हस्तशिल्प कारीगर।"
        text_en = f'"{t}"' if t else "A handmade-craft artisan."
    return MakerStory(text_en=text_en, text_hi=text_hi, source="template")


def build_maker_story(transcript: str, lang: str = "hi", use_cache: bool = True,
                      allow_gemini: bool = True) -> MakerStory:
    """Build a bilingual maker-story bio from an already-cleaned transcript.

    Order: cache -> Gemini (cached on success) -> offline template. Never raises.
    """
    transcript = (transcript or "").strip()
    lang = (lang or "hi").strip().lower()

    if not transcript:
        d = _story_template("", lang)
        d.error = "empty transcript"
        return d

    key = _cache_key(transcript, lang)
    if use_cache:
        hit = _cache_read(key)
        if hit is not None:
            return hit

    if allow_gemini:
        try:
            story = _story_gemini(transcript, lang)
            if use_cache:
                _cache_write(key, story)
            return story
        except Exception as e:
            fallback_note = f"gemini unavailable ({e.__class__.__name__}: {e}); used template"
    else:
        fallback_note = "gemini disabled; used template"

    story = _story_template(transcript, lang)
    story.error = fallback_note
    return story


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('usage: python -m pipelines.voice.maker_story "<transcript>" [lang]')
        raise SystemExit(2)
    lang_arg = sys.argv[2] if len(sys.argv) > 2 else "hi"
    r = build_maker_story(sys.argv[1], lang=lang_arg)
    print(f"source: {r.source}")
    if r.error:
        print(f"note  : {r.error}")
    print(f"EN: {r.text_en}")
    print(f"HI: {r.text_hi}")
