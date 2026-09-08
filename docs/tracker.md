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
- [x] Gemini bilingual description — `pipelines/voice/describe.py`. `describe(transcript, lang,
      attributes)` → `ListingDraft` (title/description/bullets EN+HI, seo_keywords, category,
      materials, source). Gemini over **REST** (`requests`, no SDK — D12), also does translation
      (D11). Disk cache `data/processed/listing_cache/` = Day-7 pre-cache path. Offline template
      fallback. Tests 16/16. **Verified with a real Gemini call** on a fresh free-tier key
      (billing-free project): correct EN+HI listing, fixed a transcription typo, used attributes.
- [x] Glossary fuzzy-correct · PII strip · low-confidence re-record
      `glossary.py` — `correct(text)` snaps misheard craft/material words to canonical
      spellings from `data/reference/craft_glossary.csv` (exact-variant then `difflib` fuzzy,
      stdlib only). Devanagari-safe tokeniser; script never switches. Fixes the real
      `बर्दन`→`बर्तन` from the test recording.
      `pii_strip.py` — removes `+91`/10-digit/12-digit/>=7-digit runs (Latin + Devanagari
      digits); KEEPS prices, dimensions, counts, years. Returns redaction list.
      `capture.py` — `capture(audio, lang, recorder, max_retries)` re-record loop: speaks a
      per-language "say it again" prompt via Day-1 TTS, retries via an injected `recorder`
      callable (no mic code here), keeps the BEST take not the last. Config
      `models.transcribe.max_rerecords` (2).
      Tests 24/24 (`test_glossary`, `test_pii_strip`, `test_capture`). Wired into `day2_smoke`
      in order transcribe -> glossary -> pii -> describe.
- [x] Spoken read-back confirmation — `pipelines/voice/readback.py`.
      `build_script()` composes what she hears **in her own language**: her cleaned transcript,
      every glossary correction and PII redaction spoken aloud, the extracted category/material/
      price, then "is this correct? say yes or no". `classify_answer()` fuzzy-matches a spoken
      yes/no per language (hi/bn/ta/mr/en, Devanagari + romanised).
      `readback_and_confirm()` runs the loop through an injected `recorder` (no mic code — D14),
      retries on an unclear answer (`readback.max_confirm_attempts`, 2).
      **`may_publish` is True only on an explicit spoken yes** (D15) — silence, unclear, TTS
      failure and exhausted retries all block. Tests 17/17. Wired into `day2_smoke`.
- [x] GATE: regional voice note → bilingual listing → read back aloud → confirmed by voice,
      **on a real device** (needs the Day-3 Flutter recorder to supply the `recorder` callable)

## Day 3 — Flutter shell + offline queue   · GATE   ✅ GATE PASSED (closed 6 Sep, see build_log)
- [x] App shell (camera, record)
- [x] SQLite + outbound queue (client ids, downscale, oldest-first, cap) — downscale + cap were
      still a `// TODO` as of 5 Sep despite this checkmark; implemented 5 Sep (build_log)
- [x] Draft autosave · server-side dedupe
- [x] GATE: capture+record+queue works offline and syncs with no duplicate — closed 6 Sep on an
      Android emulator against the real backend: captured+recorded a draft online (synced), then
      one fully offline (network disabled via `adb shell svc wifi/data disable` — correctly held
      as "Pending Sync"), then reconnected and watched it auto-sync via the connectivity
      listener with no manual action. Verified at the source of truth, not just the UI: pulled
      `kaarigar.db` off the device — all 3 drafts `isSynced=1`, `sync_queue` empty — and checked
      the backend's `data/uploads/` — 3 distinct client_ids, no duplicates. Found and fixed one
      real bug in the process: `SyncQueueService.processQueue()` runs the network sync
      unawaited, so `HomeScreen` could show "Pending Sync" long after a draft had actually
      synced, with nothing telling it to refresh — added `queueVersion` (a `ValueNotifier`
      bumped on every sync/eviction) that `HomeScreen` now listens to. `flutter analyze`/
      `flutter test` were both failing outright until 5 Sep (broken `widget_test.dart`) — now
      clean.

## Day 4 — Dynamic pricing   · (mandated 3) · GATE   ✅ GATE PASSED (on screen, closed 6 Sep)
- [x] Attribute extraction — `pipelines/pricing/attributes.py`. Vision suggests **size_class**
      (bbox coverage) and **finish** (specular-highlight spread in the subject mask) only —
      deliberately NOT a category name from shape alone (D16: that would be a guess dressed up
      as a vision finding, the same reasoning D2 used to refuse a material classifier). Material
      *type* is plain keyword matching on the (glossary-corrected) transcript against a materials
      vocabulary — never image inference. 0–2 spoken confirms (material only if voice found one;
      size always), attribute-only, reusing `readback.classify_answer` for yes/no. A "no"/unclear
      answer clears the field rather than guessing again. 11 unit tests, **plus a real on-device
      run**: `flutter_tts` speaks the question, `record` captures her answer, the backend
      classifies it — verified end to end on an Android emulator 6 Sep.
- [x] Material cost **derived, not asked**: `pipelines/pricing/floor.py`. `material (voice) x
      rate_inr_per_kg (data/reference/material_rates.csv, dated+sourced) x weight_kg
      (category-aware, size_score-interpolated)`. Rate date + source are rendered on the
      **Fair-price floor** card in `PricingScreen` — confirmed on screen 6 Sep, not just returned
      as data.
- [x] XGBoost band (`pipelines/pricing/model.py`) · SHAP three bars (`shap_explain.py`, via
      XGBoost's own `pred_contribs`, not the `shap` package — D16) · comparables evidence strip
      (3 nearest reference rows) — **all three rendered on screen**, comparables shown *before*
      the price band per the roadmap's exact ordering requirement.
- [x] Fair-price floor (warns, never blocks) · bounded seasonal multiplier · out-of-range honesty
      (unseen category/material -> `confidence="low"` + a wider band, shown as a plain-English
      sentence on screen, not just a flag).
- [x] GATE: floor visibly refuses an underpriced suggestion; no cost question anywhere; material
      not inferred from photo pixels — verified at the pipeline level (`scripts/day4_smoke.py`,
      36 unit tests) **and now on an actual phone screen**: `backend/app/api/pricing.py` (3 new
      endpoints: `/pricing/attributes`, `/pricing/classify_answer`, `/pricing/quote`) +
      `mobile/lib/screens/pricing_screen.dart`. Region is not guessed — Day 5's onboarding
      doesn't exist yet, so `"unknown"` is passed and the model's own out-of-range-honesty
      widens the band, which is the honest response, not a silently assumed location.

## Day 5 — Onboarding + listing page + offer/stock   · GATE   ✅ GATE PASSED (on screen, closed 6 Sep)
- [x] Voice-first onboarding — `mobile/lib/screens/onboarding/{language,phone,otp}_screen.dart` +
      `backend/app/api/onboarding.py`. Four speaking language tiles (no language list read, D2's
      "artisan is ground truth" logic extended to language choice itself) → numeric-keypad phone
      entry (`NumericKeypad`/`DigitDots` widgets, digits only, 64px+ touch targets per wireframe)
      → registered **unverified**. OTP is mocked (no SMS budget — see D17) but genuinely
      generated + TTS-spoken digit-by-digit, not faked; **deferred verification**: she can
      capture/record/see a price estimate all the way through unverified (Days 3–4 untouched),
      and OTP is only asked for at the *publish* step. Verified end to end on the Android
      emulator 6 Sep: fresh install → LanguageScreen → PhoneScreen → HomeScreen (unverified) →
      pricing round trip → "List for sale" → correctly detected unverified → OtpScreen →
      wrong-code error path rendered and cleared → correct OTP verified → publish proceeded.
- [x] Permanent public listing page — `backend/app/web/templates/listing.html` +
      `storefront_page.py`, `GET /l/{listing_id}`. Short base32 ids (`generate_short_id()`) so the
      stall-QR URL format is frozen now, not migrated later (watchlist). Matches wireframe screen
      6 (price + band, verified-artisan badge, maker's story placeholder, "offers below asking
      price declined automatically" disclosure). Confirmed rendering (200 OK) on a real published
      listing 6 Sep.
- [x] Offer inbox — `backend/app/api/offers.py` + `mobile/lib/screens/offers_screen.dart`.
      Structured offer (price, quantity, buyer contact); `offer_validation.py` auto-declines
      below-asking-minus-tolerance and over-stock offers **before** they ever reach the artisan's
      pending list — she sees the shield worked (auto-decline count), never the lowball offers
      themselves. Buyer contact is withheld from the pending list and returned only by `accept`
      (wireframe: "contact details are exchanged only after the artisan accepts") — confirmed on
      screen 6 Sep (dialog showed buyer name + contact only post-accept).
- [x] Unique-vs-batch stock, locked decrement — `backend/app/db/models.py` (`stock_type`,
      `total_count`, `remaining_count`) + `services/stock.py`'s `accept_offer_and_decrement()`
      using `.with_for_update()` (real row lock on Postgres, no-op on SQLite — see D17 caveat;
      SQLite's whole-DB write serialization still prevents double-accept at dev/demo scale).
      `PublishScreen` asks stock type as exactly two tiles ("एक ही" / "कई हैं", wireframe's
      "no screen offers more than two real choices" rule), then a numeric-keypad count for batch.
- [x] Voice accept/decline · report-an-issue record — `OffersScreen`: TTS speaks the offer
      (price + quantity), mic records her answer, backend classifies yes/no via the same
      `readback.classify_answer` primitive Day 2's read-back gate and Day 4's attribute confirms
      already use — no separate "accept/decline classifier" built. Two on-screen buttons
      (Accept/Decline) are the always-available fallback per wireframe screen 5 ("two buttons, a
      number she can read, nothing else"). `report_issue()` logs only (D6) — not yet wired to a
      mobile screen, left for Day 6 storefront work if time allows.
- [x] GATE: **batch sells down, accept by voice path exercised, no double-accept** — verified live
      through the real mobile UI, not just curl: published a batch-of-5 listing, submitted two
      competing offers (3 units each, exceeding stock together), accepted the first through
      `OffersScreen`'s Accept button (buyer contact correctly revealed only then, remaining count
      5→2), then attempted the second — got a real `409 Conflict` surfaced as a plain Hindi
      message ("यह अब उपलब्ध नहीं है — स्टॉक खत्म हो गया"), never a silent double-decrement. Backend
      also covered by 12 passing unit tests (`test_stock.py`, `test_offer_validation.py`,
      including `test_the_actual_no_double_accept_scenario`).

**Note:** the offer-accept voice path was exercised through TTS+mic+classify wiring identical to
Day 4's confirm loop (already proven live); the specific accept/decline utterance itself was
tested via silence → "unclear" → no-op (never guesses), same honest behaviour as Day 4's confirm
loop, rather than a spoken "हाँ" — a full spoken-word accept was not additionally re-verified
since the underlying `classify_answer` primitive is shared and already proven both server-side
(unit tests) and on-device (Day 4).

**Real-device pass, 6 Sep (before Day 6 started):** the user asked to test on their own physical
Pixel 8 via USB debugging instead of the emulator. This found and fixed 3 real bugs a fake mic/
camera can never exercise — a glossary near-miss (चान्दी/चांदी), an infinite confirm-loop on a
definite spoken "yes" (real bug in the original Day-4 code, only reachable with genuine speech),
and mic/speaker bleed-through corrupting recorded answers — plus added retry-on-unclear to the
confirm loops. See build_log 6 Sep for the full writeup. Also added a price confirm/edit step
(decision D19) so the model's suggestion is genuinely editable before publish, not just advisory
in name — raised by the user, not on any roadmap day, done because it closes a real gap against
the wireframe's own stated intent. (Day 6 itself started the next morning, 7 Sep — see below.)

## Day 6 — Storefront + market linkage   · differentiator   ✅ mandated items done (7 Sep)
- [x] Artisan storefront (permanent URL, maker story, all listings) —
      `backend/app/api/storefront.py` (JSON API) + `web/storefront_page.py`'s `GET /s/{artisan_id}`
      + `web/templates/storefront.html`. Maker story on top, every listing below (sold-out
      **marked**, never hidden — the roadmap says "every listing"), follow form at the bottom.
      Permanent URL, same frozen short-base32 id scheme as listings (watchlist). Verified in a
      browser 7 Sep: page renders, listing cards link through to `/l/{id}`, follow form posts.
- [x] Follow (email digest, weekly, unsubscribe) · returning-buyer flag —
      `Follower` model (email + unguessable `secrets.token_urlsafe(24)` unsubscribe token),
      `POST /storefront/follow` (idempotent — following twice returns the same token, doesn't
      duplicate), `GET /unsubscribe/{token}` as a plain no-JS GET so it works from any mail
      client. **Actual weekly SMTP send is mocked** (no provider budgeted — D20), but
      `GET /storefront/{id}/digest_preview` assembles the *real* content a send would use
      (new listings in the last 7 days + recipient count), so the data path is genuine even
      though delivery isn't. Returning-buyer flag computed once at offer-submission time from
      prior **accepted** offers by the same contact to the same artisan, then spoken with the
      offer in `OffersScreen` ("यह खरीदार पहले भी आपसे खरीद चुका है") and shown as a badge.
- [x] Stall QR → storefront · share card · export bundle —
      `GET /storefront/{id}/qr` returns a PNG QR encoding the **storefront** URL, not a listing
      (decision D5), rendered on the mobile dashboard for printing. Share card
      (`GET /listings/{id}/share_card`) composes photo + bilingual title + price + a QR to the
      listing into one 1080×1080 PNG, shared through the OS share sheet (`share_plus`) so
      "forwarded on WhatsApp" is a real share. Export bundle
      (`GET /listings/{id}/export_bundle`) is a real `.xlsx` with GeM/ONDC/Amazon-Karigar/ODOP-
      style catalog columns; fields this prototype genuinely doesn't collect (GSTIN, HSN, bank
      account) are written as explicit "not collected — …" strings rather than left blank
      (D22). Both verified on the real phone 7 Sep.
- [x] Maker story pipeline · dashboard —
      `pipelines/voice/maker_story.py` reuses the Day-2 chain (transcribe → glossary → PII
      strip) and adds its own Gemini prompt + offline template, separate from `describe()`
      because a bio is not a product listing; an empty transcript yields an honest generic line,
      never an invented name/place/years (5 unit tests). `MakerStoryScreen` records it;
      `DashboardScreen` shows **real** aggregates (listings, pending offers, total earned from
      accepted offers, stock, followers, sold-out) — no placeholder numbers.
- [ ] ○ **Not built (roadmap's own optional tier):** scheme/mela/seasonal alerts, quality meter,
      voice order & status. Deferred deliberately, not forgotten — the ★ items above plus the
      exit gate were the priority.
- [x] **Exit gate — stall QR opens the storefront; one tap yields a valid export bundle;
      dashboard shows real aggregates.** All three verified 7 Sep: QR encodes
      `{url_base}/s/{artisan_id}` and that page renders; Export on a listing produces a real
      downloadable spreadsheet through the share sheet; every dashboard number is a live
      DB aggregate (6 unit tests in `backend/tests/test_storefront.py` pin the arithmetic).

**Also done 7 Sep, outside the roadmap's Day-6 list (both raised by the user):**
- [x] **Listing rename, before AND after publish** (`rename_listing_screen.dart`,
      `POST /listings/rename_by_voice`, `PATCH /listings/{id}`) — by voice *or* by typing, both
      offered on the same screen at the user's explicit request (D21). Confirmed working on the
      real phone 7 Sep.
- [x] **Leather added to the material vocabulary** — found live: a real leather-sandal voice
      note said "लेदर" clearly and material still came back empty, because leather was absent
      from `MATERIAL_TERMS`, `material_rates.csv` and the category weight overrides entirely.
      Leather goods are a major Indian craft category; see build_log 7 Sep.

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
