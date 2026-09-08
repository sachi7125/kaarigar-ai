"""Unit tests for the three-bar SHAP-equivalent explanation (XGBoost native
pred_contribs, no `shap` package — see decision D16)."""
from __future__ import annotations

import math

import pipelines.pricing.shap_explain as shap_explain


def test_three_bars_are_finite_numbers():
    bars = shap_explain.explain("clay pottery", "clay", "medium", "north", 6)
    for v in (bars.material_inr, bars.demand_inr, bars.region_inr, bars.base_price_inr):
        assert math.isfinite(v)


def test_base_price_is_positive():
    bars = shap_explain.explain("clay pottery", "clay", "medium", "north", 6)
    assert bars.base_price_inr > 0
