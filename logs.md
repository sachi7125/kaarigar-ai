# Working Log — KaarigarAI

Shared hand-off log so multiple people (and Claude sessions) can pick up where the last
left off. **Newest entry on top.** Each entry: date, who, what got done, what's next,
and anything the next person needs to know.

Say **"update logs.md"** to append a new entry.

The deep detail lives in `docs/build_log.md` (narrative), `docs/tracker.md` (task status),
`docs/watchlist.md` (risks/gotchas), `docs/decisions.md` (locked choices D1–D11).
This file is the quick "where are we / what next".

---

## 2026-09-01 — Decision D13: material cost is derived, never asked

**What changed:** the pricing feature will **not** ask the artisan for her material cost (the
old plan: "material cost asked once per craft type"). That re-introduced the exact burden the
product removes. Instead: `cost ≈ material type (from the voice note) × ₹/unit (dated rate
table) × size/weight (photo + voice)`. Spoken confirmations stay, but are **attribute-only**
("brass or bronze?"), never about price.

**Docs updated:** `decisions.md` (new **D13**, D2 reworded), `watchlist.md` (Day-4 items),
`tracker.md` (Day 4), `planning/KaarigarAI_9Day_Roadmap.md` (scope para, Day-4 gate + body,
Day-7 hardening, watch item, cut list; also folded in D11 — no standalone MT model),
`README.md`, `config/config.yaml` (pricing comment).

**Still to do:** the binary deliverables (`docs/deliverables/*.pdf/.pptx/.docx` — proposal,
deck, architecture, wireframes) still say "material cost asked" / "IndicTrans2" in places.
They need a matching pass before submission (Day 9). Not editable as text — flagged here.

**Next task:** unchanged — Day 2 step 4 (glossary + PII + re-record loop).

---

## 2026-09-01 (later still) — Claude session — Day 2 step 3: Gemini bilingual listing

**Done**
- `pipelines/voice/describe.py` — `describe(transcript, lang, attributes)` → `ListingDraft`
  (title/description/bullets in EN+HI, seo_keywords, category, materials). Gemini also does
  the translation (D11).
- Gemini called over **REST via `requests`** — NOT the `google-generativeai` SDK (deprecated,
  156 s import, re-broke pytest; installed then `rm -rf`'d). See D12.
- Disk cache `data/processed/listing_cache/` (gitignored) = the Day-7 pre-cache mechanism.
- Offline template fallback — no key / quota / offline → still produces a bilingual listing.
- `common.py`: `load_env()` / `env_get()` for `.env`; added `.env.example`.
- Tests 16/16 pass. `day2_smoke` extended to step 3.

**Gemini key — RESOLVED.** The free tier only works on a project with **no billing account**.
The first key was made in a billing-enabled project (Maps free-trial) → 429 once credit ran
out. New key from a fresh AI Studio project works. `describe.py` verified: `source=gemini`,
correct EN+HI listing, model `gemini-3.6-flash`.

**Next task (priority order)**
1. Day 2 step 4 — `glossary.py` (craft-vocab fuzzy-correct, e.g. clay→मिट्टी, ikat/bandhani/
   dhokra spellings) + `pii_strip.py` (strip identifier-like digit runs before publish) + the
   low-confidence **re-record loop** (speak prompt via `tts.py`, re-capture, cap retries).
2. Day 2 step 5 — spoken read-back confirmation (reuse `tts.py`). Nothing publishes without it.
3. Populate `data/processed/listing_cache/` with the demo items (Day-7 pre-cache).

**Notes for whoever's next**
- Repo on `~/Desktop` (iCloud-synced) makes every Python import slow (~30 s pytest, ~3 min
  for a one-off script). Consider moving to `~/dev/`. Not blocking.
- Do NOT install `google-generativeai` / `grpcio` / `torch` / `transformers` (watchlist).
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` for pytest.

---

## 2026-09-01 (later) — Claude session — voice recognition FIXED

**Done**
- Diagnosed the garbled transcription with `scripts/stt_probe.py` (new) on a real 6.5s
  Hindi note ("ye ek clay ka bartan hai"): `tiny` and `base` are **unusable for Hindi**
  (conf ~0.25, garbage text); `small` gets it right — "ये एक क्ले का बर्तन है" at conf **0.70**,
  clearing the 0.55 gate. The confidence metric was fine all along; it was the model.
- `config/config.yaml`: `models.transcribe.on_device` `whisper-tiny-q` → **`whisper-small`**.
- `pipelines/voice/transcribe.py` `_transcribe_fw`: `vad_filter=False` (was clipping short
  notes) + `condition_on_previous_text=False` (cleaner one-shot text). Evidence in build_log.
- `scripts/stt_probe.py` added — reusable STT diagnostic (audio metadata + model/setting sweep).

**Still open / caveats**
- `small` steady-state ~2.6s for a 6.5s note on the Air — acceptable. First-ever run
  downloads the model (~465 MB).
- Minor residual errors (बर्तन→बर्दन; English loanwords like "clay") — acceptable, Gemini
  handles them. Optional later: seed whisper with an `initial_prompt` of craft vocabulary.
- Re-test on Bengali / Tamil / Marathi notes before Day 7.
- `day2_smoke.py` still uses robotic `say` audio → will still show low conf there; that's the
  test's synthetic input, not the system. Real audio is the real check.

**Next task (priority order)**
1. Day 2 step 3 — Gemini bilingual description (`pipelines/voice/describe.py`): transcript +
   confirmed attributes → EN + HI listing text, templated offline fallback for API outages.
2. Day 2 step 4 — glossary fuzzy-correct (`glossary.py`) + PII-digit strip (`pii_strip.py`) +
   low-confidence re-record loop (speak prompt via `tts.py`, re-capture, cap retries).
3. Day 2 step 5 — spoken read-back confirmation (reuse `tts.py`).

**Notes for whoever's next**
- Same as previous entry. Plus: transcription config is now `whisper-small`; expect a
  one-time ~465 MB download on a fresh machine.

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
