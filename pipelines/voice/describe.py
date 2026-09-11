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

import csv
import functools
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path

from pipelines.common import cfg_get, env_get, REPO_ROOT
from pipelines.pricing.material_terms import MATERIAL_TERMS

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
# category guess + normalisation (Day 7)                                      #
# --------------------------------------------------------------------------- #
# floor.py looks the category up in category_weight_overrides.csv for a
# realistic weight/hours. That lookup used to miss two ways: offline (template
# path) the category was always "", and online Gemini returns free text
# ("silver jewelry", "leather sandals") not spelled like the CSV ("silver
# jewellery", "leather footwear"). Both now go through the same plain keyword
# match — no model, no invention; text that matches nothing is left as it was.
#
# Two tiers, because a specific craft word should win wherever it appears in
# the sentence: "पीतल की मूर्ति ढोकरा शैली की" is a dhokra figurine even though
# the generic "मूर्ति" comes first. Within a tier the first match wins.
#
# Generic entries that are dicts disambiguate by MATERIAL, via the same
# MATERIAL_TERMS vocabulary pricing uses — so a Hindi "तांबे का बर्तन" reaches
# "copper", not only an English "copper vessel". A dict with no matching
# material and no "default" contributes nothing and the scan carries on: "हार"
# is a necklace next to silver, but also a garland and the word for "lost".
_DEVA_RANGE = "ऀ-ॿ"
_WORD_RE = re.compile(rf"[\w{_DEVA_RANGE}]+", re.UNICODE)
_CATEGORIES_PATH = REPO_ROOT / "data" / "reference" / "category_weight_overrides.csv"

_SPECIFIC_TERMS: dict[str, str] = {
    "dhokra": "dhokra figurine", "ढोकरा": "dhokra figurine",
    "kanjivaram": "kanjivaram silk saree", "कांजीवरम": "kanjivaram silk saree",
    "kanchipuram": "kanjivaram silk saree", "कांचीपुरम": "kanjivaram silk saree",
    "banarasi": "banarasi silk saree", "बनारसी": "banarasi silk saree",
    "madhubani": "madhubani painting", "मधुबनी": "madhubani painting",
    "pashmina": "pashmina shawl", "पश्मीना": "pashmina shawl",
}

_METAL_OR_CLAY_VESSEL = {"copper": "copper vessel", "brass": "copper vessel",
                         "clay": "clay pottery", "default": "clay pottery"}

_GENERIC_TERMS: dict[str, str | dict[str, str]] = {
    # pottery ("matki" is where the glossary sends an English "matka")
    "मटका": "clay pottery", "मटकी": "clay pottery", "कुल्हड़": "clay pottery",
    "matka": "clay pottery", "matki": "clay pottery", "pottery": "clay pottery",
    "pot": {"copper": "copper vessel", "brass": "copper vessel", "default": "clay pottery"},
    # diya — "दिया" is also the everyday verb "gave", so it only counts next to clay
    "दीया": "terracotta diya", "दीये": "terracotta diya",
    "diya": "terracotta diya", "diyas": "terracotta diya",
    "दिया": {"clay": "terracotta diya", "terracotta": "terracotta diya"},
    # idols (dhokra is in _SPECIFIC_TERMS)
    "मूर्ति": "brass idol", "मूर्ती": "brass idol",
    "idol": "brass idol", "statue": "brass idol", "murti": "brass idol",
    # vessels: metal vs clay by material
    "लोटा": "copper vessel", "lota": "copper vessel",
    "vessel": {**_METAL_OR_CLAY_VESSEL, "default": "copper vessel"},
    "बर्तन": _METAL_OR_CLAY_VESSEL, "bartan": _METAL_OR_CLAY_VESSEL,
    "cup": {"copper": "copper vessel", "default": "clay pottery"},
    # a cooking pot: metal or clay; a bamboo पतीला matches no category we
    # have, so it gets none (and the wider band that goes with it)
    "पतीला": {"copper": "copper vessel", "brass": "copper vessel", "clay": "clay pottery"},
    "पतीली": {"copper": "copper vessel", "brass": "copper vessel", "clay": "clay pottery"},
    # jewellery
    "कड़ा": "silver jewellery", "kada": "silver jewellery",
    "गहना": "silver jewellery", "गहने": "silver jewellery", "जेवर": "silver jewellery",
    "झुमका": "silver jewellery",
    "jewellery": "silver jewellery", "jewelry": "silver jewellery",
    "necklace": "silver jewellery", "earring": "silver jewellery",
    "earrings": "silver jewellery", "bangle": "silver jewellery",
    "bangles": "silver jewellery",
    "हार": {"silver": "silver jewellery"},
    # textiles
    "साड़ी": {"silk": "banarasi silk saree", "default": "handloom cotton saree"},
    "साडी": {"silk": "banarasi silk saree", "default": "handloom cotton saree"},
    "saree": {"silk": "banarasi silk saree", "default": "handloom cotton saree"},
    "sari": {"silk": "banarasi silk saree", "default": "handloom cotton saree"},
    "दुपट्टा": "bandhani dupatta", "dupatta": "bandhani dupatta",
    "शॉल": "pashmina shawl", "shawl": "pashmina shawl",
    # bags: leather vs jute by material
    "बैग": {"leather": "leather bag", "default": "jute bag"},
    "bag": {"leather": "leather bag", "default": "jute bag"},
    "बस्ता": {"leather": "leather bag", "default": "jute bag"},
    # the rest
    "टोकरी": "bamboo basket", "basket": "bamboo basket",
    "खिलौना": "wooden toy", "खिलौने": "wooden toy", "toy": "wooden toy",
    "पेंटिंग": "madhubani painting", "painting": "madhubani painting",
    "चप्पल": "leather footwear", "चप्पलें": "leather footwear",
    "chappal": "leather footwear", "chappals": "leather footwear",
    "sandal": "leather footwear", "sandals": "leather footwear",
    "जूता": "leather footwear", "जूते": "leather footwear",
    "shoe": "leather footwear", "shoes": "leather footwear",
    "footwear": "leather footwear",
}


def _resolve(entry: str | dict[str, str], materials: set[str]) -> str:
    if isinstance(entry, str):
        return entry
    for material, category in entry.items():
        if material != "default" and material in materials:
            return category
    return entry.get("default", "")


def _guess_category(transcript: str, materials: list[str]) -> str:
    """One of category_weight_overrides.csv's categories, or "" if nothing
    matched. `materials` (already-confirmed) and any material word in the
    transcript itself both count for disambiguation."""
    tokens = _WORD_RE.findall((transcript or "").lower())
    mats = {MATERIAL_TERMS.get(m, m) for m in (str(x).strip().lower() for x in materials or []) if m}
    mats |= {MATERIAL_TERMS[t] for t in tokens if t in MATERIAL_TERMS}
    for t in tokens:
        if t in _SPECIFIC_TERMS:
            return _SPECIFIC_TERMS[t]
    for t in tokens:
        entry = _GENERIC_TERMS.get(t)
        if entry is not None and (category := _resolve(entry, mats)):
            return category
    return ""


@functools.lru_cache(maxsize=1)
def _known_categories() -> frozenset[str]:
    """Category names in category_weight_overrides.csv, read once."""
    try:
        text = _CATEGORIES_PATH.read_text(encoding="utf-8")
    except OSError:
        return frozenset()
    rows = csv.DictReader(l for l in text.splitlines() if l.strip() and not l.startswith("#"))
    return frozenset(r["category"].strip().lower() for r in rows if r.get("category"))


def normalize_category(raw: str, transcript: str = "", materials: list[str] | None = None) -> str:
    """Snap a free-text category onto the names the weight table uses. Tries
    the text itself, then the transcript; keeps the original words when
    neither matches rather than forcing a wrong category."""
    raw = (raw or "").strip().lower()
    if raw in _known_categories():
        return raw
    return (_guess_category(raw, materials or [])
            or _guess_category(transcript, materials or [])
            or raw)


# --------------------------------------------------------------------------- #
# backend 2: offline template                                                 #
# --------------------------------------------------------------------------- #
def _describe_template(transcript: str, lang: str, attributes: dict) -> ListingDraft:
    a = attributes or {}
    cat = str(a.get("category", "")).strip().lower()
    materials = a.get("materials") or ([a["material"]] if a.get("material") else [])
    materials = [str(m).strip() for m in materials if str(m).strip()]
    if not materials:
        # Day 7: the materials she named, through the same vocabulary pricing
        # uses — so "ये एक बांस का पतीला है" still yields "made of bamboo" even
        # when the object itself is one we have no category for.
        heard = (MATERIAL_TERMS[t] for t in _WORD_RE.findall(transcript.lower()) if t in MATERIAL_TERMS)
        materials = list(dict.fromkeys(heard))

    # Day 7: if the caller didn't supply a category (Gemini unreachable and
    # no confirmed attribute yet), try a keyword-based guess against the
    # transcript so floor.py can still match category_weight_overrides.csv.
    if not cat:
        cat = _guess_category(transcript, materials)

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
            return _snap_category(hit, transcript)

    if allow_gemini:
        try:
            draft = _describe_gemini(transcript, lang, attributes)
            if use_cache:
                _cache_write(key, draft)
            return _snap_category(draft, transcript)
        except Exception as e:
            fallback_note = f"gemini unavailable ({e.__class__.__name__}: {e}); used template"
    else:
        fallback_note = "gemini disabled; used template"

    draft = _describe_template(transcript, lang, attributes)
    draft.error = fallback_note
    return _snap_category(draft, transcript)


def _snap_category(draft: ListingDraft, transcript: str) -> ListingDraft:
    # Every backend's category goes through the same snap, so pricing sees
    # "silver jewellery" whether Gemini, the cache or the template produced it.
    draft.category = normalize_category(draft.category, transcript, draft.materials)
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