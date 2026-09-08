"""Reconcile the market-comparable price band (`model.py`) with the derived
fair-price floor (`floor.py`) into the ONE number actually shown to the artisan.
(Day 4 follow-up, 6 Sep.)

These two systems are built independently — one from comparable listings, one from
material rate x weight + labour — and testing found they can disagree: 34 of 100
stress-test scenarios had the model's own point estimate sitting BELOW its derived
floor (worst case a 21x gap on a sandalwood wooden toy, since fixed separately by
category-aware weights in `floor.py`). Rather than trying to force the two datasets
into permanent agreement, `suggest_price` picks the higher of the two at query time:
a price that doesn't even cover materials and labour is never the number to lead
with, no matter what comparable listings suggest. When the floor is unknown (D13's
"out-of-range honesty" case), there is nothing to reconcile against, so the model's
point estimate is used as-is.

This never blocks anything — same as `floor.check_against_floor` — it just decides
which of two honestly-computed numbers to put in front of her first.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, asdict

from pipelines.pricing.floor import FloorResult, fair_price_floor
from pipelines.pricing.model import PricingResult, predict_band


@dataclass
class PriceSuggestion:
    value_inr: float
    based_on: str   # "model" | "floor"
    note: str

    def as_dict(self) -> dict:
        return asdict(self)


def suggest_price(pricing: PricingResult, floor: FloorResult) -> PriceSuggestion:
    if not floor.known:
        return PriceSuggestion(
            value_inr=pricing.point_inr, based_on="model",
            note="floor unknown (material or size not confirmed) — using the market-comparable estimate",
        )
    if floor.floor_inr > pricing.point_inr:
        return PriceSuggestion(
            value_inr=floor.floor_inr, based_on="floor",
            note=(f"the market-comparable estimate (₹{pricing.point_inr:.0f}) was below the cost of "
                 f"materials + your time (₹{floor.floor_inr:.0f}) — raised to the floor"),
        )
    return PriceSuggestion(
        value_inr=pricing.point_inr, based_on="model",
        note="market-comparable estimate already clears the floor",
    )


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("usage: python -m pipelines.pricing.recommend <category> <material> <size> <region> "
              "[month] [size_score]")
        raise SystemExit(2)
    cat_arg, mat_arg, size_arg, region_arg = sys.argv[1:5]
    import datetime
    month_arg = int(sys.argv[5]) if len(sys.argv) > 5 else datetime.date.today().month
    score_arg = float(sys.argv[6]) if len(sys.argv) > 6 else None

    band = predict_band(cat_arg, mat_arg, size_arg, region_arg, month_arg, score_arg)
    floor = fair_price_floor(mat_arg, size_arg, score_arg, cat_arg)
    suggestion = suggest_price(band, floor)

    print(f"model point : Rs.{band.point_inr:.0f}  (band Rs.{band.band_low_inr:.0f}-{band.band_high_inr:.0f})")
    print(f"floor       : Rs.{floor.floor_inr:.0f}  (known={floor.known})")
    print(f"SUGGESTED   : Rs.{suggestion.value_inr:.0f}  (based_on={suggestion.based_on})")
    print(f"note        : {suggestion.note}")
