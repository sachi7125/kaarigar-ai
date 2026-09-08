"""Pricing endpoints — bridges the Flutter app to `pipelines.pricing.*` and the Day 2
voice pipeline (Day 4 mobile UI wiring, 6 Sep).

Three stateless endpoints (no server-side session — each call is self-contained and
safe to retry, matching `sync.py`'s style):

  - POST /api/pricing/attributes — image + audio -> the UNCONFIRMED vision/voice
    suggestion (category from the transcript via `describe()`, material from the
    transcript via `attributes.extract_material`, size_class/size_score/finish from
    vision). Nothing here is a cost/price value.
  - POST /api/pricing/classify_answer — one recorded yes/no clip -> True/False/None.
    Generic (not pricing-specific) — the same primitive `readback.classify_answer`
    already uses for the Day-2 gate.
  - POST /api/pricing/quote — confirmed category/material/size(+size_score) -> the
    derived floor, the XGBoost band, the reconciled suggested price, comparables,
    and the three-bar explanation. No image/audio needed at this stage.

`region` is never guessed here: Day 5's voice-first onboarding (where an artisan's
location would actually be captured) doesn't exist yet, so the caller passes
"unknown" — `model.py`'s existing out-of-range-honesty logic already widens the band
for an unseen category value, which is the honest response to a genuinely unknown
region, not a silently assumed one.
"""
from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, File, UploadFile, Form
from pydantic import BaseModel

from pipelines.voice.transcribe import transcribe
from pipelines.voice.glossary import correct as glossary_correct
from pipelines.voice.pii_strip import strip_pii
from pipelines.voice.describe import describe
from pipelines.voice.readback import classify_answer
from pipelines.pricing.attributes import suggest_attributes
from pipelines.pricing.floor import fair_price_floor
from pipelines.pricing.model import predict_band
from pipelines.pricing.shap_explain import explain
from pipelines.pricing.recommend import suggest_price

router = APIRouter()


def _save_upload(f: UploadFile, suffix: str) -> str:
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as out:
        out.write(f.file.read())
    return path


@router.post("/pricing/attributes")
async def pricing_attributes(
    image: UploadFile = File(...),
    audio: UploadFile = File(...),
    lang: str = Form("hi"),
):
    """Unconfirmed suggestion only — the caller is responsible for the spoken
    attribute-only confirmations before treating material/size as final."""
    image_path = _save_upload(image, ".jpg")
    audio_path = _save_upload(audio, ".m4a")
    try:
        t = transcribe(audio_path, lang=lang)
        g = glossary_correct(t.text or "")
        p = strip_pii(g.text)
        d = describe(p.text, lang=lang)
        attrs = suggest_attributes(image_path, p.text, lang=lang, recorder=None)
        return {
            "transcript": p.text,
            "category": d.category,
            "material": attrs.material,
            "material_source": attrs.material_source,
            "size_class": attrs.size_class,
            "size_score": attrs.size_score,
            "size_source": attrs.size_source,
            "finish": attrs.finish,
            # Full bilingual listing text, so a later publish step (listings.py,
            # Day 5) can reuse this instead of a second describe() call — it
            # would hit the same disk cache anyway (transcript+attributes keyed),
            # but there is no reason to ask twice for what's already in hand.
            "title_en": d.title_en, "title_hi": d.title_hi,
            "description_en": d.description_en, "description_hi": d.description_hi,
            "bullets_en": d.bullets_en,
        }
    finally:
        os.unlink(image_path)
        os.unlink(audio_path)


@router.post("/pricing/classify_answer")
async def pricing_classify_answer(audio: UploadFile = File(...), lang: str = Form("hi")):
    audio_path = _save_upload(audio, ".m4a")
    try:
        t = transcribe(audio_path, lang=lang)
        verdict = classify_answer(t.text, lang)
        return {"answer": verdict, "heard": t.text}
    finally:
        os.unlink(audio_path)


class QuoteRequest(BaseModel):
    category: str
    material: str
    size_class: str
    size_score: float | None = None
    region: str = "unknown"
    month: int | None = None


@router.post("/pricing/quote")
async def pricing_quote(req: QuoteRequest):
    import datetime
    month = req.month or datetime.date.today().month

    floor = fair_price_floor(req.material, req.size_class, req.size_score, req.category)
    band = predict_band(req.category, req.material, req.size_class, req.region, month, req.size_score)
    suggestion = suggest_price(band, floor)
    bars = explain(req.category, req.material, req.size_class, req.region, month, req.size_score)

    return {
        "floor": floor.as_dict(),
        "band": band.as_dict(),
        "suggested": suggestion.as_dict(),
        "explain": bars.as_dict(),
    }
