# pipelines

The three AI pipelines, each an independent worker so one slow/failed model degrades only its
own step.

- `image/`   — rembg U2-Net + OpenCV enhancement (mandated 1)
- `voice/`   — whisper.cpp -> IndicTrans2 -> Gemini, + glossary, PII strip, shared TTS (mandated 2)
- `pricing/` — attributes (material from voice, not photo) -> XGBoost band -> SHAP + floor (mandated 3)
