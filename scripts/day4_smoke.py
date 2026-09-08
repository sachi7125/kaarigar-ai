"""Day 4 smoke test — verifies the gate: photo + voice -> price band with a plain
explanation, no cost question asked, the floor visibly refusing an underpriced
suggestion, material type never inferred from photo pixels, and the rate's
date + source on screen.

Reuses the Day-1 synthetic "bad phone photo" generator so this needs no real camera
or microphone. Run:  python -m scripts.day4_smoke
"""
from __future__ import annotations

from pathlib import Path

from scripts.day1_smoke import _make_bad_photo
from pipelines.pricing.attributes import suggest_attributes
from pipelines.pricing.floor import fair_price_floor, check_against_floor
from pipelines.pricing.model import predict_band
from pipelines.pricing.shap_explain import explain
from pipelines.pricing.recommend import suggest_price

OUT = Path("results/day4")
OUT.mkdir(parents=True, exist_ok=True)

TRANSCRIPT = "ये एक मिट्टी की मटकी है, हाथ से बनी, मध्यम आकार"
CATEGORY = "clay pottery"
REGION = "north"
MONTH = 10  # Diwali season, to also exercise the seasonal multiplier


def main() -> int:
    photo = OUT / "raw_input.png"
    _make_bad_photo(photo)
    print(f"[photo] wrote {photo}")

    attrs = suggest_attributes(str(photo), TRANSCRIPT, lang="hi", recorder=None)
    print(f"\n[attrs] material={attrs.material or '(none)'} ({attrs.material_source})  "
          f"size={attrs.size_class or '(unknown)'} ({attrs.size_source}, "
          f"score={attrs.size_score:.3f})  finish={attrs.finish}")
    assert attrs.material == "clay", "material must come from the transcript, not the photo"
    # Prove it: a completely different (blank) photo must not change the material,
    # since material is never derived from pixels (D2).
    blank = OUT / "blank.png"
    import cv2, numpy as np
    cv2.imwrite(str(blank), np.zeros((400, 400, 3), dtype="uint8"))
    attrs_blank_photo = suggest_attributes(str(blank), TRANSCRIPT, lang="hi", recorder=None)
    assert attrs_blank_photo.material == attrs.material, \
        "material changed when only the photo changed — it must come from voice alone"
    print("[attrs] confirmed: material is unchanged when the photo changes (voice-only, D2)")

    floor = fair_price_floor(attrs.material, attrs.size_class, attrs.size_score, CATEGORY)
    print(f"\n[floor] material cost = Rs.{floor.material_cost.cost_inr:.0f} "
          f"({floor.material_cost.rate_inr_per_kg}/kg x {floor.material_cost.weight_kg}kg)")
    print(f"[floor] rate date={floor.material_cost.rate_date}  source={floor.material_cost.rate_source}")
    assert floor.material_cost.rate_date and floor.material_cost.rate_source, \
        "rate date + source must be on screen"
    print(f"[floor] labour cost = Rs.{floor.labour_cost_inr:.0f} "
          f"({floor.labour_hours}h x Rs.{floor.labour_wage_per_hour}/h)")
    print(f"[floor] FLOOR = Rs.{floor.floor_inr:.0f}")

    underpriced = floor.floor_inr * 0.5
    check = check_against_floor(underpriced, floor)
    print(f"\n[floor] artisan suggests Rs.{underpriced:.0f} -> below_floor={check.is_below_floor}")
    print(f"[floor] {check.message}")
    assert check.is_below_floor is True, "GATE: the floor must visibly refuse an underpriced suggestion"

    fine = floor.floor_inr * 2
    check_ok = check_against_floor(fine, floor)
    assert check_ok.is_below_floor is False, "the floor must never block — only warn"
    print(f"[floor] artisan suggests Rs.{fine:.0f} -> below_floor={check_ok.is_below_floor} (never blocks)")

    band = predict_band(CATEGORY, attrs.material, attrs.size_class, REGION, MONTH, attrs.size_score)
    # Roadmap Day 4: "comparables evidence strip ... shown BEFORE the model number" —
    # she sees the evidence first, then the number, not the other way round.
    print("\n[price] comparables (shown before the model number):")
    for c in band.comparables:
        print(f"  - {c.category} / {c.material} / {c.size} / {c.region} -> "
              f"Rs.{c.price_inr:.0f} ({c.observed_or_synthesised})")
    print(f"[price] band = Rs.{band.band_low_inr:.0f} - Rs.{band.band_high_inr:.0f}  "
          f"(point Rs.{band.point_inr:.0f}, confidence={band.confidence})")
    print(f"[price] seasonal multiplier = {band.seasonal_multiplier} (Diwali month)")

    bars = explain(CATEGORY, attrs.material, attrs.size_class, REGION, MONTH, attrs.size_score)
    print(f"\n[explain] material={'+' if bars.material_inr>=0 else ''}Rs.{bars.material_inr:.0f}  "
          f"demand={'+' if bars.demand_inr>=0 else ''}Rs.{bars.demand_inr:.0f}  "
          f"region={'+' if bars.region_inr>=0 else ''}Rs.{bars.region_inr:.0f}")

    suggestion = suggest_price(band, floor)
    print(f"\n[suggest] SUGGESTED PRICE = Rs.{suggestion.value_inr:.0f}  (based_on={suggestion.based_on})")
    print(f"[suggest] {suggestion.note}")

    for q in attrs.questions_asked:
        lowered = q.lower()
        assert "कीमत" not in q and "price" not in lowered and "cost" not in lowered, \
            f"GATE VIOLATION: a confirmation question mentioned price/cost: {q!r}"
    print("\n[gate] no cost question anywhere: OK")
    print("[gate] material not inferred from photo pixels: OK")
    print("[gate] floor visibly refuses an underpriced suggestion: OK")
    print("[gate] rate date + source on screen: OK")
    print("\nDay 4 gate: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
