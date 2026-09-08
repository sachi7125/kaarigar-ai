"""Bounded seasonal multiplier — mandated feature 3, step 3 (Roadmap Day 4).

A small, deterministic lookup (Diwali pottery/brass, wedding-season textiles/
jewellery) — not a learned effect, so it can never run away. The multiplier is
always clamped to +/- `pricing.seasonal_multiplier_cap` (config.yaml, default 0.25),
so even a wrongly-matched category shifts the price band by at most a quarter, never
distorts it into something implausible.

CLI:  python -m pipelines.pricing.seasonal <category> <month 1-12>
"""
from __future__ import annotations

import sys

from pipelines.common import cfg_get

# Month numbers a season is considered "in". Diwali's actual date is lunar and
# shifts each year (mid-Oct to mid-Nov); Oct/Nov is a reasonable fixed approximation
# for a rule-based table. Wedding season in most of India runs roughly Oct-Feb.
_SEASON_MONTHS: dict[str, set[int]] = {
    "diwali": {10, 11},
    "wedding": {10, 11, 12, 1, 2},
}

# category keyword (matched as a substring of the lowercased category) -> per-season
# boost, BEFORE clamping to the config cap.
_CATEGORY_SEASON_BOOST: dict[str, dict[str, float]] = {
    "diya": {"diwali": 0.20},
    "pottery": {"diwali": 0.10},
    "brass": {"diwali": 0.10},
    "dhokra": {"diwali": 0.10},
    "saree": {"wedding": 0.20},
    "dupatta": {"wedding": 0.15},
    "jewellery": {"wedding": 0.20},
    "jewelry": {"wedding": 0.20},
    "shawl": {"wedding": 0.10},
    "pashmina": {"wedding": 0.10},
}


def active_seasons(month: int) -> list[str]:
    return [s for s, months in _SEASON_MONTHS.items() if month in months]


def seasonal_multiplier(category: str, month: int) -> float:
    """1.0 + a bounded boost, never below (1 - cap) or above (1 + cap)."""
    cap = float(cfg_get("pricing.seasonal_multiplier_cap", 0.25))
    cat = (category or "").lower()
    boost = 0.0
    for keyword, season_boosts in _CATEGORY_SEASON_BOOST.items():
        if keyword not in cat:
            continue
        for season in active_seasons(month):
            boost = max(boost, season_boosts.get(season, 0.0))
    boost = max(-cap, min(cap, boost))
    return round(1.0 + boost, 4)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python -m pipelines.pricing.seasonal <category> <month 1-12>")
        raise SystemExit(2)
    cat_arg, month_arg = sys.argv[1], int(sys.argv[2])
    mult = seasonal_multiplier(cat_arg, month_arg)
    print(f"seasons active: {active_seasons(month_arg) or '(none)'}")
    print(f"multiplier    : {mult}")
