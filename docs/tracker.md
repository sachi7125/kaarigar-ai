# Tracker

What's done, in progress, and next. Updated **every task**. Status: `[ ]` todo · `[~]` in
progress · `[x]` done · `[!]` done-with-caveat (see build_log / watchlist).

Roadmap: [`planning/KaarigarAI_9Day_Roadmap.md`](planning/KaarigarAI_9Day_Roadmap.md).

---

## Day 0 — Scaffolding
- [x] Project directory structure created
- [x] Roadmap moved to `docs/planning/`; deliverables to `docs/deliverables/`
- [x] README, tracker, watchlist, build_log, decisions, data_sources created
- [x] `config/config.yaml`, `.gitignore`, `backend/requirements.txt`, `mobile/pubspec.yaml`
- [ ] Git first commit of the scaffold *(user setting up git)*

## Day 1 — Image pipeline + shared TTS   · gate: photo → clean image on device; TTS speaks   ✅ GATE PASSED
- [x] rembg (U2-Net) background removal — GrabCut fallback if rembg absent (`pipelines/image/enhance.py`)
- [x] OpenCV white-balance (scene Shades-of-Gray, clamped) + CLAHE lighting + saliency/bbox crop to square
- [x] Failure-aware retake — mask-sanity (coverage + fragmentation), NOT internal contrast; keeps original
- [x] Texture close-up for textiles
- [x] Shared TTS voice — `pipelines/voice/tts.py` (pyttsx3 → macOS `say` fallback, offline)
- [x] Smoke test `scripts/day1_smoke.py` + unit test `pipelines/image/test_enhance.py`
- [ ] Extras deferred (build if time): blur/shake at capture, synthetic shadow, perspective de-skew, angle coach

## Day 2 — Voice → listing   · (mandated 2)
- [x] ✅ **FIX: voice recognition quality** — was `tiny` (garbled, conf 0.25). `stt_probe.py`
      proved `tiny`/`base` unusable for Hindi, `small` correct at conf 0.70. Set
      `on_device: whisper-small`; `vad_filter=False` + `condition_on_previous_text=False`.
      Verified on a real Hindi note. Re-test bn/ta/mr before Day 7.
- [x] whisper.cpp transcription (server + on-device fallback) — `pipelines/voice/transcribe.py`
      server (`KAARIGAR_WHISPER_SERVER`) → faster-whisper int8 fallback, confidence +
      `needs_rerecord`. Smoke `scripts/day2_smoke.py` **ran on the Air 1 Sep**: `tiny` model
      downloaded, real decode, backend works, confidence gate fires correctly
      (0.36 on synthetic TTS audio → `needs_rerecord=True`). Tests 10/10 pass (use
      `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`). Caveat: quality on `tiny` + robotic `say` voice is
      poor — **re-check gate with a real human voice note per language** (watchlist).
- [x] Translation — `pipelines/voice/translate.py`. Passthrough (keeps `TranslationResult`
      contract); **Gemini does the real MT in step 3.** IndicTrans2/torch/transformers cut after
      `import transformers` hung ~20 min on the conda-based venv (D11 revised, watchlist).
      Optional real path behind `KAARIGAR_MT=indictrans2`. Tests + smoke green, instant.
- [!] Gemini bilingual description — `pipelines/voice/describe.py`. `describe(transcript, lang,
      attributes)` → `ListingDraft` (title/description/bullets EN+HI, seo_keywords, category,
      materials, source). Gemini over **REST** (`requests`, no SDK — D12), also does translation
      (D11). Disk cache `data/processed/listing_cache/` = Day-7 pre-cache path. Offline template
      fallback. Tests 6/6, chained into `day2_smoke`. **CAVEAT:** the test Gemini key hits 429
      "prepayment credits depleted" — needs a fresh free-tier AI Studio key; code path verified
      (REST fires, errors handled, template produced). See logs.md.
- [ ] Glossary fuzzy-correct · PII strip · low-confidence re-record
- [ ] Spoken read-back confirmation

## Day 3 — Flutter shell + offline queue   · GATE
- [ ] App shell (camera, record)
- [ ] SQLite + outbound queue (client ids, downscale, oldest-first, cap)
- [ ] Draft autosave · server-side dedupe
- [ ] GATE: capture+record+queue works offline and syncs with no duplicate

## Day 4 — Dynamic pricing   · (mandated 3) · GATE
- [ ] Attribute extraction (vision suggests; material from voice; 0–2 spoken confirms)
- [ ] Material cost asked once/craft type · dated material-rate table (source on screen)
- [ ] XGBoost band · SHAP three bars · comparables evidence strip
- [ ] Fair-price floor (warn, not block) · bounded seasonal multiplier · out-of-range honesty
- [ ] GATE: floor visibly refuses an underpriced suggestion; no material inferred from photo

## Day 5 — Onboarding + listing page + offer/stock   · GATE
- [ ] Voice-first onboarding (speaking tiles, keypad, OTP read aloud, deferred verification)
- [ ] Permanent public listing page
- [ ] Offer inbox (structured offer, asking-price auto-decline, quantity validation)
- [ ] Unique-vs-batch stock, locked decrement, sold-out + spoken restock, expiry
- [ ] Voice accept/decline · report-an-issue record
- [ ] GATE: batch sells down, accept by voice, no double-accept

## Day 6 — Storefront + market linkage   · differentiator
- [ ] Artisan storefront (permanent URL, maker story, all listings)
- [ ] Follow (email digest, weekly, unsubscribe) · returning-buyer flag
- [ ] Stall QR → storefront · share card · export bundle
- [ ] Maker story pipeline · scheme/mela/seasonal alerts · quality meter · dashboard · voice status

## Day 7 — Hardening + offline rehearsal + pre-cache   · GATE
- [ ] Edge-case register hardened
- [ ] Offline rehearsal (network disabled) · pre-cache demo responses
- [ ] GATE: full seven-beat demo runs twice with no internet

## Day 8 — Freeze + rehearsal + video
- [ ] Freeze build (tag) · rehearse seven beats · live-API + cached fallback tested
- [ ] 90-second backup video

## Day 9 — Final docs pass + submission
- [ ] README clean-clone check · demo script · sections mapped to impact goals
- [ ] Submit · hold ~2 hrs slack
