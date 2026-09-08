"""Train XGBoost on the pricing reference set; save the model + feature metadata.
(Roadmap Day 4.)

Features are `category`, `material`, `size`, `region`, `season` (categorical, via
XGBoost's native `enable_categorical` rather than manual one-hot, so
`pipelines.pricing.shap_explain` can attribute a prediction back to named columns
instead of a pile of one-hot dummies) plus `size_score` (numeric, added 6 Sep): the
continuous 0-1 vision-coverage fraction that `size` buckets. Two items can both
confirm as "medium" by voice yet differ 3x in actual frame coverage — `size_score`
lets the model (and, separately, `pipelines.pricing.floor`'s weight/hours
interpolation) use that difference instead of discarding it. `ALL_COLS` is the
canonical column order shared with `model.py`/`shap_explain.py` so a feature index
never silently drifts between training and inference.

The reference set is small (see data_sources.md — currently 58 rows, entirely
"synthesised") and the target spans two orders of magnitude (₹20 diyas to ₹15,000
silk sarees), so training happens on `log1p(price)` for stability; `model.py` inverts
with `expm1` at prediction time. Depth and estimator count are kept low to avoid
memorising a dataset this small.

Training is lazy — `model.py` calls `train()` on first use if no saved model exists,
the same "build once, cache" pattern as the Day-1 u2netp model download. Re-run this
directly whenever `pricing_reference.csv` changes:

    python -m ml.train_pricing

Writing accepted/declined offers back as transacted rows for scheduled retraining
needs the offer system (Day 5) and is not built here — this only trains on the
static reference set.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

from pipelines.common import REPO_ROOT

REFERENCE_PATH = REPO_ROOT / "data" / "reference" / "pricing_reference.csv"
MODEL_DIR = REPO_ROOT / "ml" / "models"
MODEL_PATH = MODEL_DIR / "pricing_xgb.json"
META_PATH = MODEL_DIR / "pricing_meta.json"

FEATURE_COLS = ["category", "material", "size", "region", "season"]   # categorical
NUMERIC_COLS = ["size_score"]                                         # continuous
ALL_COLS = FEATURE_COLS + NUMERIC_COLS


def _skip_comments(fh):
    for line in fh:
        if not line.lstrip().startswith("#"):
            yield line


def load_reference_df() -> pd.DataFrame:
    with open(REFERENCE_PATH, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(_skip_comments(fh)))
    df = pd.DataFrame(rows)
    df["price_inr"] = df["price_inr"].astype(float)
    for col in FEATURE_COLS:
        df[col] = df[col].astype("category")
    for col in NUMERIC_COLS:
        df[col] = df[col].astype(float)
    return df


def train(df: pd.DataFrame | None = None) -> xgb.XGBRegressor:
    if df is None:
        df = load_reference_df()

    X = df[ALL_COLS]
    y = np.log1p(df["price_inr"].to_numpy())

    model = xgb.XGBRegressor(
        n_estimators=60, max_depth=3, learning_rate=0.15,
        subsample=0.9, colsample_bytree=0.9,
        enable_categorical=True, tree_method="hist",
        reg_lambda=1.0, random_state=42,
    )
    model.fit(X, y)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model.save_model(str(MODEL_PATH))

    categories = {col: sorted(df[col].cat.categories.tolist()) for col in FEATURE_COLS}
    META_PATH.write_text(json.dumps({
        "feature_cols": FEATURE_COLS,
        "numeric_cols": NUMERIC_COLS,
        "categories": categories,
        "row_count": len(df),
        "target_transform": "log1p",
    }, indent=2), encoding="utf-8")

    return model


if __name__ == "__main__":
    m = train()
    print(f"trained on {len(load_reference_df())} rows -> {MODEL_PATH}")
    print(f"metadata -> {META_PATH}")
