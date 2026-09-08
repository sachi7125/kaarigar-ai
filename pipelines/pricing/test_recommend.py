"""Unit tests for reconciling the model's price band with the derived floor into
one suggested number."""
from __future__ import annotations

from pipelines.pricing.floor import FloorResult, MaterialCostResult
from pipelines.pricing.model import PricingResult
from pipelines.pricing.recommend import suggest_price


def _floor(floor_inr: float, known: bool = True) -> FloorResult:
    mat = MaterialCostResult(material="x", known=known, cost_inr=floor_inr * 0.8)
    return FloorResult(material_cost=mat, labour_hours=1, labour_wage_per_hour=60,
                       labour_cost_inr=floor_inr * 0.2, floor_inr=floor_inr, known=known)


def _pricing(point_inr: float) -> PricingResult:
    return PricingResult(point_inr=point_inr, band_low_inr=point_inr * 0.85,
                         band_high_inr=point_inr * 1.15, band_halfwidth_frac=0.15,
                         confidence="normal", confidence_reason="", seasonal_multiplier=1.0)


def test_model_wins_when_it_already_clears_the_floor():
    s = suggest_price(_pricing(500), _floor(300))
    assert s.value_inr == 500 and s.based_on == "model"


def test_floor_wins_when_model_undercuts_it():
    # the sandalwood-toy case: model said ~Rs.1138, floor was ~Rs.3700.
    s = suggest_price(_pricing(1138), _floor(3700))
    assert s.value_inr == 3700 and s.based_on == "floor"
    assert "1138" in s.note and "3700" in s.note


def test_unknown_floor_defers_to_the_model():
    s = suggest_price(_pricing(500), _floor(999999, known=False))
    assert s.value_inr == 500 and s.based_on == "model"


def test_never_below_either_number():
    for point, floor_inr in [(100, 400), (400, 100), (250, 250)]:
        s = suggest_price(_pricing(point), _floor(floor_inr))
        assert s.value_inr == max(point, floor_inr)
