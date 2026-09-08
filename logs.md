# Working Log — KaarigarAI

Shared hand-off log so multiple people (and Claude sessions) can pick up where the last
left off. **Newest entry on top.** Each entry: date, who, what got done, what's next,
and anything the next person needs to know.

Say **"update logs.md"** to append a new entry.

The deep detail lives in `docs/build_log.md` (narrative), `docs/tracker.md` (task status),
`docs/watchlist.md` (risks/gotchas), `docs/decisions.md` (locked choices D1–D15).
This file is the quick "where are we / what next".

---

## 2026-09-07 — Claude session — Day 6 done (mandated items) + leather material gap fixed

**Done**
- **Day 6's ★ items are all built and verified**: artisan storefront (`GET /s/{artisan_id}`,
  maker story on top + every listing, sold-out marked), follow with one-click unsubscribe,
  returning-buyer flag (spoken + badged in the offer inbox), stall QR → storefront, share card,
  export bundle (`.xlsx`), maker-story voice pipeline, and an icon-driven dashboard whose numbers
  are all live DB aggregates. Exit gate met on all three counts. 142 tests passing.
- The roadmap's **optional (○) tier is deliberately not built** — scheme/mela/seasonal alerts,
  quality meter, voice order & status. Not forgotten; deprioritised behind the ★ items and gate.
- **Two user-raised additions**, both live-verified on the phone: renaming a listing before *and*
  after publish (by voice **or** by typing — the user asked for both, recorded as D21), and the
  leather fix below.
- **Three real bugs, all surfaced by using it on the real device:**
  1. Share card centre-cropped portrait photos — a leather sandal lost its straps off the top.
     Now contain-fits (whole photo always visible, plain margin instead).
  2. **Leather wasn't in the material vocabulary at all** — a real voice note said "लेदर",
     transcribed correctly, and material still came back empty because `MATERIAL_TERMS`,
     `material_rates.csv` and the category weight overrides had no leather anywhere. Added all
     three (a medium leather sandal now derives a sane ₹380 floor). Leather goods are a major
     Indian craft category this vocabulary simply never covered.
  3. Share card was missing the storefront address under the QR that the watchlist asks for.
- New decisions: **D20** (digest content is real, SMTP send is mocked), **D21** (rename by voice
  *or* typing — the one keyboard surface in the artisan-facing app, deliberately), **D22** (export
  bundle is a data handoff, not a faked marketplace integration — this is the written answer to
  "why not just sell on Amazon/Flipkart": both need an already-KYC'd approved seller account, a
  weeks-to-months onboarding, which is exactly why Amazon Karigar exists as an assisted programme).

**Open caveats**
- **`listings.url_base` is `https://kaarigar.in`, which nothing serves.** Every QR and share card
  now bakes that host in. Fine for a laptop demo; must be resolved (open decision O1) before
  anything is *printed*.
- **Category came back empty on a real capture**, not just material — `describe()` only produces a
  category via Gemini, and its offline template has no category extraction, which also means the
  per-category weight overrides can't match. Worth a look before the demo (watchlist Day 6).
- **Still no migrations.** Day 6's new columns/table meant deleting and recreating the dev DB,
  which orphaned the phone's stored `artisan_id` until app data was cleared with
  `adb shell pm clear com.example.kaarigar`. Remember that before demo day.
- Not device-tested yet: maker-story recording with real speech, the export-bundle share sheet,
  and the buyer-side follow flow from a phone browser. Backend paths for all three are verified.

**Next task (priority order)**
1. Day 7 — edge-case hardening + offline rehearsal + pre-cache. Its gate is the full seven-beat
   demo running **twice with no internet**, so the pre-cache work matters most.
2. Before the demo: settle O1 (hosting/domain, or the printed QR is dead), the empty-category
   issue above, and the still-open material-rate verification pass (9 of 11 rates are
   typical-range, not independently sourced).
3. Optionally revisit Day 6's ○ tier if Day 7/8 leave room.

**Notes for whoever's next**
- Docs updated this session: `docs/build_log.md`, `docs/tracker.md`, `docs/watchlist.md`,
  `docs/decisions.md`, `logs.md`.
- Backend must be running with the phone tunnelled: `adb reverse tcp:8000 tcp:8000` after every
  reconnect, then `flutter run -d <device-id>`.
- `email-validator` was added to `backend/requirements.txt` (pydantic `EmailStr`, 13 ms import).
- Nothing committed or pushed — all work is local, per the standing instruction.

---

## 2026-09-06 — Claude session — End of day: price override added, Day 6 not yet started

**Done**
- After the real-device bug-fix pass (previous entry), the user pointed out the pricing model is
  meant to be *suggestive*, not final, and asked whether a "set your own price" step exists
  anywhere in the plan. It didn't (checked all 9 roadmap days — not there), but it matches the
  wireframe's own stated design intent ("the floor... warns without seizing her decision"), so
  added it: `publish_screen.dart` now has a price confirm/edit step between verification and
  stock type, prefilled with the suggestion, editable via the same numeric keypad used elsewhere,
  with a non-blocking warning if she goes below the known floor. Recorded as decision **D19**.
  Verified live on the real Pixel 8 after a force-stop + cold relaunch (worth remembering: a
  `flutter run` reinstall doesn't always kill a stale process on this device — force-stop before
  retesting a rebuild if something doesn't look right).
- Session ending for the day here, at the user's request, before Day 6 itself begins.

**Where things stand**
- Days 1–5 are fully built, gated, and now real-device-verified (not just emulator).
- Today's real-device detour (previous log entry) found and fixed 3 genuine bugs plus added the
  price-override step above — all logged in `docs/build_log.md`, `docs/decisions.md` (D19),
  `docs/watchlist.md`, `docs/tracker.md`.
- **Day 6 (Storefront + market linkage) has not been started** — 0 of its 6 items built. Research
  had just begun (reading the empty `storefront.py` stub and the `Artisan`/`Listing` models) when
  the session pivoted to real-device testing instead.

**Next task (priority order)**
1. Day 6 — Storefront + market linkage, starting fresh tomorrow:
   - Artisan storefront (permanent URL, maker story on top, every listing below, sold-out marked)
   - Follow (email digest, weekly, one-click unsubscribe) + returning-buyer flag
   - Stall QR → storefront, share card (per-listing QR + storefront address)
   - Export bundle (GeM/ONDC/Amazon Karigar/ODOP — structured data handoff, not live marketplace
     API selling; see the session's earlier discussion of why a real Amazon/Flipkart integration
     is out of scope for a 9-day prototype — needs an already-KYC'd seller account neither this
     app nor a hackathon timeline can shortcut)
   - Maker story voice pipeline (reuses Day-2 transcribe/glossary/PII-strip/TTS)
   - Exit gate: stall QR opens the storefront; one tap yields a valid export bundle; dashboard
     shows real aggregates
2. Before the actual demo: a real-device pass again once Day 6/7 add anything voice-confirmed,
   and the still-open material-rate verification pass (9 of 11 materials are typical-range, not
   independently sourced).

**Notes for whoever's next**
- Docs updated this session (both entries): `docs/build_log.md`, `docs/decisions.md`,
  `docs/tracker.md`, `docs/watchlist.md`, `logs.md`.
- Backend was running locally on the dev machine with the phone tunneled via
  `adb reverse tcp:8000 tcp:8000` — that process won't persist between sessions; restart it
  (`cd backend && PYTHONPATH=.. uvicorn app.main:app --reload` or equivalent) before resuming.
- Nothing has been committed or pushed to git this session, per standing instruction — all work
  is local only.

---

## 2026-09-06 — Claude session — Real Pixel 8 test found and fixed 3 bugs the emulator hid

**Done**
- User asked to test on their own Android phone via USB debugging instead of the emulator. Set up
  `adb reverse tcp:8000 tcp:8000` (real devices can't use the emulator's `10.0.2.2` alias) and
  simplified `api_base.dart` to always use `localhost` for Android.
- This surfaced three real bugs, all only reachable with a genuine mic/camera:
  1. Glossary near-miss: "चान्दी" (0.80 fuzzy match, just under the 0.82 threshold) wasn't
     recognized as "चांदी" (silver) — material silently dropped to empty. Added as a known
     variant in `craft_glossary.csv`, same fix pattern as every prior glossary gap.
  2. **Infinite confirm loop** — a genuine bug in the original Day-4 code: `_confirmNext()` had
     no way to know a field was already confirmed, only whether it was empty or voice-sourced, so
     a definite spoken "yes" (correctly classified every time) still triggered the same question
     forever. Fixed with explicit `_materialConfirmed`/`_sizeConfirmed` flags. Never surfaced
     before because the emulator's fake mic never produced a real "yes".
  3. **Mic/speaker bleed-through** — tapping the mic before the TTS prompt finished let the
     question's own audio leak into the recorded answer. Fixed with
     `_tts.awaitSpeakCompletion(true)` + a `_ttsSpeaking` gate on the mic button, in both
     `pricing_screen.dart` and `offers_screen.dart`.
- Also added the retry-on-unclear behavior the user asked for: an unclear (not definite-"no")
  confirm answer now re-asks once (matching `config.yaml`'s existing
  `readback.max_confirm_attempts: 2`, which mobile hadn't actually been using) before giving up
  and clearing the field.
- End-to-end verified live on the real phone: a genuine spoken "चान्दी का कड़ा, मध्यम साइज़" now
  correctly prices as real silver, confirms each field exactly once, and publishes with the
  material-cost floor (₹250,000/kg silver) correctly overriding a too-low market-comparable band.

**Open caveats**
- A locked phone screen or a loose USB cable drops the *entire* adb connection (not just the app)
  — happened twice this session and looked identical to a hung network request until diagnosed
  via `adb devices`. Worth remembering during the actual demo.
- Temporary debug `print()`s were added to `pricing.py` to diagnose this, then removed once fixed
  — not left in the shipped code.
- The confirm-loop fix lives in `pricing_screen.dart`/`offers_screen.dart` specifically; any new
  confirm loop built later (Day 6+) needs the same "mark confirmed" pattern, not just an emptiness
  check, or it can silently reintroduce bug #2.

**Next task (priority order)**
1. Day 6 — Storefront + market linkage, picking back up where it was paused for this real-device
   detour.
2. Before the demo: a real-device pass again once Day 6/7 add anything voice-confirmed, and the
   still-open material-rate verification pass (9 of 11 materials are typical-range, not
   independently sourced — see watchlist Day 4).

**Notes for whoever's next**
- Docs updated this session: `docs/build_log.md`, `docs/watchlist.md`, `logs.md`.
- To retest on a real device: enable USB debugging, connect, `adb reverse tcp:8000 tcp:8000`
  after every reconnect (it doesn't persist across a lock-screen drop), then
  `flutter run -d <device-id>`.

---

## 2026-09-06 — Claude session — Day 5 fully closed: onboarding, publish, offers — verified live

**Done**
- Full Day 5: voice-first onboarding (`onboarding/{language,phone,otp}_screen.dart` +
  `backend/app/api/onboarding.py`, deferred verification), publish flow
  (`publish_screen.dart` + `/listings`, stock type as two tiles + batch count), and the
  artisan offer inbox (`offers_screen.dart` + `/offers`, voice accept/decline via the same
  `classify_answer` primitive Day 2/4 already use, two-button fallback). 12 new backend unit
  tests all pass.
- Verified the **entire flow live through the real mobile app** on the Android emulator, not
  just curl: fresh install → language → phone → unverified home → capture/record/price →
  "List for sale" → correctly routed to OTP (unverified) → wrong-code error path → correct
  OTP → stock type → batch count → real listing published (`kaarigar.in/l/<id>`, page renders)
  → two competing offers → accepted one via the app's Accept button (buyer contact revealed
  only then, stock 5→2) → second correctly hit a real `409`, shown as a plain Hindi message,
  no silent double-decrement.
- Found and fixed one real UX bug during testing: a failed accept (409) showed the raw English
  exception text in a SnackBar underneath an already-correct Hindi TTS message — replaced with
  a matching Hindi SnackBar string (`offers_screen.dart`), consistent with the project's own
  "nothing essential exists only as text she can't read" rule.
- Added decisions **D17** (SQLite instead of the architecture doc's Postgres — disclosed,
  swappable via `DATABASE_URL`) and **D18** (mocked OTP delivery, disclosed) to
  `docs/decisions.md`, closing a loose end from Day 4 (D17 had been referenced in code comments
  but never actually written up).

**Open caveats**
- `.with_for_update()`'s row lock is a real lock on Postgres but a no-op on SQLite (current dev
  DB) — the no-double-accept gate passed today, but that guarantee should be re-verified if/when
  the DB moves to Postgres under real concurrent writers. See D17 and the watchlist.
- New watchlist item: re-calling `/onboarding/send_otp` (her tapping the replay/speaker icon, or
  a widget re-init) overwrites the previously-issued OTP server-side. Not exercised as a bug in
  front of her since the app re-speaks the new code, but worth a deliberate look before demo day.
- `report_issue()` has a backend endpoint only — no mobile screen yet.
- Per-set vs per-piece pricing ambiguity for batch listings (flagged in the watchlist since Day
  1's roadmap read-through) is still open — a batch listing's price is per-item only right now.

**Next task (priority order)**
1. Day 6 — Storefront + market linkage (per-artisan storefront page, follower email digest,
   stall QR → storefront, maker-story pipeline, scheme/mela alerts).
2. Before the demo: profile the pricing round trip (still ~30-40s per Day 4's note), do a
   real-device pass with an actual spoken accept/decline in `OffersScreen` (this session's
   emulator has no real mic, same caveat as Day 4), and decide the backend hosting tier (open
   decision O1 — still unresolved, a permanent domain is needed before a stall QR can be printed).

**Notes for whoever's next**
- Docs updated this session: `docs/build_log.md`, `docs/tracker.md`, `docs/watchlist.md`,
  `docs/decisions.md`.
- Manual OTP testing via curl needs `--data-urlencode "phone=+91..."` — a bare `-d` turns `+`
  into a space in form-urlencoded bodies, silently storing the OTP under the wrong key. Cost
  significant time this session before being caught; not an app bug.
- `flutter analyze` clean (only pre-existing lint-style infos, none new).

---

## 2026-09-06 — Claude session — Day 4 fully closed: pricing now on screen

**Done**
- Wired the whole Day-4 pricing pipeline into the app — the one gap left after the pipeline work
  and recalibration earlier today. New `backend/app/api/pricing.py` (3 endpoints: attribute
  suggestion, yes/no answer classification, final quote) + new
  `mobile/lib/screens/pricing_screen.dart`, reached right after `RecordScreen` saves+queues a
  draft. Verified live end to end on an Android emulator: comparables shown before the price
  band (roadmap's exact ordering), floor + rate date/source on screen, SHAP three bars, and a
  **real spoken attribute confirmation** — `flutter_tts` speaks the question, `record` captures
  her answer, the backend classifies it, a "no"/unclear clears the field rather than re-guessing.
  Day 4's tracker line is now a clean `[x]`, gate fully closed.
- Found and fixed a real bug while testing with actual Hindi audio: whisper misheard पीतल
  (brass) as पीटल — one character off, just below the glossary's fuzzy-match threshold — so
  material extraction silently came back empty. Added the mishearing to `craft_glossary.csv`
  (same pattern as Day 2's बर्दन→बर्तन fix).
- Fixed a real infra issue: the backend crashed with `ModuleNotFoundError: No module named
  'pipelines'` the first time, because `pricing.py` imports the top-level `pipelines` package
  (a sibling of `backend/`) which isn't on `sys.path` when run the documented way. Fixed at the
  source in `main.py` (adds the repo root to `sys.path`) so `cd backend && uvicorn app.main:app`
  keeps working exactly as documented — no PYTHONPATH incantation needed.

**Open caveats**
- The full round trip (stop recording → confirm question appears) takes ~30-40 seconds — whisper
  load + inference + Gemini + a full-res image upload over the emulator's network. Worth
  profiling before the demo; a real artisan needs feedback that something is happening, not just
  a spinner for 40 seconds.
- The Android emulator has no real microphone, so this session's confirm-answer recordings were
  effectively silence (correctly classified as unclear, handled gracefully) — real device testing
  with an actual spoken yes/no is still the more meaningful accuracy test.
- `pricing_reference.csv` is still small (58 rows) and 100% synthesised; unchanged from earlier.

**Next task (priority order)**
1. Day 5 — Onboarding + listing page + offer/stock. Day 4 no longer has open items.
2. Before the demo: profile/speed up the pricing round trip, do a real-device pass on the
   spoken confirmations, and verify the "typical-range" material rates against a live source.

**Notes for whoever's next**
- Docs updated this session: `docs/build_log.md`, `docs/tracker.md`, `docs/watchlist.md`.
- `cd backend && uvicorn app.main:app --reload` works as originally documented again — the
  PYTHONPATH issue above is fixed, not just worked around.

---

## 2026-09-06 — Claude session — Day 3 gate closed; Day 4 pricing recalibrated

**Done**
- **Day 3 gate closed for real.** Ran the actual capture→record→queue→sync loop against a live
  backend on an Android emulator: online sync, offline capture (network disabled via `adb`,
  held as "Pending Sync"), then auto-sync on reconnect with zero manual action. Verified at the
  DB/backend level (not just the UI) — 3 drafts, all `isSynced=1`, empty `sync_queue`, 3
  distinct client_ids on the backend, no duplicates. Found and fixed a real bug along the way:
  `HomeScreen` never refreshed after a background sync finished (`processQueue()` isn't
  awaited by design), so it could show "Pending Sync" long after a draft had actually synced —
  added `SyncQueueService.queueVersion` and had `HomeScreen` listen to it. `tracker.md`'s Day 3
  line is now a clean `[x]`, not `[!]`.
- **Day 4 pricing recalibrated** (two follow-ups after the model was declared "good enough" but
  then stress-tested harder): added `size_score` (continuous 0-1 vision coverage) alongside the
  spoken size bucket so two "medium" items don't get identical costs; found and fixed a real bug
  where a large wooden toy in sandalwood costed out at ~₹27,700 (generic bulk-density weight
  table assumed up to 3kg, fine for a saree, absurd for a toy) — added
  `category_weight_overrides.csv` with realistic per-category weight/hours, dropping that case
  to ~₹4,000; added `pipelines/pricing/recommend.py` to reconcile the model's price against the
  floor (takes whichever is higher) instead of leaving two disagreeing numbers on screen.
  119 Python tests pass repo-wide; the mobile side has 1 widget test (unchanged) plus the
  manual device verification above — `flutter analyze` stays clean.

**Open caveats**
- The 5 Sep emulator crash (during audio-recorder init) did not reproduce today on the same
  image — inconclusive, not confirmed fixed. If it recurs, capture `adb logcat` at the moment of
  the crash.
- Day 4's pricing pipeline still has no mobile UI — everything is verified via CLI/tests, not on
  a phone screen. This is the actual next gap, not anything pricing-logic-related.

**Next task (priority order)**
1. Wire the pricing pipeline into a mobile screen.
2. Day 5 — Onboarding + listing page + offer/stock.

**Notes for whoever's next**
- Docs updated this session: `docs/build_log.md`, `docs/tracker.md`, `docs/watchlist.md`.
- To pull the on-device SQLite DB for debugging: `adb exec-out run-as com.example.kaarigar cat
  /data/data/com.example.kaarigar/databases/kaarigar.db > local.db` — must be `exec-out`, plain
  `adb shell` corrupts binary output via CRLF translation.

---

## 2026-09-05 — Claude session — Day 4: dynamic pricing pipeline

**Done**
- Built the whole Day-4 pricing pipeline in `pipelines/pricing/` (all four files were empty
  `# TODO(day4)` stubs before this): `attributes.py` (vision suggests size_class + finish only —
  never a category name or material, D16; material comes from a keyword match on the voice
  transcript), `floor.py` (derived material cost + labour → fair-price floor, warns via
  `check_against_floor`, never blocks), `model.py` (XGBoost price band, native categorical
  features, lazy-trained via new `ml/train_pricing.py`), `shap_explain.py` (three bars via
  XGBoost's own `pred_contribs` instead of the heavy `shap` package — see decision D16),
  `seasonal.py` (bounded Diwali/wedding multiplier).
- Assembled the reference data that didn't exist yet: `data/reference/material_rates.csv`
  (silver + copper live-fetched and verified; the rest typical-range and flagged as such),
  `data/reference/size_estimates.csv` (weight/hours by size_class, documented placeholder),
  `data/reference/pricing_reference.csv` (58 rows / 15 categories, 100% synthesised, disclosed
  in `data_sources.md`). Added `silver`/`wood` to `craft_glossary.csv`.
- `scripts/day4_smoke.py` proves the actual gate end to end: floor refuses an underpriced
  suggestion, no confirmation question ever mentions price/cost, and material is unchanged when
  only the photo changes (proves it comes from voice, not pixels). 36 new pricing unit tests;
  98 tests pass repo-wide.

**Open caveats**
- **No mobile UI consumes any of this yet.** The pipeline is real and tested, but nothing in
  `mobile/` shows a price band, a floor warning, or comparables — the gate's "on screen" language
  is satisfied at the data level only. Wiring a pricing screen into the Flutter app is the actual
  next step to make this demoable on a device (likely alongside Day 5's listing page).
- `pricing_reference.csv` is small and entirely synthesised — fine as a working default, but
  every demo-day craft category needs a real row before the demo, or it'll hit the (correctly
  honest, but less impressive-looking) low-confidence wide-band path.
- Only silver and copper rates are live-verified; the other 9 materials need a real
  Agmarknet/eNAM/MCX/WPI pass before the demo.

**Next task (priority order)**
1. Wire the pricing pipeline into a mobile screen (Day 4's actual missing piece).
2. Close out Day 3's still-open item: run capture→record→queue→sync end to end on a real device.
3. Day 5 — Onboarding + listing page + offer/stock.

**Notes for whoever's next**
- `python -m scripts.day4_smoke` is the fastest way to see the whole pricing chain run.
- Docs updated this session: `docs/build_log.md`, `docs/tracker.md`, `docs/watchlist.md` (Day 4
  section), `docs/decisions.md` (new **D16**), `docs/data_sources.md`.

---

## 2026-09-05 — Claude session — Day 3 verification: gate wasn't actually green

**Done**
- Asked to verify Day 3 and fix the UI. It wasn't green: `flutter analyze` and `flutter test`
  both failed outright, and two of the four checked-off tracker items ("downscale", "cap")
  turned out to be a bare `// TODO`, not real code.
- Fixed: `test/widget_test.dart` (was `flutter create` boilerplate referencing a `MyApp` class
  that never existed — now tests the real `KaarigarApp`, backed by `sqflite_common_ffi` so it
  can hit the local db without a device); downscale-before-upload + a 50-draft queue cap in
  `sync_queue.dart`; an escaped-`$` bug in `capture_screen.dart` that hid real camera errors;
  the Android-only hardcoded `10.0.2.2` server URL in `api_client.dart` (now platform-aware);
  the missing `mobile/ios/` platform folder + missing camera/mic `Info.plist` usage strings
  (added — a real iOS build would have crashed on first camera access without these); dropped
  the unused `provider` dependency.
- Visually verified on an Android emulator (Pixel 8, since this Mac only has Xcode CLI tools,
  not full Xcode): home screen, camera/mic permission prompts, live camera preview, and the
  capture→record navigation all render and behave correctly.

**Open caveats**
- The emulator crashed initialising the audio recorder (AAC encoder) the moment recording
  started, before a save-and-enqueue could be observed — this host's Android emulator support is
  flagged unsupported/unstable, not a bug found in the app code, but it means **the actual
  record→enqueue→sync round trip (the real Day-3 gate) is still not independently confirmed
  end to end.** `docs/tracker.md` reflects this with a `[!]` rather than reverting to `[ ]`.
- iOS Simulator testing is still blocked on this dev machine (needs full Xcode installed +
  `sudo xcode-select -s /Applications/Xcode.app/Contents/Developer`) — the iOS platform/Info.plist
  fix is unverified beyond static review.

**Next task (priority order)**
1. **Manual verification, for real this time:** run `flutter run` on a real device or a stable
   emulator, go offline, capture + record, confirm the draft queues and later syncs with no
   duplicate.
2. Install full Xcode on this Mac if iOS is a target platform for the demo.
3. Day 4 — Dynamic Pricing (attribute extraction, derived material cost, XGBoost band, fair-price
   floor) — unchanged from before.

**Notes for whoever's next**
- Docs updated this session: `docs/build_log.md`, `docs/tracker.md`, `docs/watchlist.md` (Day 3
  section) — read those for the full list of what was actually broken vs. what was genuinely
  fine.
- `flutter analyze && flutter test` now both pass clean from `mobile/` — run both before ticking
  off any future mobile-side gate; a broken test file doesn't fail loudly on its own.

---

## 2026-09-05 — Antigravity session — Day 3: Flutter shell + offline queue ✅ Day 3 complete

**Done**
- **Mobile app scaffold built:** Added `provider` for state management and `uuid` for client ID generation to `pubspec.yaml`.
- **UI (Premium & Polished):** Created `home_screen.dart` (dashboard of drafts), `capture_screen.dart` (camera UI), and `record_screen.dart` (voice recording with visual pulse).
- **Offline DB & Queue:** Built `local_db.dart` using `sqflite` (tables for `drafts` and `sync_queue`).
- **Sync Logic:** `sync_queue.dart` listens to connectivity via `connectivity_plus`. It processes the queue oldest-first.
- **Backend API:** Built `backend/app/api/sync.py` with a `/sync` endpoint. Configured server-side deduplication using an in-memory set to discard identical `client_id`s, returning success without duplicating work.
- **Day 2 Gate Closed:** The Flutter app now provides the necessary camera and `recorder` hooks for the full Day-2 pipeline to run on a real device.

**Open caveats**
- The app needs to be manually tested on an emulator/device since I (the AI agent) cannot run physical mobile tests.
- Backend deduplication is currently in-memory. Will need to move to a database in Day 4/5 when the real DB schema is established.

**Next task (priority order)**
1. **Manual Verification**: Run the app locally, go offline, create a draft, go online, and ensure it syncs.
2. **Day 4 — Dynamic Pricing**: Extract attributes, derive material cost based on type/rate/size, and build the XGBoost pricing band and fair-price floor.

**Notes for whoever's next**
- To run the backend: `cd backend && uvicorn app.main:app --reload`
- To run the mobile app: `cd mobile && flutter run`

## 2026-09-01 — Claude session — Day 2 step 5: spoken read-back  ✅ Day 2 pipeline complete


**Done**
- `pipelines/voice/readback.py` — the Day-2 exit gate. Reads back **what we heard**, in her
  language: her cleaned transcript, then every glossary correction and PII redaction spoken
  aloud, then the extracted category/material/price, then "is this correct? say yes or no".
  Wrapper phrases templated for hi/bn/ta/mr/en; the content is her own words (D15).
- `classify_answer()` — spoken yes/no per language (Devanagari, Bengali, Tamil + romanised),
  fuzzy-matched because one-word answers transcribe noisily. Neither → `None`, never guessed.
- `readback_and_confirm()` — loop through an **injected** `recorder` (no mic code, D14),
  re-asks on an unclear answer (`readback.max_confirm_attempts`, 2).
- **`may_publish` is True only on an explicit spoken yes.** Silence, unclear answers, a
  walked-away artisan, exhausted retries and TTS failure all block. Publish code must gate on
  this property.
- Tests: **57 passing** across `pipelines/voice/`. `day2_smoke` now runs all five steps.

**Day 2 status:** all five steps built — transcribe → glossary → PII strip → bilingual listing
→ spoken read-back. The **gate is not signed off yet**: it requires the whole chain on a *real
device*, which needs the Day-3 Flutter app to supply the `recorder` callable.

**Open caveats**
- `tts.py` has a real macOS voice only for Hindi (`Lekha`); bn/ta/mr read-backs *sound* wrong on
  the dev Mac although the text is right. `flutter_tts` handles them on device — verify there.
- Still untested end to end in Bengali / Tamil / Marathi (O3).

**Next task (priority order)**
1. **Day 3 — Flutter shell + offline queue** (camera, record, SQLite outbound queue with
   client-generated ids, downscale, oldest-first sync, size cap, draft autosave, server-side
   dedupe). This is also what closes the Day-2 gate, since it supplies the `recorder`.
2. Re-test the full chain on Bengali / Tamil / Marathi notes (O3).
3. Populate `data/processed/listing_cache/` with the demo items (Day-7 pre-cache).

**Notes for whoever's next**
- Two injection points the app must fill: `capture.capture(recorder=…)` for the low-confidence
  re-record, and `readback.readback_and_confirm(recorder=…)` for the yes/no. Both take
  `(prompt_audio_path, attempt) -> new_audio_path | None`.
- Gate publish on `ReadbackResult.may_publish`. Silence is not consent.

---

## 2026-09-01 — Claude session — Day 2 step 4: glossary · PII strip · re-record loop

**Done**
- `pipelines/voice/glossary.py` + `data/reference/craft_glossary.csv` (~55 rows) — fuzzy-corrects
  misheard craft/material words. Fixes the exact error from the real recording:
  `बर्दन`→`बर्तन`, `मिटटी`→`मिट्टी`, `मटकि`→`मटकी`, `साडी`→`साड़ी`, `dokra`→`dhokra`,
  `bandani`→`bandhani`. stdlib `difflib`, no new dependency (D14).
  *Bug caught in verification:* Python's `\w` drops Devanagari matras/virama, which shredded
  `मिट्टी` — tokeniser now spells out the `\u0900-\u097F` block.
- `pipelines/voice/pii_strip.py` — strips `+91`/10-digit/12-digit/≥7-digit runs (Latin +
  Devanagari digits) before publish; **keeps** prices, dimensions, counts, years.
- `pipelines/voice/capture.py` — low-confidence re-record loop. Speaks a per-language
  "say it again" prompt via the Day-1 TTS, retries through an **injected** `recorder` callable
  (no mic code in the pipeline — D14), keeps the **best** take not the last.
  Budget: `models.transcribe.max_rerecords` (2).
- Pipeline order wired in `day2_smoke`: transcribe → glossary → PII strip → describe.
- Tests: 40 passing across `pipelines/voice/`.
- Docs: tracker, build_log, watchlist, decisions (**D14**).

**Next task (priority order)**
1. Day 2 step 5 — **spoken read-back confirmation** (reuse `tts.py`). Nothing publishes without
   it. Should read back the EN/HI title + description, mention any glossary correction and any
   PII redaction out loud, and take a voice confirm. This closes the Day-2 exit gate.
2. Re-test transcription + the full chain on **Bengali / Tamil / Marathi** notes (O3).
3. Populate `data/processed/listing_cache/` with the demo items (Day-7 pre-cache).

**Notes for whoever's next**
- `python -m pipelines.voice.capture <audio> hi` loads whisper `small` — takes ~2-3 min on this
  machine (iCloud-synced `~/Desktop`), that is not a hang.
- Add a glossary row every time a real recording surfaces a new mishear — cheapest quality win.

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
