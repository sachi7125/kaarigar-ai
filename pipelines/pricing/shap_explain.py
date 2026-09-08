"""SHAP as three bars: material / demand / region — mandated feature 3, step 3
(Roadmap Day 4, decision D16).

Uses XGBoost's own tree-contribution output (`Booster.predict(..., pred_contribs=
True)`) instead of the separate `shap` package. For a tree ensemble this IS the
exact Shapley-value decomposition — not an approximation of one — so nothing is lost
by skipping the package. `shap` took ~20s just to `import` on this machine, the same
class of import-time tax this project has refused everywhere else (rembg,
transformers, the Gemini SDK — see D9/D11/D12); see D16 for the full rationale.

The three bars group the model's 6 features (5 categorical + the continuous
`size_score` added 6 Sep):
  - **material** — the `material` feature's own contribution
  - **region**    — the `region` feature's own contribution
  - **demand**    — `category` + `size` + `size_score` + `season` combined: together
                    the closest proxy among these features for "what it is, how big,
                    and when" (the roadmap's third bar)

Contributions are computed in the model's log1p(price) training space, then
converted to an approximate rupee delta per bar (bias-only price vs. bias+that
bar's contribution). Because `expm1` is nonlinear, the three rupee deltas do not
sum exactly to (point estimate - bias price) — they are a visualisation aid, not an
exact accounting identity, and are presented that way.

CLI:  python -m pipelines.pricing.shap_explain <category> <material> <size> <region> [month] [size_score]
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, asdict

import numpy as np
import xgboost as xgb

from pipelines.pricing.model import load_model_and_meta, make_feature_row, season_label
from ml.train_pricing import ALL_COLS


@dataclass
class ThreeBars:
    material_inr: float
    demand_inr: float
    region_inr: float
    base_price_inr: float   # price implied by the bias term alone, before any bar

    def as_dict(self) -> dict:
        return asdict(self)


def explain(category: str, material: str, size: str, region: str, month: int,
           size_score: float | None = None) -> ThreeBars:
    model, meta = load_model_and_meta()
    season = season_label(month)
    row = make_feature_row(category, material, size, region, season, meta, size_score)

    dmat = xgb.DMatrix(row, enable_categorical=True)
    contribs = model.get_booster().predict(dmat, pred_contribs=True)[0]
    by_feature = dict(zip(ALL_COLS, contribs[:-1]))
    bias = float(contribs[-1])

    base_price = float(np.expm1(bias))

    def rupee_delta(log_contrib: float) -> float:
        return float(np.expm1(bias + log_contrib)) - base_price

    return ThreeBars(
        material_inr=round(rupee_delta(by_feature["material"]), 2),
        demand_inr=round(rupee_delta(by_feature["category"] + by_feature["size"]
                                     + by_feature["size_score"] + by_feature["season"]), 2),
        region_inr=round(rupee_delta(by_feature["region"]), 2),
        base_price_inr=round(base_price, 2),
    )


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("usage: python -m pipelines.pricing.shap_explain <category> <material> <size> <region> [month] [size_score]")
        raise SystemExit(2)
    cat_arg, mat_arg, size_arg, region_arg = sys.argv[1:5]
    import datetime
    month_arg = int(sys.argv[5]) if len(sys.argv) > 5 else datetime.date.today().month
    score_arg = float(sys.argv[6]) if len(sys.argv) > 6 else None

    bars = explain(cat_arg, mat_arg, size_arg, region_arg, month_arg, score_arg)
    print(f"base (bias only) : Rs.{bars.base_price_inr:.0f}")
    print(f"material          : {'+' if bars.material_inr >= 0 else ''}Rs.{bars.material_inr:.0f}")
    print(f"demand            : {'+' if bars.demand_inr >= 0 else ''}Rs.{bars.demand_inr:.0f}")
    print(f"region            : {'+' if bars.region_inr >= 0 else ''}Rs.{bars.region_inr:.0f}")
