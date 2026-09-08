"""Unit tests for the derived material cost + labour -> fair-price floor.
No cost is ever asked here; every number comes from the reference tables."""
from __future__ import annotations

import pipelines.pricing.floor as floor


def test_known_material_and_size_derives_a_cost():
    r = floor.derive_material_cost("clay", "medium")
    assert r.known is True
    assert r.weight_kg == 1.0
    assert r.rate_inr_per_kg == 10.0
    assert r.cost_inr == 10.0
    assert r.rate_date and r.rate_source


def test_unknown_material_flagged_not_fabricated():
    r = floor.derive_material_cost("unobtainium", "medium")
    assert r.known is False
    assert r.cost_inr == 0.0


def test_labour_cost_uses_config_wage(monkeypatch):
    monkeypatch.setattr(floor, "cfg_get", lambda path, default=None: 60 if "wage" in path else default)
    hours, wage, cost = floor.derive_labour_cost("clay", "small")
    assert hours == 2.0 and wage == 60.0 and cost == 120.0


def test_precious_metal_weight_is_gram_scale_not_kg_scale():
    # regression test for the 6 Sep bug: a "medium" silver item must NOT cost out
    # at 1.0kg of silver (that was a Rs.250,300 floor for a piece that should
    # weigh tens of grams).
    r = floor.derive_material_cost("silver", "medium")
    assert r.known is True
    assert r.density_class == "precious"
    assert r.weight_kg < 0.2
    assert r.cost_inr < 50000


def test_bulk_material_still_uses_kg_scale_weight():
    r = floor.derive_material_cost("clay", "medium")
    assert r.density_class == "bulk"
    assert r.weight_kg == 1.0


def test_metal_is_between_precious_and_bulk():
    silver = floor.derive_material_cost("silver", "medium")
    brass = floor.derive_material_cost("brass", "medium")
    clay = floor.derive_material_cost("clay", "medium")
    assert silver.weight_kg < brass.weight_kg < clay.weight_kg


# --------------------------------------------------- size_score interpolation
def test_no_size_score_falls_back_to_flat_bucket_value():
    r = floor.derive_material_cost("clay", "medium")   # size_score defaults to None
    assert r.weight_kg == 1.0


def test_size_score_at_bucket_center_matches_flat_value():
    from pipelines.pricing.attributes import SIZE_REPRESENTATIVE
    r = floor.derive_material_cost("clay", "medium", SIZE_REPRESENTATIVE["medium"])
    assert r.weight_kg == 1.0


def test_barely_medium_and_barely_large_differ_within_the_same_spoken_bucket():
    # both confirm as "medium" by voice, but their vision coverage is very
    # different — the whole point of adding size_score.
    barely_medium = floor.derive_material_cost("clay", "medium", 0.16)
    barely_large = floor.derive_material_cost("clay", "medium", 0.44)
    medium_small = floor.derive_material_cost("clay", "small")
    medium_large = floor.derive_material_cost("clay", "large")
    assert medium_small.weight_kg < barely_medium.weight_kg < barely_large.weight_kg < medium_large.weight_kg


def test_interpolation_is_clamped_at_the_extremes():
    tiny_score = floor.derive_material_cost("clay", "small", 0.0)
    huge_score = floor.derive_material_cost("clay", "large", 1.0)
    small_flat = floor.derive_material_cost("clay", "small")
    large_flat = floor.derive_material_cost("clay", "large")
    assert tiny_score.weight_kg == small_flat.weight_kg
    assert huge_score.weight_kg == large_flat.weight_kg


def test_interpolation_also_applies_to_labour_hours():
    barely_medium = floor.derive_labour_cost("clay", "medium", 0.16)
    barely_large = floor.derive_labour_cost("clay", "medium", 0.44)
    assert barely_medium[0] < barely_large[0]   # hours


def test_fair_price_floor_accepts_size_score_end_to_end():
    flat = floor.fair_price_floor("clay", "medium")
    scored = floor.fair_price_floor("clay", "medium", 0.44)
    assert scored.floor_inr > flat.floor_inr


# ------------------------------------------------ category weight overrides
def test_category_override_beats_generic_density_class():
    # regression test for the 6 Sep bug: a "large wooden toy" was costed at 2kg of
    # sandalwood (generic bulk-large) — a real toy uses far less material than a
    # saree or a sack of jute even though both are "bulk".
    generic = floor.derive_material_cost("sandalwood", "large")            # no category
    toy = floor.derive_material_cost("sandalwood", "large", category="wooden toy")
    assert toy.weight_kg < generic.weight_kg
    assert toy.cost_inr < generic.cost_inr / 5   # was a >7x gap; assert it's not marginal


def test_unlisted_category_falls_back_to_generic_density_class():
    r = floor.derive_material_cost("clay", "medium", category="a totally novel craft")
    assert r.weight_kg == 1.0   # unchanged from the no-category generic bulk value


def test_category_override_also_applies_with_size_score_interpolation():
    small = floor.derive_material_cost("sandalwood", "small", 0.05, category="wooden toy")
    large = floor.derive_material_cost("sandalwood", "large", 0.8, category="wooden toy")
    assert small.weight_kg < large.weight_kg
    assert large.weight_kg < 1.0   # still nowhere near the generic bulk-large 3.0kg


def test_category_override_applies_to_labour_hours_too():
    generic_hours, _, _ = floor.derive_labour_cost("sandalwood", "large")
    toy_hours, _, _ = floor.derive_labour_cost("sandalwood", "large", category="wooden toy")
    assert toy_hours < generic_hours


def test_fair_price_floor_accepts_category_end_to_end():
    f = floor.fair_price_floor("sandalwood", "large", 0.6, "wooden toy")
    assert f.known is True
    assert f.floor_inr < 5000   # sanity bound well below the old ~Rs.27,700


def test_fair_price_floor_sums_material_and_labour():
    f = floor.fair_price_floor("clay", "medium")
    assert f.known is True
    assert f.floor_inr == round(f.material_cost.cost_inr + f.labour_cost_inr, 2)


def test_floor_unknown_when_material_missing():
    f = floor.fair_price_floor("unobtainium", "medium")
    assert f.known is False


def test_floor_unknown_when_size_missing():
    f = floor.fair_price_floor("clay", "")
    assert f.known is False


# --------------------------------------------------------- check_against_floor
def test_below_floor_warns_but_never_blocks():
    f = floor.fair_price_floor("clay", "medium")
    check = floor.check_against_floor(1, f)   # absurdly low
    assert check.is_below_floor is True
    assert "still list" in check.message.lower() or "you can" in check.message.lower()
    # the function only returns a warning object — nothing raises or refuses


def test_above_floor_not_flagged():
    f = floor.fair_price_floor("clay", "medium")
    check = floor.check_against_floor(f.floor_inr + 500, f)
    assert check.is_below_floor is False


def test_unknown_floor_is_not_treated_as_below():
    f = floor.fair_price_floor("unobtainium", "medium")
    check = floor.check_against_floor(1, f)
    assert check.is_below_floor is False
    assert "unknown" in check.message.lower() or "confidence" in check.message.lower()


def test_never_prompts_for_a_cost():
    # the whole module's public surface takes material + size_class only —
    # asserting the floor functions never accept/require a price/cost argument.
    import inspect
    for fn in (floor.derive_material_cost, floor.derive_labour_cost, floor.fair_price_floor):
        params = list(inspect.signature(fn).parameters)
        assert not any("cost" in p or "price" in p for p in params)
