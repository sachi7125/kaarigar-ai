"""XGBoost regression -> price band — mandated feature 3, step 3 (Roadmap Day 4).

Trained lazily on first use (like the Day-1 u2netp download): if no saved model
exists, `ml.train_pricing.train()` runs once against `pricing_reference.csv` and the
result is cached to `ml/models/`. The point estimate becomes a band of
+/- `pricing.band_halfwidth_frac` (config, default 15%), further widened for
**out-of-range honesty** whenever the input isn't well covered by the training data:
an unseen category/material, or fewer than `pricing.comparables_shown` genuine
same-category comparables. A wider band + `confidence="low"` is the only response to
that — never a confident-looking number the data can't support.

`size` (the spoken small/medium/large bucket) can optionally be refined with
`size_score` — the continuous 0-1 vision-coverage fraction behind that bucket (see
`attributes.AttributeResult.size_score`). Two items that both confirm as "medium"
can differ 3x in coverage; passing the real number instead of leaving it out lets
the model use that difference. Omitting it (the default) falls back to the bucket's
own representative midpoint — the same number every "medium" item used before this
existed — so this is a strict refinement, never a required new input.

CLI:  python -m pipelines.pricing.model <category> <material> <size> <region> [month] [size_score]
"""
from __future__ import annotations

import functools
import sys
from dataclasses import dataclass, field, asdict

import numpy as np
import pandas as pd
import xgboost as xgb

from pipelines.common import cfg_get
from pipelines.pricing.attributes import SIZE_REPRESENTATIVE
from pipelines.pricing.seasonal import seasonal_multiplier, active_seasons
from ml.train_pricing import (
    FEATURE_COLS, NUMERIC_COLS, ALL_COLS, MODEL_PATH, META_PATH, load_reference_df, train,
)

import json


@dataclass
class Comparable:
    category: str
    material: str
    size: str
    region: str
    season: str
    price_inr: float
    observed_or_synthesised: str


@dataclass
class PricingResult:
    point_inr: float
    band_low_inr: float
    band_high_inr: float
    band_halfwidth_frac: float
    confidence: str                 # "normal" | "low"
    confidence_reason: str
    seasonal_multiplier: float
    comparables: list[Comparable] = field(default_factory=list)

    def as_dict(self) -> dict:
        d = asdict(self)
        return d


def season_label(month: int) -> str:
    seasons = active_seasons(month)
    return seasons[0] if seasons else "regular"


@functools.lru_cache(maxsize=1)
def load_model_and_meta() -> tuple[xgb.XGBRegressor, dict]:
    if not MODEL_PATH.exists() or not META_PATH.exists():
        train()
    model = xgb.XGBRegressor()
    model.load_model(str(MODEL_PATH))
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    return model, meta


def make_feature_row(category: str, material: str, size: str, region: str,
                      season: str, meta: dict, size_score: float | None = None) -> pd.DataFrame:
    """One-row frame matching the training-time schema. A categorical value outside
    the trained categories becomes NaN (XGBoost's hist method handles missing
    categoricals natively) — the caller must separately flag this as low-confidence;
    this function only builds the row. `size_score=None` defaults to the bucket's
    own representative midpoint, recovering the pre-size_score behaviour exactly."""
    if size_score is None:
        size_score = SIZE_REPRESENTATIVE.get(size, 0.3)

    row = {"category": category, "material": material, "size": size,
          "region": region, "season": season, "size_score": size_score}
    df = pd.DataFrame([row])
    for col in FEATURE_COLS:
        cats = meta["categories"][col]
        df[col] = df[col].where(df[col].isin(cats))  # unseen value -> NaN first
        df[col] = pd.Categorical(df[col], categories=cats)
    for col in NUMERIC_COLS:
        df[col] = df[col].astype(float)
    return df


def find_comparables(category: str, material: str, size: str, region: str,
                     n: int | None = None) -> list[Comparable]:
    """Nearest reference rows: same category first, then prefer matching
    material/size/region among those, widening to the whole set if the category has
    too few rows (out-of-range honesty — never silently invent a comparable)."""
    if n is None:
        n = int(cfg_get("pricing.comparables_shown", 3))
    ref = load_reference_df()

    same_cat = ref[ref["category"] == category]
    pool = same_cat if len(same_cat) >= n else ref

    def score(r) -> int:
        return (int(r["material"] == material) + int(r["size"] == size)
                + int(r["region"] == region))

    ranked = pool.assign(_score=pool.apply(score, axis=1)) \
                .sort_values("_score", ascending=False).head(n)
    return [Comparable(category=r["category"], material=r["material"], size=r["size"],
                       region=r["region"], season=r["season"], price_inr=float(r["price_inr"]),
                       observed_or_synthesised=r["observed_or_synthesised"])
            for _, r in ranked.iterrows()]


def predict_band(category: str, material: str, size: str, region: str,
                 month: int, size_score: float | None = None) -> PricingResult:
    model, meta = load_model_and_meta()
    season = season_label(month)

    row = make_feature_row(category, material, size, region, season, meta, size_score)
    point = float(np.expm1(model.predict(row)[0]))

    unseen = [col for col, val in
             [("category", category), ("material", material), ("size", size), ("region", region)]
             if val not in meta["categories"].get(col, [])]

    comparables = find_comparables(category, material, size, region)
    sparse = len(comparables) < int(cfg_get("pricing.comparables_shown", 3))

    base_frac = float(cfg_get("pricing.band_halfwidth_frac", 0.15))
    if unseen or sparse:
        confidence = "low"
        reason = ("unseen: " + ", ".join(unseen) if unseen else "") + \
                 (" too few comparables" if sparse else "")
        halfwidth = min(0.6, base_frac * 2)
    else:
        confidence = "normal"
        reason = ""
        halfwidth = base_frac

    mult = seasonal_multiplier(category, month)
    point *= mult

    return PricingResult(
        point_inr=round(point, 2),
        band_low_inr=round(point * (1 - halfwidth), 2),
        band_high_inr=round(point * (1 + halfwidth), 2),
        band_halfwidth_frac=halfwidth,
        confidence=confidence, confidence_reason=reason.strip(),
        seasonal_multiplier=mult, comparables=comparables,
    )


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("usage: python -m pipelines.pricing.model <category> <material> <size> <region> [month] [size_score]")
        raise SystemExit(2)
    cat_arg, mat_arg, size_arg, region_arg = sys.argv[1:5]
    import datetime
    month_arg = int(sys.argv[5]) if len(sys.argv) > 5 else datetime.date.today().month
    score_arg = float(sys.argv[6]) if len(sys.argv) > 6 else None

    r = predict_band(cat_arg, mat_arg, size_arg, region_arg, month_arg, score_arg)
    print(f"band          : Rs.{r.band_low_inr:.0f} - Rs.{r.band_high_inr:.0f}  (point Rs.{r.point_inr:.0f})")
    print(f"confidence    : {r.confidence}  {r.confidence_reason}")
    print(f"seasonal mult : {r.seasonal_multiplier}")
    print("comparables   :")
    for c in r.comparables:
        print(f"  - {c.category} / {c.material} / {c.size} / {c.region} / {c.season} "
              f"-> Rs.{c.price_inr:.0f} ({c.observed_or_synthesised})")
