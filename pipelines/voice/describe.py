"""Bilingual (EN + HI) product listing from a voice-note transcript — mandated
feature 2, step 3 (Roadmap Day 2).

Input is the (glossary-corrected, PII-stripped) transcript plus any structured
attributes already confirmed (category, materials, dimensions, colour, technique —
these mostly arrive on Day 4). Output is a `ListingDraft`: title, description and
feature bullets in **both English and Hindi**, plus SEO keywords and a normalised
category.

Gemini also does the *translation* here — it takes the regional-language transcript
directly and emits EN + HI (decision D11: no standalone MT model).

Backends, one return type:
  1. gemini   — Gemini REST API via `requests` (NO SDK: `google-generativeai` is
                deprecated and imports in ~156s on this machine). Model `models.describe`
                (default gemini-2.0-flash). One structured prompt -> strict JSON. Ground
                rule in the prompt: the voice note is the source of truth; never invent
                materials or prices.
  2. template — offline / no API key / quota hit. Builds a serviceable bilingual
                listing from the transcript + attributes with string templates. Never
                blocks the pipeline.

Disk cache: `data/processed/listing_cache/<sha1>.json`, keyed by transcript+attributes.
Checked before any API call, written on every gemini success. This *is* the Day-7
pre-cache path — run once online, replays offline. The API is never called in a loop.

CLI:  python -m pipelines.voice.describe "<transcript>" [lang]
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

from pipelines.common import cfg_get, env_get, REPO_ROOT

_CACHE_DIR = REPO_ROOT / "data" / "processed" / "listing_cache"

_MODEL = {
    "gemini-free": "gemini-3.6-flash",
    "gemini-flash": "gemini-3.6-flash",
    "gemini-flash-latest": "gemini-flash-latest",
    "gemini-2.5-flash": "gemini-2.5-flash",   # older keys only
    "gemini-pro": "gemini-3.6-pro",
}
_GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

_LANG_NAME = {"hi": "Hindi", "bn": "Bengali", "ta": "Tamil", "mr": "Marathi", "en": "English"}


@dataclass
class ListingDraft:
    title_en: str
    title_hi: str
    description_en: str
    description_hi: str
    bullets_en: list[str] = field(default_factory=list)
    bullets_hi: list[str] = field(default_factory=list)
    seo_keywords: list[str] = field(default_factory=list)
    category: str = ""
    materials: list[str] = field(default_factory=list)
    source: str = "template"          # "gemini" | "cache" | "template"
    error: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- #
# cache                                                                       #
# --------------------------------------------------------------------------- #
def _cache_key(transcript: str, lang: str, attributes: dict) -> str:
    blob = json.dumps({"t": transcript.strip(), "l": lang,
                       "a": attributes or {}}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()


def _cache_read(key: str) -> ListingDraft | None:
    fp = _CACHE_DIR / f"{key}.json"
    if not fp.exists():
        return None
    try:
        d = json.loads(fp.read_text(encoding="utf-8"))
        d["source"] = "cache"
        d.pop("_prompt", None)
        return ListingDraft(**d)
    except Exception:
        return None


def _cache_write(key: str, draft: ListingDraft) -> None:
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (_CACHE_DIR / f"{key}.json").write_text(
            json.dumps(draft.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


# --------------------------------------------------------------------------- #
# backend 1: Gemini                                                           #
# --------------------------------------------------------------------------- #
_PROMPT = """You write product listings for an online marketplace of Indian handmade crafts.
The seller is a low-literacy artisan who recorded a short voice note in {lang_name}.
That transcript is the ONLY source of truth about the product.

TRANSCRIPT ({lang_name}):
\"\"\"{transcript}\"\"\"

CONFIRMED ATTRIBUTES (may be empty; trust these over the transcript when they conflict):
{attributes}

Rules:
- Do NOT invent materials, dimensions, prices, or origin that are not in the transcript
  or the attributes. If unknown, leave it out.
- Keep it honest and plain. Short: title <= 12 words, description 2-3 sentences,
  3-5 bullets.
- Produce the listing in BOTH English and Hindi (natural Hindi, not transliteration).
- seo_keywords: 6-10 lowercase search terms a buyer might type (mix English + common
  transliterations), no hashtags.
- category: one short lowercase noun phrase (e.g. "clay pottery", "handloom saree").
- materials: array of materials explicitly mentioned; [] if none.

Return ONLY minified JSON, no markdown, with exactly these keys:
{{"title_en","title_hi","description_en","description_hi","bullets_en","bullets_hi",
"seo_keywords","category","materials"}}"""


def _describe_gemini(transcript: str, lang: str, attributes: dict) -> ListingDraft:
    import requests  # lazy; already a project dependency

    api_key = env_get("GEMINI_API_KEY") or env_get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("no GEMINI_API_KEY in .env")

    model_name = _MODEL.get(cfg_get("models.describe", "gemini-free"), "gemini-3.6-flash")
    prompt = _PROMPT.format(
        lang_name=_LANG_NAME.get(lang, lang or "the local language"),
        transcript=transcript.strip(),
        attributes=json.dumps(attributes or {}, ensure_ascii=False, indent=2),
    )
    resp = requests.post(
        _GEMINI_URL.format(model=model_name),
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.4,
                                 "responseMimeType": "application/json"},
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

    return ListingDraft(
        title_en=str(data.get("title_en", "")).strip(),
        title_hi=str(data.get("title_hi", "")).strip(),
        description_en=str(data.get("description_en", "")).strip(),
        description_hi=str(data.get("description_hi", "")).strip(),
        bullets_en=[str(x).strip() for x in data.get("bullets_en", []) if str(x).strip()],
        bullets_hi=[str(x).strip() for x in data.get("bullets_hi", []) if str(x).strip()],
        seo_keywords=[str(x).strip().lower() for x in data.get("seo_keywords", []) if str(x).strip()],
        category=str(data.get("category", "")).strip().lower(),
        materials=[str(x).strip() for x in data.get("materials", []) if str(x).strip()],
        source="gemini",
    )


def _parse_json(raw: str):
    for candidate in (raw, _strip_fence(raw)):
        try:
            return json.loads(candidate)
        except Exception:
            continue
    # last resort: first {...} block
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


# --------------------------------------------------------------------------- #
# backend 2: offline template                                                 #
# --------------------------------------------------------------------------- #
def _describe_template(transcript: str, lang: str, attributes: dict) -> ListingDraft:
    a = attributes or {}
    cat = str(a.get("category", "")).strip().lower()
    materials = a.get("materials") or ([a["material"]] if a.get("material") else [])
    materials = [str(m).strip() for m in materials if str(m).strip()]

    noun = cat or "craft item"
    lead = noun if "handmade" in noun or "handloom" in noun else f"Handmade {noun}"
    lead = lead[0].upper() + lead[1:]
    mat_phrase = f" made of {', '.join(materials)}" if materials else ""
    title_en = f"{lead}{mat_phrase}".strip()
    desc_en = (f"{lead}{mat_phrase}, crafted by an Indian artisan. "
               f"Described by the maker: \"{transcript.strip()}\"")

    # Hindi side: the maker's own words are already in their language; keep them
    # verbatim rather than risk a bad machine translation offline (D11).
    title_hi = transcript.strip()[:60] if lang != "en" else title_en
    desc_hi = transcript.strip() if lang != "en" else desc_en

    bullets_en = ["Handmade by an Indian artisan"]
    if materials:
        bullets_en.append("Material: " + ", ".join(materials))
    if a.get("dimensions"):
        bullets_en.append("Size: " + str(a["dimensions"]))
    if a.get("colour") or a.get("color"):
        bullets_en.append("Colour: " + str(a.get("colour") or a.get("color")))

    kw = [w for w in [noun, "handmade", "artisan", "indian craft", "handcrafted", *materials]
          if w]
    return ListingDraft(
        title_en=title_en, title_hi=title_hi,
        description_en=desc_en, description_hi=desc_hi,
        bullets_en=bullets_en, bullets_hi=[transcript.strip()] if transcript.strip() else [],
        seo_keywords=[k.lower() for k in kw][:10],
        category=cat, materials=materials, source="template",
    )


# --------------------------------------------------------------------------- #
# public entry point                                                          #
# --------------------------------------------------------------------------- #
def describe(transcript: str, lang: str = "hi", attributes: dict | None = None,
            use_cache: bool = True, allow_gemini: bool = True) -> ListingDraft:
    """Build a bilingual listing draft from a transcript.

    Order: cache -> Gemini (cached on success) -> offline template. Never raises;
    inspect `.source` and `.error`.
    """
    transcript = (transcript or "").strip()
    lang = (lang or "hi").strip().lower()
    attributes = attributes or {}

    if not transcript and not attributes:
        d = _describe_template("", lang, {})
        d.error = "empty transcript and no attributes"
        return d

    key = _cache_key(transcript, lang, attributes)
    if use_cache:
        hit = _cache_read(key)
        if hit is not None:
            return hit

    if allow_gemini:
        try:
            draft = _describe_gemini(transcript, lang, attributes)
            if use_cache:
                _cache_write(key, draft)
            return draft
        except Exception as e:
            fallback_note = f"gemini unavailable ({e.__class__.__name__}: {e}); used template"
    else:
        fallback_note = "gemini disabled; used template"

    draft = _describe_template(transcript, lang, attributes)
    draft.error = fallback_note
    return draft


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('usage: python -m pipelines.voice.describe "<transcript>" [lang]')
        raise SystemExit(2)
    lang_arg = sys.argv[2] if len(sys.argv) > 2 else "hi"
    r = describe(sys.argv[1], lang=lang_arg)
    print(f"source   : {r.source}")
    if r.error:
        print(f"note     : {r.error}")
    print(f"category : {r.category}   materials: {r.materials}")
    print("-" * 60)
    print(f"EN  {r.title_en}\n    {r.description_en}")
    for b in r.bullets_en:
        print(f"    • {b}")
    print()
    print(f"HI  {r.title_hi}\n    {r.description_hi}")
    for b in r.bullets_hi:
        print(f"    • {b}")
    print()
    print("keywords:", ", ".join(r.seo_keywords))
