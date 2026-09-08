"""Fair-price floor — mandated feature 3, step 2 (Roadmap Day 4, decision D13).

The floor is `derived material cost + labour cost`. There is no cost question
anywhere:
  - material cost = (material type, from her voice, via `attributes.extract_material`)
    x (rate INR/kg, from the dated `material_rates.csv`) x (weight_kg, a rough
    estimate in `size_estimates.csv` keyed by BOTH the material's `density_class`
    and size_class — no scale in the photo)
  - labour cost = (hours, the same table) x `pricing.floor_wage_per_hour`
    (config.yaml, conservative)

`density_class` (precious/metal/bulk, read off the material's row in
`material_rates.csv`) matters because size_class alone is not a weight: testing on
6 Sep found a "medium" silver item costed out at 1.0kg of silver (a Rs.250,300
floor) using a single size-class weight table — a medium silver pendant/necklace
actually weighs tens of grams. `bulk` (clay, textile, wood) keeps kg-scale weights;
`metal` (brass/copper) sits in between; `precious` (silver) is gram-scale.

A second round of testing (also 6 Sep) found `density_class` alone still isn't
enough: a "large wooden toy" was costed at 2kg of sandalwood (~Rs.20,000 of material
for a toy) because wood's `bulk` bucket assumes up to 3kg — reasonable for a saree,
absurd for a toy. Weight fundamentally depends on the OBJECT, not just the material's
density class, so `data/reference/category_weight_overrides.csv` gives a specific
(category, size_class) -> weight/hours wherever available, and `derive_material_cost`
/`derive_labour_cost` take an optional `category` to use it. No override for that
category falls back to the generic density_class table — out-of-range honesty, an
unlisted category still gets an answer, just a less specific one.

Within a bucket, weight_kg/hours can additionally be refined by the optional
`size_score` (the raw 0-1 frame-coverage fraction behind `size_class` — see
`attributes.AttributeResult.size_score`): two items that both confirm as "medium"
can differ 3x in coverage (16% vs 44%), and today both get costed identically.
Piecewise-linear interpolation between the small/medium/large anchor points (at
`attributes.SIZE_REPRESENTATIVE`) uses that difference instead of discarding it.
`size_score=None` (no vision reading, or she rejected the size confirmation) falls
back to the flat per-bucket anchor value exactly as before this existed.

The floor only WARNS on an underpriced suggestion; it never blocks or overrides her
own pricing (D3, D13) — `check_against_floor` returns a warning, and the caller
decides what to show, but nothing here prevents publishing at any price.

An unknown material (not in the rate table) or unknown size (never confirmed) means
the floor cannot be computed with confidence — `MaterialCostResult.known` /
`FloorResult.known` say so, so the caller can fall back to "wider band, low
confidence" (out-of-range honesty) instead of inventing a number.

CLI:  python -m pipelines.pricing.floor <material> <size_class> [size_score] [category] [suggested_price]
"""
from __future__ import annotations

import csv
import functools
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

from pipelines.common import cfg_get, REPO_ROOT
from pipelines.pricing.attributes import SIZE_REPRESENTATIVE

_RATES_PATH = REPO_ROOT / "data" / "reference" / "material_rates.csv"
_SIZES_PATH = REPO_ROOT / "data" / "reference" / "size_estimates.csv"
_CATEGORY_WEIGHTS_PATH = REPO_ROOT / "data" / "reference" / "category_weight_overrides.csv"
_SIZE_ORDER = ["small", "medium", "large"]


@functools.lru_cache(maxsize=1)
def load_material_rates() -> dict[str, dict]:
    """material -> {unit, rate_inr, date, source, confidence, density_class, notes}."""
    if not _RATES_PATH.exists():
        return {}
    with open(_RATES_PATH, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(_skip_comments(fh))]
    return {r["material"]: r for r in rows}


@functools.lru_cache(maxsize=1)
def load_size_estimates() -> dict[tuple[str, str], dict]:
    """(density_class, size_class) -> {weight_kg, hours, note}."""
    if not _SIZES_PATH.exists():
        return {}
    with open(_SIZES_PATH, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(_skip_comments(fh))]
    return {(r["density_class"], r["size_class"]): r for r in rows}


@functools.lru_cache(maxsize=1)
def load_category_weights() -> dict[tuple[str, str], dict]:
    """(category, size_class) -> {weight_kg, hours, note}. Overrides the generic
    density_class table wherever a specific category is listed."""
    if not _CATEGORY_WEIGHTS_PATH.exists():
        return {}
    with open(_CATEGORY_WEIGHTS_PATH, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(_skip_comments(fh))]
    return {(r["category"].lower(), r["size_class"]): r for r in rows}


def _size_row(density_class: str, size_class: str) -> dict | None:
    key = ((density_class or "").strip().lower(), (size_class or "").strip().lower())
    return load_size_estimates().get(key)


def _category_row(category: str | None, size_class: str) -> dict | None:
    if not category:
        return None
    key = (category.strip().lower(), (size_class or "").strip().lower())
    return load_category_weights().get(key)


def _anchors(category: str | None, density_class: str, field: str) -> list[tuple[float, float]]:
    """Anchor points for interpolation: the category's own small/medium/large
    values if that category has ANY override rows, else the generic density_class
    table. A category with a partial override (missing a size) still counts as
    "has one" and won't silently mix category and generic anchors for the other
    sizes — author category_weight_overrides.csv with all three sizes per category."""
    if category and any(_category_row(category, sc) for sc in _SIZE_ORDER):
        return sorted((SIZE_REPRESENTATIVE[sc], float(row[field]))
                     for sc in _SIZE_ORDER if (row := _category_row(category, sc)) is not None)
    return sorted((SIZE_REPRESENTATIVE[sc], float(row[field]))
                 for sc in _SIZE_ORDER if (row := _size_row(density_class, sc)) is not None)


def _interpolated_value(category: str | None, density_class: str, size_class: str,
                        size_score: float | None, field: str) -> float:
    """`field` is "weight_kg" or "hours". Piecewise-linear across the small/medium/
    large anchor points (at SIZE_REPRESENTATIVE), preferring a category-specific
    table over the generic density_class one (see `_anchors`). Falls back to the
    flat per-bucket anchor when size_score is unavailable — a strict superset of
    the old behaviour, not a new required input."""
    if size_score is None:
        row = _category_row(category, size_class) or _size_row(density_class, size_class)
        return float(row[field]) if row else 0.0

    anchors = _anchors(category, density_class, field)
    if not anchors:
        return 0.0
    if size_score <= anchors[0][0]:
        return anchors[0][1]
    if size_score >= anchors[-1][0]:
        return anchors[-1][1]
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if x0 <= size_score <= x1:
            return y0 + (size_score - x0) / (x1 - x0) * (y1 - y0)
    return anchors[-1][1]  # unreachable, defensive


def _skip_comments(fh):
    for line in fh:
        if not line.lstrip().startswith("#"):
            yield line


@dataclass
class MaterialCostResult:
    material: str
    known: bool                 # False if material or (density_class, size_class) is unresolved
    rate_inr_per_kg: float = 0.0
    rate_date: str = ""
    rate_source: str = ""
    rate_confidence: str = ""   # "live" | "typical-range"
    density_class: str = ""     # "precious" | "metal" | "bulk"
    weight_kg: float = 0.0
    cost_inr: float = 0.0

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class FloorResult:
    material_cost: MaterialCostResult
    labour_hours: float
    labour_wage_per_hour: float
    labour_cost_inr: float
    floor_inr: float
    known: bool   # False if material or size_class is unknown -> caller should widen the band

    def as_dict(self) -> dict:
        d = asdict(self)
        d["material_cost"] = self.material_cost.as_dict()
        return d


@dataclass
class FloorCheck:
    floor: FloorResult
    suggested_price: float
    is_below_floor: bool
    message: str

    def as_dict(self) -> dict:
        d = asdict(self)
        d["floor"] = self.floor.as_dict()
        return d


def derive_material_cost(material: str, size_class: str, size_score: float | None = None,
                         category: str | None = None) -> MaterialCostResult:
    rates = load_material_rates()
    row = rates.get((material or "").strip().lower())
    if not row:
        return MaterialCostResult(material=material or "", known=False)

    density_class = row["density_class"]
    size_row = _category_row(category, size_class) or _size_row(density_class, size_class)
    weight_kg = (_interpolated_value(category, density_class, size_class, size_score, "weight_kg")
                if size_row else 0.0)
    rate = float(row["rate_inr"])
    return MaterialCostResult(
        material=material, known=size_row is not None, rate_inr_per_kg=rate,
        rate_date=row["date"], rate_source=row["source"],
        rate_confidence=row["confidence"], density_class=density_class,
        weight_kg=round(weight_kg, 4), cost_inr=round(rate * weight_kg, 2),
    )


def derive_labour_cost(material: str, size_class: str, size_score: float | None = None,
                       category: str | None = None) -> tuple[float, float, float]:
    """(hours, wage_per_hour, cost_inr). Hours vary by category/density_class too —
    e.g. silversmithing or fine weaving is slower, more detailed work per size than
    shaping clay."""
    rates = load_material_rates()
    row = rates.get((material or "").strip().lower())
    density_class = row["density_class"] if row else ""
    size_row = _category_row(category, size_class) or _size_row(density_class, size_class)
    hours = (_interpolated_value(category, density_class, size_class, size_score, "hours")
             if size_row else 0.0)
    wage = float(cfg_get("pricing.floor_wage_per_hour", 60))
    return round(hours, 4), wage, round(hours * wage, 2)


def fair_price_floor(material: str, size_class: str, size_score: float | None = None,
                     category: str | None = None) -> FloorResult:
    mat_cost = derive_material_cost(material, size_class, size_score, category)
    hours, wage, labour_cost = derive_labour_cost(material, size_class, size_score, category)
    known = mat_cost.known and hours > 0
    return FloorResult(
        material_cost=mat_cost, labour_hours=hours, labour_wage_per_hour=wage,
        labour_cost_inr=labour_cost, floor_inr=round(mat_cost.cost_inr + labour_cost, 2),
        known=known,
    )


def check_against_floor(suggested_price: float, floor: FloorResult) -> FloorCheck:
    """WARN only — never blocks. `is_below_floor` is False (not "safe") when the
    floor itself is unknown, since there is nothing to compare against."""
    if not floor.known:
        return FloorCheck(floor=floor, suggested_price=suggested_price, is_below_floor=False,
                          message="Floor unknown (material or size not confirmed) — "
                                  "showing the price band with lower confidence instead.")
    below = suggested_price < floor.floor_inr
    if below:
        msg = (f"This is below the estimated cost of materials (₹{floor.material_cost.cost_inr:.0f}) "
               f"plus your time (₹{floor.labour_cost_inr:.0f}) — about ₹{floor.floor_inr:.0f} total. "
               f"You can still list at this price if you choose.")
    else:
        msg = f"Above the estimated floor of ₹{floor.floor_inr:.0f}."
    return FloorCheck(floor=floor, suggested_price=suggested_price, is_below_floor=below, message=msg)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("usage: python -m pipelines.pricing.floor <material> <size_class> [size_score] [category] [suggested_price]")
        raise SystemExit(2)
    material_arg, size_arg = sys.argv[1], sys.argv[2]
    score_arg = float(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3].lower() != "none" else None
    category_arg = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4].lower() != "none" else None
    f = fair_price_floor(material_arg, size_arg, score_arg, category_arg)
    print(f"material cost : Rs.{f.material_cost.cost_inr:.2f}  "
          f"({f.material_cost.rate_inr_per_kg}/kg x {f.material_cost.weight_kg}kg "
          f"[{f.material_cost.density_class}{', category=' + category_arg if category_arg else ''}], "
          f"rate dated {f.material_cost.rate_date}, source: {f.material_cost.rate_source})")
    print(f"labour cost   : Rs.{f.labour_cost_inr:.0f}  ({f.labour_hours}h x Rs.{f.labour_wage_per_hour}/h)")
    print(f"FLOOR         : Rs.{f.floor_inr:.2f}   (known={f.known}, size_score={score_arg})")
    if len(sys.argv) > 5:
        check = check_against_floor(float(sys.argv[5]), f)
        print(f"\nsuggested Rs.{check.suggested_price:.0f} -> below_floor={check.is_below_floor}")
        print(check.message)
