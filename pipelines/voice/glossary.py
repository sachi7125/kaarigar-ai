"""Craft-vocabulary fuzzy-correct — mandated feature 2, step 4 (Roadmap Day 2).

Whisper reliably mangles craft words it has never seen: `dhokra` -> "dokra",
`bandhani` -> "bandani", `बर्तन` -> "बर्दन". Those words are exactly the ones a buyer
searches for, so a mishear costs the artisan the listing. This module snaps such
tokens back to a canonical spelling.

Data: `data/reference/craft_glossary.csv` — `canonical,variants` (variants pipe-
separated). Devanagari and Latin live in SEPARATE rows so a correction never
switches script.

Matching, in order per token:
  1. exact variant hit  -> canonical
  2. `difflib` close match over canonical+variant forms of the same script, above
     `min_ratio` (default 0.82) -> canonical
Tokens shorter than 3 chars, pure digits, and exact canonical hits are left alone.

stdlib only (`difflib`) — no fuzzy-match dependency, deliberately (watchlist).

CLI:  python -m pipelines.voice.glossary "<text>"
"""
from __future__ import annotations

import csv
import difflib
import functools
import re
import sys
from dataclasses import dataclass, asdict

from pipelines.common import REPO_ROOT

GLOSSARY_PATH = REPO_ROOT / "data" / "reference" / "craft_glossary.csv"

# Split into word / non-word runs so we can rebuild the string with spacing intact.
# The Devanagari block is spelled out because Python's `\w` excludes matras and the
# virama (they are Mn marks), which would shred "मिट्टी" into "म" + "िट" + ...
_DEVA_RANGE = "\u0900-\u097F"
_TOKEN_RE = re.compile(rf"([\w{_DEVA_RANGE}]+|[^\w{_DEVA_RANGE}]+)", re.UNICODE)
_DEVANAGARI = re.compile(rf"[{_DEVA_RANGE}]")
# "contains at least one letter" — str.isalnum() is False for tokens holding a virama
_HAS_LETTER = re.compile(rf"[^\W\d_]|[{_DEVA_RANGE}]", re.UNICODE)


@dataclass
class Correction:
    original: str
    corrected: str
    how: str          # "exact" | "fuzzy"
    ratio: float      # 1.0 for exact


@dataclass
class GlossaryResult:
    text: str
    corrections: list[Correction]

    def as_dict(self) -> dict:
        return asdict(self)


def _is_devanagari(s: str) -> bool:
    return bool(_DEVANAGARI.search(s))


@functools.lru_cache(maxsize=1)
def _load() -> tuple[dict, dict, tuple, tuple]:
    """-> (variant->canonical for latin, same for deva, latin forms, deva forms)."""
    latin_map: dict[str, str] = {}
    deva_map: dict[str, str] = {}
    if not GLOSSARY_PATH.exists():
        return latin_map, deva_map, (), ()

    with open(GLOSSARY_PATH, encoding="utf-8") as fh:
        rows = [ln for ln in fh if ln.strip() and not ln.lstrip().startswith("#")]
    for row in csv.DictReader(rows):
        canonical = (row.get("canonical") or "").strip()
        if not canonical:
            continue
        target = deva_map if _is_devanagari(canonical) else latin_map
        forms = [canonical] + [v.strip() for v in (row.get("variants") or "").split("|")]
        for form in forms:
            if form:
                target.setdefault(form.lower(), canonical)
    return latin_map, deva_map, tuple(latin_map), tuple(deva_map)


def correct(text: str, min_ratio: float = 0.82) -> GlossaryResult:
    """Snap misheard craft/material words to their canonical spelling."""
    if not (text or "").strip():
        return GlossaryResult(text="", corrections=[])

    latin_map, deva_map, latin_forms, deva_forms = _load()
    corrections: list[Correction] = []
    out: list[str] = []

    for tok in _TOKEN_RE.findall(text):
        if not _HAS_LETTER.search(tok) or tok.isdigit() or len(tok) < 3:
            out.append(tok)
            continue

        deva = _is_devanagari(tok)
        mapping, forms = (deva_map, deva_forms) if deva else (latin_map, latin_forms)
        key = tok.lower()

        canonical = mapping.get(key)
        if canonical is not None:
            if canonical != tok:
                corrections.append(Correction(tok, canonical, "exact", 1.0))
            out.append(canonical)
            continue

        hit = difflib.get_close_matches(key, forms, n=1, cutoff=min_ratio)
        if hit:
            canonical = mapping[hit[0]]
            ratio = difflib.SequenceMatcher(None, key, hit[0]).ratio()
            if canonical != tok:
                corrections.append(Correction(tok, canonical, "fuzzy", round(ratio, 3)))
            out.append(canonical)
            continue

        out.append(tok)

    return GlossaryResult(text="".join(out), corrections=corrections)


def terms() -> list[str]:
    """Every canonical term — useful as a whisper `initial_prompt` bias later."""
    latin_map, deva_map, _, _ = _load()
    return sorted(set(latin_map.values()) | set(deva_map.values()))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('usage: python -m pipelines.voice.glossary "<text>"')
        raise SystemExit(2)
    r = correct(sys.argv[1])
    print(r.text)
    for c in r.corrections:
        print(f"  {c.original!r} -> {c.corrected!r}  ({c.how}, {c.ratio})")
