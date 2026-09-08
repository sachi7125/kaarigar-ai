"""Unit tests for the bounded seasonal multiplier."""
from __future__ import annotations

import pipelines.pricing.seasonal as seasonal


def test_diwali_boosts_diya_in_season():
    assert seasonal.seasonal_multiplier("terracotta diya", 10) > 1.0


def test_diya_regular_month_no_boost():
    assert seasonal.seasonal_multiplier("terracotta diya", 6) == 1.0


def test_wedding_boosts_saree_in_season():
    assert seasonal.seasonal_multiplier("banarasi silk saree", 12) > 1.0


def test_unmatched_category_no_boost_even_in_season():
    assert seasonal.seasonal_multiplier("bamboo basket", 10) == 1.0


def test_multiplier_never_exceeds_configured_cap(monkeypatch):
    monkeypatch.setattr(seasonal, "cfg_get", lambda path, default=None: 0.05)
    mult = seasonal.seasonal_multiplier("terracotta diya", 10)   # raw boost is 0.20
    assert mult <= 1.05 + 1e-9


def test_active_seasons_reports_correctly():
    assert "diwali" in seasonal.active_seasons(10)
    assert "wedding" in seasonal.active_seasons(1)
    assert seasonal.active_seasons(6) == []
