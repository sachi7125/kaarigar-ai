# Working Log — KaarigarAI

Shared hand-off log so multiple people (and Claude sessions) can pick up where the last
left off. **Newest entry on top.** Each entry: date, who, what got done, what's next,
and anything the next person needs to know.

Say **"update logs.md"** to append a new entry.

The deep detail lives in `docs/build_log.md` (narrative), `docs/tracker.md` (task status),
`docs/watchlist.md` (risks/gotchas), `docs/decisions.md` (locked choices D1–D11).
This file is the quick "where are we / what next".

---

## 2026-09-01 — Claude session (Day 2, steps 1–2)

**Done**
- Day 2 step 1 (transcription) verified on the MacBook Air: `pipelines/voice/transcribe.py`
  — whisper.cpp server → faster-whisper `tiny` int8 fallback, confidence + `needs_rerecord`.
  `scripts/day2_smoke.py` passes the step-1 gate. 10/10 voice unit tests pass
  (run with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`).
- Day 2 step 2 (translation): `pipelines/voice/translate.py` is now a **passthrough**
  (keeps the `TranslationResult` contract). Standalone MT model (IndicTrans2 / HF
  `transformers` / torch) was **cut** — `import transformers` hung ~20 min on this venv.
  Gemini (step 3) will translate regional → EN+HI directly. See decision **D11 (revised)**.
- Environment fixes: `conda config --set auto_activate_base false`; removed
  torch/transformers/IndicTrans2 debris from `.venv`; documented in `docs/watchlist.md`.
- Docs updated: tracker, build_log, watchlist, decisions.

**NOT working / open issue**
- ⚠️ **Voice recognition quality is poor.** On the smoke test (`tiny` model + robotic macOS
  `say` voice) the Hindi decode came back garbled at confidence 0.35 (`needs_rerecord=True`
  — the gate correctly caught it, so bad text does NOT reach a listing). Needs proper
  evaluation on **real human voice notes** and likely a model bump (`tiny` → `base`/`small`)
  or wiring the whisper.cpp server. Nothing committed yet.

**Next task (priority order)**
1. **Fix voice recognition** — test `transcribe.py` on real recorded Hindi/Bengali/Tamil/
   Marathi voice notes; if clean human audio still scores < 0.55, bump the on-device model
   in `config/config.yaml` (`models.transcribe.on_device`) from `whisper-tiny-q` to
   `whisper-base`, and/or build + point at a whisper.cpp `server` (`KAARIGAR_WHISPER_SERVER`).
2. Day 2 step 3 — Gemini bilingual description (also does the translation): regional
   transcript + confirmed attributes → EN + HI listing text, with a templated offline
   fallback for API outages. Stub at `pipelines/voice/describe.py`.
3. Day 2 step 4 — glossary fuzzy-correct (`glossary.py`) + PII-digit strip (`pii_strip.py`)
   + the low-confidence **re-record loop** (speak the prompt via `tts.py`, re-capture, cap
   retries). This is the real guardrail against garbled listings.
4. Day 2 step 5 — spoken read-back confirmation (reuse `tts.py`).

**Notes for whoever's next**
- Always `source .venv/bin/activate`; keep conda `(base)` OFF the prompt.
- Run pytest as `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest pipelines/voice/ -q`.
- Do NOT `pip install` torch / transformers / rembg (see `docs/watchlist.md`).
- Uncommitted work: `pipelines/voice/{transcribe,translate,test_transcribe,test_translate}.py`,
  `scripts/day2_smoke.py`, `backend/requirements.txt`, `docs/*`. Commit block is in the
  chat / build_log.
