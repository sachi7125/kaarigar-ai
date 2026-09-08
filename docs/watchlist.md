# Watchlist

Things to verify, check, or watch out for — written when noticed, checked when the day
arrives. **Read this at the start of each build day and raise anything due.**

Status: `[ ]` open · `[x]` checked, fine · `[!]` checked, it was a problem.

---

## Environment (macOS arm64 dev machine) — learned the hard way 1 Sep

- [x] **pip hangs on the macOS Keychain (keyring).** Symptom: `pip install` sits at 0% CPU with
      no output for many minutes. Fixed globally with `pip config set global.keyring-provider
      disabled`. If it recurs on another machine: prefix installs with
      `PYTHON_KEYRING_BACKEND=keyring.backends.null.Keyring`.
- [x] **Do NOT let OpenCV resolve to 5.0.0** (beta) — it imports in ~25 s on arm64. Pinned to
      `opencv-python-headless==4.10.0.84`.
- [x] **Do NOT import rembg** — it pulls pymatting+numba whose import-time JIT stalls for minutes.
      We run u2netp via onnxruntime directly instead. Keep it that way for any new bg work.
- [!] **`import transformers` / heavy dist-info in the venv hangs tooling for 10–20 min.** Root
      cause was `transformers` on `sys.path` — its import calls `importlib.metadata.packages_
      distributions()` which walks every distribution. Removing `torch/transformers/IndicTrans2`
      fixed it; `pytest` and `translate.py` are instant again. Rules: (1) `conda config --set
      auto_activate_base false` is now set — keep `(base)` off. (2) run pytest with
      `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. (3) don't reintroduce torch/transformers (D11).
      (4) `rm -rf` in zsh aborts entirely if any glob matches nothing — delete with explicit paths.
- [!] **No `torch` / `transformers` in this project.** Removed 1 Sep (see above). If a future
      task "needs" them, find a lighter path first (ONNX/CTranslate2, or an API).
- [ ] **Heavy models are slow on the Air's CPU** — expected. Mask at ≤720px; on device / for the
      demo, plan server-side processing and pre-cached responses (Day 7).

## Cross-cutting (any day)

- [ ] **Free-tier caps + demo-day internet.** Gemini and other free tiers carry daily request
      caps, and venue internet is unreliable. Mitigation: **pre-cache every demo-item response**
      (Day 7) and keep the on-device whisper.cpp as the offline fallback. **Never call any API
      inside a training or batch loop.**
- [ ] **Account/key/domain ownership.** Managed Postgres, object storage, Firebase project,
      Gemini key, and the public domain — bind them to a team-owned account, not one person's,
      and keep every secret in `.env` (never committed).

## Day 1 — image + voice

- [ ] **TTS is a hard dependency.** Read-back, onboarding, alerts and nudges all need it. If the
      shared voice slips, those slip too — build it Day 1, not later.
- [x] **Failure-aware enhancement must actually fire.** Implemented as **mask sanity**
      (coverage in 0.02–0.98 AND largest connected blob ≥ 0.55 of subject pixels), NOT internal
      subject contrast — a flat-coloured pot/sari is legitimately low-contrast and must NOT be
      rejected. `[!]`-watch on real photos: confirm a genuine pale-on-pale case still trips it.
- [ ] **White balance is scene-based (Shades-of-Gray, gains clamped 0.6–1.6).** Verify on real
      warm-lit photos that it corrects the cast without over-blueing; the clamp is the safety net.
- [ ] **rembg model is a ~176 MB download** (`~/.rembg/u2net.onnx`) on first use. For the demo/
      device path, pre-fetch it (ties into the Day-7 pre-cache + on-device model plan).

## Day 2 — voice → listing

- [ ] **faster-whisper first-run download** — now `small` (~465 MB, CTranslate2 int8) to
      `~/.cache/kaarigar/whisper/`. Pre-fetch for the demo/device path (ties into Day-7 pre-cache).
- [ ] **whisper.cpp server is optional and unbuilt.** Code prefers it via `KAARIGAR_WHISPER_SERVER`
      and falls back to on-device on any failure. If we want the server for the demo, build+test it
      before Day 7, not on the day.
- [x] **Voice recognition quality — FIXED 1 Sep.** `tiny`/`base` are unusable for Hindi
      (garbled, conf ~0.25); moved `on_device` to `whisper-small` (conf 0.70 on a real note) +
      `vad_filter=False` + `condition_on_previous_text=False`. Diagnostic: `scripts/stt_probe.py`.
      Still to do: re-test bn/ta/mr before Day 7; `small` is ~465 MB (pre-cache for the demo).
- [ ] **Glossary is only as good as its rows.** `data/reference/craft_glossary.csv` currently
      covers ~55 techniques/materials/objects. Every new real recording that surfaces a mishear
      should add a row — this is the cheapest quality win in the voice pipeline, because the words
      whisper mangles are the words buyers search for. Devanagari and Latin must stay on separate
      rows (a correction must never switch script).
- [ ] **PII strip must not eat prices.** Threshold is ≥7 digits; prices/dimensions/counts/years
      stay. If the demo ever shows a missing price, check `pii_strip` first. Tested both ways.
- [ ] **The re-record loop needs a real `recorder` on device.** `capture()` deliberately owns no
      microphone (D14) — Flutter must supply the callable, play `prompt_audio`, and re-record.
      Until Day 3 wires that, the loop only returns the prompt for the caller to drive.
- [ ] **Confidence gate is heuristic** (`exp(avg_logprob)` × `1-no_speech_prob`, threshold 0.55).
      Tune the threshold against real regional-language notes so it re-records genuine mishears
      without nagging on clean audio.
- [!] **TTS has a real voice only for Hindi on macOS.** `tts.py` maps `hi`→`Lekha`; bn/ta/mr fall
      back to an English voice, so a Bengali/Tamil/Marathi read-back *sounds* wrong on the dev Mac
      even though the script is correct. `flutter_tts` handles them on device — verify there before
      claiming those languages (ties to O3 and the "one tested language" fallback).
- [ ] **Publish must gate on `ReadbackResult.may_publish`, never on `confirmed is not False`.**
      `confirmed=None` (unclear / no answer / TTS down) must block. Silence is not consent (D15).
- [ ] **Read-back needs the Flutter `recorder` callable (Day 3).** `readback_and_confirm()` owns
      no microphone; until the app supplies it, the loop only returns the script + audio. The Day-2
      gate is not signed off until it runs on a real device.
- [ ] **`say`/pyttsx3 TTS is not a real speaker** — `day2_smoke` proves the plumbing, not accent
      robustness. Gate must still be checked with an actual human voice note per language.
- [!] **No standalone MT model (D11).** `translate()` is a passthrough; **Gemini (step 3) must do
      the actual regional→EN+HI translation.** Verify Gemini output quality per language against a
      real note. Offline, the listing text stays in the source language — acceptable degradation,
      but note it in the demo script.
- [x] **Gemini carries translation + description** — single point of failure, subject to free-tier
      caps. Template fallback (`describe.py`) + disk cache built; real Gemini call verified 1 Sep on
      a billing-free AI Studio project (a billing-enabled project 429s once trial credit is gone).
      Still to do: pre-cache every demo item Day 7 (populate `listing_cache/` online → replays
      offline); tune the prompt against more real transcripts.
- [!] **Never install `google-generativeai`** (or `google-api-python-client`, `grpcio`) — SDK is
      deprecated, imports in ~156 s, and its dep tree re-broke pytest. Gemini is REST via `requests`.
- [ ] **Free-tier Gemini model names churn** — `1.5-flash` gone, `2.5-flash` "not for new users",
      `3.6-flash` current. `models.describe` in config.yaml is the single place to change it;
      `curl .../v1beta/models` lists what a key can see.

## Day 3 — offline queue

- [x] **Queue must survive days offline — cap, downscale, oldest-first sync, dedupe.** Checked
      5 Sep: downscale and the size cap were still a bare `// TODO` in `sync_queue.dart` despite
      the tracker marking this done. Implemented: images downscaled to 1600px longest side
      before upload (original kept locally, cached upload copy reused on retry), queue capped
      at 50 pending drafts (oldest draft + its files evicted past that). Oldest-first sync and
      client-id dedupe were already correct.
- [ ] **First run needs one brief connection** (OTP) and must *defer, not block* when offline —
      capture allowed unverified, publish blocked.
- [!] **`flutter analyze` / `flutter test` were both red the entire time Day 3 was marked "GATE
      PASSED".** `test/widget_test.dart` was untouched `flutter create` boilerplate referencing
      a `MyApp` class that has never existed in this app — fixed 5 Sep, plus added
      `sqflite_common_ffi` as a dev dependency so the widget test can exercise `HomeScreen`'s
      local-db read without a device. **Run `flutter analyze && flutter test` before checking
      off any future mobile gate** — a broken test file doesn't fail loudly on its own.
- [x] **Record→enqueue→sync round trip verified end to end — closed 6 Sep.** Same emulator that
      crashed on 5 Sep worked cleanly this time (retry, not a permanent host limitation as
      feared — likely a transient resource issue that day). Captured+recorded online (synced),
      then fully offline (`adb shell svc wifi/data disable` — held as "Pending Sync"), then
      reconnected and watched it auto-sync via the connectivity listener alone. Verified at the
      DB/backend level, not just the UI: `kaarigar.db` pulled off-device shows all 3 drafts
      `isSynced=1` and an empty `sync_queue`; the backend's `data/uploads/` has exactly 3
      distinct client_ids, no duplicates.
- [!] **`HomeScreen` didn't refresh after a background sync completed.** Found live-testing
      6 Sep: `SyncQueueService.processQueue()` fires the network sync without awaiting it (by
      design, so capture isn't blocked on a slow connection), so a screen that read sync status
      once right after enqueueing could show "Pending Sync" long after the draft had actually
      synced — confirmed via the DB (`isSynced=1`) while the UI still said pending. Fixed:
      `SyncQueueService.queueVersion` (a `ValueNotifier<int>`) increments on every sync success
      or queue-cap eviction; `HomeScreen` listens to it in `initState`/`dispose` instead of only
      reloading once after returning from `CaptureScreen`.
- [!] **No iOS platform existed until 5 Sep** — `mobile/ios/` was never generated (only
      `android/` had been), and `Info.plist` had no `NSCameraUsageDescription` /
      `NSMicrophoneUsageDescription`, which crashes an iOS build on first camera/mic access
      instead of prompting. Added the platform and both usage strings 5 Sep. iOS Simulator
      testing is still blocked on this dev Mac — only Xcode command-line tools are installed,
      not full Xcode (`sudo xcode-select -s /Applications/Xcode.app/Contents/Developer` after
      installing Xcode from the App Store) — so the fix above is unverified on an actual
      simulator/device, only by static review.

## Day 4 — pricing

- [x] **No material classifier.** Checked 5 Sep: `pipelines/pricing/attributes.py` extracts
      material by keyword-matching the (glossary-corrected) transcript text only —
      `scripts/day4_smoke.py` proves it by swapping in a blank photo with the same transcript and
      asserting the extracted material doesn't change. Vision (`_vision_suggestions`) only
      produces `size_class` and `finish`, never a material or a category name (D16).
- [!] **Weight-by-size-class must be density-aware, not one table for every material.**
      Found live-testing 6 Sep: a "medium" silver item costed out at 1.0kg of silver (a
      ₹250,300 floor) because the original `size_estimates.csv` had one weight scale shared by
      every material. Fixed same day — `material_rates.csv` now has a `density_class`
      (precious/metal/bulk) and `size_estimates.csv` is keyed by `(density_class, size_class)`
      with three separate weight scales (see build_log 6 Sep). Regression-tested. If a future
      material doesn't obviously fit one of the three buckets, add a row rather than guessing.
- [x] **Material cost is DERIVED, never asked (D13).** Implemented 5 Sep in `floor.py`:
      `material (voice) × rate (material_rates.csv, dated+sourced) × weight_kg
      (size_estimates.csv, by size_class)`. The rate table currently covers 11 materials
      (clay, terracotta, brass, copper, silver, cotton, silk, wool, jute, bamboo, sandalwood,
      wood) — **a craft whose material isn't in that list gets `known=False`, not a fabricated
      cost** (verified: `pipelines.pricing.floor.derive_material_cost("paper", ...)`). Add a row
      whenever a real demo item's material is missing. Floor is a warning only (see below), so a
      wrong derived cost never blocks.
- [x] **Spoken confirmations are attribute-only.** Implemented 5 Sep: up to 2 questions (material
      only if voice found one; size always), reusing `readback.classify_answer`.
      `scripts/day4_smoke.py` and `test_attributes.py::test_never_asks_about_price_or_cost` both
      assert no confirmation text ever mentions price/cost.
- [x] **The floor is a warning, not a quote.** `check_against_floor()` in `floor.py` only ever
      returns a `FloorCheck` with a message — nothing in the module raises, blocks, or refuses.
      Tested 5 Sep (`test_below_floor_warns_but_never_blocks`).
- [!] **Material rates are a dated snapshot.** Only **silver and copper** are live-fetched and
      source-verified-reachable as of 5 Sep (goodreturns.in; tradingeconomics.com via xe.com FX)
      — the other 9 materials are typical-range, hand-compiled figures, clearly flagged via each
      row's `confidence` column, NOT independently verified against Agmarknet/eNAM/MCX/WPI yet.
      Do that pass before the demo. The date + source are now rendered directly on
      `PricingScreen`'s floor card (closed 6 Sep) — still worth re-verifying the underlying
      figures before the demo, since "on screen" no longer means "not yet checked."
- [x] **Band sanity — wider band + low confidence for unseen categories.** Implemented in
      `model.py`: an unseen category/material, or fewer than `pricing.comparables_shown` genuine
      same-category comparables, sets `confidence="low"` and doubles the band half-width (capped
      at 0.6). Tested 5 Sep (`test_unseen_category_gets_low_confidence_and_wider_band`); the
      resulting plain-English sentence is now shown on screen too (6 Sep).
- [x] **The pricing pipeline had no mobile UI — closed 6 Sep.** Added `backend/app/api/pricing.py`
      (3 endpoints: attribute suggestion, yes/no answer classification, final quote — all
      stateless) and `mobile/lib/screens/pricing_screen.dart`. Verified live on an Android
      emulator: comparables shown before the price band (roadmap's exact ordering requirement),
      floor + rate date/source on screen, SHAP three bars rendered, and a real spoken attribute
      confirmation using `flutter_tts` + `record` + the same `classify_answer` primitive the
      Day-2 gate uses. Two things worth knowing for next time:
      (1) `pricing.py` imports the top-level `pipelines` package (a sibling of `backend/`), which
      isn't on `sys.path` when run the documented way (`cd backend && uvicorn app.main:app`) —
      first surfaced as `ModuleNotFoundError: No module named 'pipelines'`. Fixed at the source in
      `backend/app/main.py` (adds the repo root to `sys.path` before importing the routers), so
      the original documented command keeps working unmodified — no PYTHONPATH incantation
      needed or to remember.
      (2) uvicorn's `--reload` only watches `.py` files — editing a `data/reference/*.csv` (e.g.
      the glossary) needs a manual backend restart to take effect, it will silently keep serving
      stale in-memory data otherwise.
- [ ] **`pricing_reference.csv` is small (58 rows) and 100% synthesised.** Every row is
      hand-compiled within researched-plausible ranges, not scraped from a real GeM/marketplace
      listing (data_sources.md). Fine for a working demo default; augment with real observed
      listings before the price band is treated as more than directional. Every demo-day craft
      category needs at least one row, or it will hit the unseen-category low-confidence path.
- [ ] **`size_estimates.csv` (weight_kg + hours by size_class) is a rough, undated placeholder,**
      not a measurement — there's no scale reference in the photo and no on-site scale. It
      affects only the floor (a warning), never the price band itself, so the failure mode of a
      wrong estimate here is a mistimed warning, not a wrong quoted price. Replace with real
      data if it becomes available.
- [x] **The confirm loop only worked by accident on the emulator — real hardware found 3 bugs
      6 Sep.** A real device's genuine microphone and camera exercise code paths the emulator's
      fake ones never can. Found and fixed: (1) an infinite confirm loop on a definite spoken
      "yes" — `_confirmNext()` never recorded that a field had already been confirmed, only that
      it was empty or voice-sourced; (2) mic/speaker bleed-through, where tapping the mic before
      the TTS prompt finished let its own audio contaminate the recorded answer; (3) another
      glossary near-miss (चान्दी/चांदी, 0.80 vs the 0.82 threshold — same class as पीतल/पीटल).
      See build_log 6 Sep for the fixes. **Re-run a real-device pass again once more of Day 6/7
      is built**, since new confirm loops (the offer accept/decline path already shares the fix,
      but anything new won't) could reintroduce the same class of bug.

## Day 5 — listing page + offers + stock

- [x] **Permanent URL id scheme is IRREVERSIBLE once a stall QR is printed.** Freeze the
      artisan/listing id format deliberately here; don't change it later in a migration.
      → `generate_short_id()` (`backend/app/db/models.py`) picked and frozen 6 Sep: base32,
      short, collision-checked on insert.
- [x] **Stock decrement must be atomic.** Decrement remaining_count under a row lock *inside* the
      acceptance transaction, or two buyers can both be accepted for the same batch.
      → `services/stock.py`'s `accept_offer_and_decrement()` — verified live 6 Sep through the
      real mobile Offers screen (two competing offers, one accept succeeds, the second gets a
      real 409). **Caveat carried forward as D17**: the row lock is a no-op on SQLite (current
      dev DB); re-verify under real concurrent writers once/if the DB moves to Postgres.
- [ ] **Per-piece vs per-set ambiguity** — ask explicitly, or every price is wrong by the size of
      the set. Not addressed in Day 5 — `PublishScreen` asks unique-vs-batch and a count, but a
      batch listing's price is per-item only; no explicit per-set framing exists yet.
- [ ] **Two mechanisms pointed opposite ways:** the buyer-side auto-decline is *asking price −
      tolerance*; the fair-price floor is advice to *her*. Keep them separate, or an artisan who
      prices below the floor finds her own listing unbuyable.
- [ ] **Middleman capture** — bind account + stall QR to her own number; earnings visible only in
      her own view.
- [ ] **New from Day 5 build:** the OTP screen's own "replay code" tap and its `initState`-time
      auto-send both call `/onboarding/send_otp` again, which **overwrites** the previously-issued
      code in the server's in-memory `_otp_store`. If she taps replay after already having heard
      the first code, the first code silently stops working — not exercised as a bug in front of
      her (TTS re-speaks the new code immediately after replay), but worth a deliberate look
      before demo day: a slow re-read or a distracted tap-then-look-away could leave her holding
      a code that's already invalid.

## Day 6 — storefront

- [x] **Follower email** — collect email only, weekly batched digest, one-click unsubscribe,
      delete on unsubscribe. This is the only outbound channel to a buyer; keep it minimal (DPDP).
      → Done 7 Sep: email is the ONLY field stored (no name, no phone); unsubscribe is a plain
      GET on an unguessable token and **deletes the row** rather than flagging it, so nothing is
      retained after opt-out. Actual sending is mocked (D20) — when SMTP is wired in, keep the
      batched-weekly shape; a per-listing instant email would be a different (worse) DPDP story.
- [x] **Stall QR points at the STOREFRONT**, not a single listing. Share card keeps a per-listing
      QR + storefront address underneath. → Done 7 Sep: `/storefront/{id}/qr` encodes
      `{url_base}/s/{artisan_id}`; the share card's QR points at the listing (`/l/{id}`) with the
      storefront address printed under it, so a forwarded card still leads somewhere after that
      one listing sells out. (The address line was missed on the first pass and added the same
      day — it needs right-aligning by measured text width, since artisan ids vary in length and
      a fixed x ran off the card.)
- [ ] **`listings.url_base` is still `https://kaarigar.in`, which nothing serves.** Every QR and
      share card now bakes that host in. Until open decision O1 (hosting) is settled and the
      domain actually resolves, a scanned stall QR goes nowhere — fine on a laptop demo where
      you show the local page, but it must be resolved before anything is *printed*.
- [ ] **Category came back empty on a real capture (7 Sep), not just material.** The leather fix
      addressed material; the same sandal listing also stored `category=""`, because `describe()`
      only produces a category via Gemini and its offline template has no category extraction at
      all. Empty category also means `category_weight_overrides.csv` can't match, so the floor
      silently falls back to the generic density bucket. Worth a look before the demo: either
      confirm Gemini is reliably reachable, or give the template a keyword-based category guess.
- [ ] **No migrations (still).** Day 6 added columns and a table, which meant deleting and
      recreating the dev DB — and that orphaned the phone's stored `artisan_id` until app data
      was cleared. Before the demo build is frozen, either add Alembic or accept that any schema
      change means re-onboarding every test device.

## Day 7–8 — demo

- [ ] **Decide + test the API fallback now, not on the day.** Live Google Maps at demo time, with
      a silent fall-back to the cached matrix if it fails.
- [ ] **Freeze before rehearsal.** No functional change after the Day-8 freeze/tag.
- [ ] **Languages:** four are tested end to end (Hindi/Bengali/Tamil/Marathi). For the live demo,
      lead with one; describe the rest as supported-but-unverified rather than faking them.
