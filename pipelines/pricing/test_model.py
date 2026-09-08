"""Unit tests for the XGBoost price band + comparables. Trains lazily against the
real (small) pricing_reference.csv on first use, same as the u2netp lazy download —
these run in well under a second once the model is cached."""
from __future__ import annotations

import pipelines.pricing.model as model


def test_known_combo_gets_normal_confidence():
    r = model.predict_band("clay pottery", "clay", "medium", "north", 6)
    assert r.confidence == "normal"
    assert r.band_low_inr < r.point_inr < r.band_high_inr
    assert len(r.comparables) == 3


def test_unseen_category_gets_low_confidence_and_wider_band():
    r = model.predict_band("glass beadwork", "clay", "medium", "north", 6)
    assert r.confidence == "low"
    assert "category" in r.confidence_reason
    assert r.band_halfwidth_frac > 0.15


def test_band_is_never_inverted():
    for cat in ("clay pottery", "banarasi silk saree", "unseen thing"):
        r = model.predict_band(cat, "clay", "medium", "north", 6)
        assert r.band_low_inr <= r.point_inr <= r.band_high_inr
        assert r.point_inr > 0


def test_comparables_prefer_same_category():
    comps = model.find_comparables("clay pottery", "clay", "medium", "north")
    assert all(c.category == "clay pottery" for c in comps)


def test_comparables_widen_for_a_category_with_too_few_rows():
    # every real category has >= 3 rows in the reference set, so force the widen
    # path with a category name that matches nothing.
    comps = model.find_comparables("no such category", "clay", "medium", "north")
    assert len(comps) == 3   # falls back to the whole reference set, not empty


def test_seasonal_multiplier_moves_the_diwali_point_up():
    off_season = model.predict_band("terracotta diya", "terracotta", "small", "west", 6)
    diwali = model.predict_band("terracotta diya", "terracotta", "small", "west", 10)
    assert diwali.seasonal_multiplier > off_season.seasonal_multiplier
    assert diwali.point_inr > off_season.point_inr


def test_never_asks_for_or_takes_a_cost_input():
    import inspect
    params = list(inspect.signature(model.predict_band).parameters)
    assert not any("cost" in p or "price" in p for p in params)
