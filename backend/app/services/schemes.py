"""Government scheme cards (Day 7; roadmap Day 8 beat: "close on a real scheme").

One file per scheme in data/reference/schemes/, each with its sources and the
date the figures were checked. A card appears only when one of her listing
categories maps to a trade the scheme names, and even then it says her work
"seems to" or "may" fall under that trade and asks her to confirm at the
centre: eligibility is decided by the scheme's own verification, not by us.
Crafts with no mapping (textiles, painting, bags) get no card rather than a
guessed one.
"""
from __future__ import annotations

import json
from collections import Counter
from functools import lru_cache

from app.config import REPO_ROOT
from pipelines.voice.describe import normalize_category

SCHEMES_DIR = REPO_ROOT / "data" / "reference" / "schemes"

_FIT_HI = {
    "likely": "आपका काम '{trade}' वाले पारंपरिक काम में आता दिखता है — सेंटर पर पक्का कर लीजिए।",
    "possible": "आपका काम शायद '{trade}' वाले काम में आ सकता है — पंजीकरण से पहले सेंटर पर पूछ लीजिए।",
}
_FIT_EN = {
    "likely": "Your work seems to fall under the '{trade}' trade — confirm at the centre.",
    "possible": "Your work may fall under the '{trade}' trade — ask at the centre before registering.",
}


@lru_cache(maxsize=1)
def load_schemes() -> tuple[dict, ...]:
    return tuple(json.loads(p.read_text(encoding="utf-8")) for p in sorted(SCHEMES_DIR.glob("*.json")))


def _card(scheme: dict, category: str, trade: dict) -> dict:
    fit_hi = _FIT_HI[trade["match"]].format(trade=trade["trade_hi"])
    return {
        "id": scheme["id"],
        "name_en": scheme["name_en"], "name_hi": scheme["name_hi"],
        "for_category": category,
        "trade_en": trade["trade_en"], "trade_hi": trade["trade_hi"], "match": trade["match"],
        "fit_en": _FIT_EN[trade["match"]].format(trade=trade["trade_en"]),
        "fit_hi": fit_hi,
        "benefits_en": scheme["benefits_en"], "benefits_hi": scheme["benefits_hi"],
        "eligibility_en": scheme["eligibility_en"], "eligibility_hi": scheme["eligibility_hi"],
        "how_to_apply_en": scheme["how_to_apply_en"], "how_to_apply_hi": scheme["how_to_apply_hi"],
        "spoken_hi": " ".join([f"{scheme['name_hi']}।", fit_hi, scheme["summary_hi"],
                               scheme["conditions_hi"], scheme["how_to_apply_hi"]]),
        "checked_on": scheme["checked_on"],
        "sources": scheme["sources"],
    }


def scheme_cards(categories: list[str]) -> list[dict]:
    """At most one card per scheme, for her most-listed mapped category.
    Categories are snapped onto the weight table's names first, so listings
    published before Day 7 with free text like "pottery" still match."""
    ranked = [c for c, _ in Counter(normalize_category(c) for c in categories if c).most_common()]
    cards = []
    for scheme in load_schemes():
        for category in ranked:
            trade = scheme["trades"].get(category)
            if trade is not None:
                cards.append(_card(scheme, category, trade))
                break
    return cards
