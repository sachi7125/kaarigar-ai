# Build Log

Dated, narrative record of what was built — **appended when a task is done**. Each entry:
what changed, how to run/verify it, and anything non-obvious a future reader (or the viva
panel) would need. Newest first.

Format:
```
## YYYY-MM-DD — <short title>   [Day N]
**Done:** ...
**How to run / verify:** ...
**Notes / gotchas:** ...
**Commit:** <hash or "pending">
```

---

## 2026-09-07 — Day 6: storefront, follow, stall QR, share card, export bundle, maker story   [Day 6]
**Done:** all of Day 6's mandated (★) items, plus two user-raised additions and two real bugs
found by testing on the physical phone. The optional (○) tier — scheme/mela alerts, quality
meter, voice order status — is deliberately not built; the ★ items and the exit gate came first.

**Backend (new/changed):**
- `app/db/models.py` — `Follower` (email + unguessable `secrets.token_urlsafe(24)` unsubscribe
  token), `Artisan.maker_story_text_en/_hi/_audio_path`, `Offer.is_returning_buyer`. No `event`
  table: dashboard aggregates are COUNT/SUM queries over the tables that already exist —
  event-sourcing would be scaffolding a prototype doesn't need to answer "how many followers".
- `app/api/storefront.py` (was an empty Day-0 stub) — `POST /storefront/maker_story`,
  `GET /storefront/{id}`, `POST /storefront/follow`, `GET /storefront/{id}/digest_preview`,
  `GET /storefront/{id}/qr` (PNG), `GET /storefront/{id}/dashboard`.
- `app/api/listings.py` — `GET /listings/{id}/share_card` (Pillow-composed 1080×1080 PNG),
  `GET /listings/{id}/export_bundle` (openpyxl `.xlsx`), `POST /listings/rename_by_voice`,
  `PATCH /listings/{id}` (rename).
- `app/api/offers.py` — returning-buyer flag computed at submission time from prior **accepted**
  offers by the same contact to the same artisan (not a live join, so it can't change under an
  offer that already exists); surfaced in `GET /offers`.
- `app/web/storefront_page.py` + `templates/storefront.html` — public `GET /s/{artisan_id}`
  (maker story on top, every listing below with sold-out marked, follow form) and
  `GET /unsubscribe/{token}` as a plain no-JS GET.
- `pipelines/voice/maker_story.py` (new) — reuses the Day-2 chain (transcribe → glossary → PII
  strip) then its own Gemini prompt + offline template. Deliberately *not* `describe()`: a bio
  is a different kind of text, and overloading one prompt with two jobs would degrade both. An
  empty transcript returns an honest generic line, never an invented name/place/years.
- `backend/tests/test_storefront.py` (6 tests) + `pipelines/voice/test_maker_story.py` (5) —
  dashboard arithmetic, follow idempotency, and all three returning-buyer cases (first-ever
  offer, after a prior accepted one, and *not* after a merely pending one).

**Mobile (new/changed):** `storefront_client.dart`, `dashboard_screen.dart` ("My Shop": real
aggregates, maker-story card, printable stall QR, per-listing Share/Export/rename),
`maker_story_screen.dart`, `rename_listing_screen.dart`, plus `share_plus` for the OS share
sheet and the returning-buyer badge + spoken note in `offers_screen.dart`.

**How to run / verify:** backend as usual; `PYTHONPATH=. .venv/bin/python -m pytest backend/tests/ pipelines/ -q`
→ 142 passing. Curl-verified every endpoint end to end (register → publish → follow → digest
preview → QR → dashboard → share card → export bundle → rename), browser-verified the storefront
and unsubscribe pages, and device-verified "My Shop", the share card, the export bundle and the
rename flow on the physical Pixel 8.

**Two real bugs, both found by using it on the real phone:**
1. **Share card cropped the product.** The photo band did a centre "cover" crop into a
   landscape-shaped area; a portrait phone photo of a leather sandal lost its strap and buckles
   off the top. Switched to a contain-fit (scale to fit entirely, centred on the placeholder
   colour) — a plain margin on one axis is the honest trade against silently cutting the product
   out of its own listing photo.
2. **Leather wasn't in the material vocabulary at all.** A real voice note said "लेदर" clearly
   and transcribed correctly, but `MATERIAL_TERMS` had no entry for it — nor did
   `material_rates.csv` or the category weight overrides — so material came back empty and the
   floor fell back to "unknown". Leather goods (chappals, bags, belts) are a major Indian craft
   category the vocabulary simply never covered. Added `leather`/`चमड़ा`/`चमड़े`/`लेदर` to
   `MATERIAL_TERMS`, a `leather` row to `material_rates.csv` (₹400/kg, typical-range, bulk
   density class, sourced/dated in the same format as every other row), and `leather footwear` /
   `leather bag` rows to `category_weight_overrides.csv` — without those the generic `bulk`
   bucket would price a pair of chappals as 1 kg of hide, the same class of bug the silver and
   wooden-toy overrides already exist to prevent. A medium leather sandal now derives a ₹380
   floor (0.2 kg × ₹400 + 5 h × ₹60), which is sane.

Also fixed two small ones. The inline unsubscribe page didn't declare `color-scheme: light`, so a
dark-mode browser rendered it unpredictably. And the share card was missing the **storefront
address under the QR** that the watchlist explicitly asks for — without it a forwarded card is a
dead end once that one listing sells out; it has to be right-aligned by measured text width,
since artisan ids vary in length and a fixed x ran the URL off the edge of the card.

**Notes / gotchas:**
- **The dev SQLite DB had to be recreated** to pick up the new columns/table — `init_db()` is
  `create_all`, which never ALTERs an existing table, and there's no Alembic (session.py says
  so). Only synthetic test data was lost, but it orphaned the *phone's* locally stored
  `artisan_id`, which then 404'd on the dashboard until the app's data was cleared
  (`adb shell pm clear com.example.kaarigar`). Worth remembering before the demo: recreating the
  DB means re-onboarding on the device too.
- `email-validator` added (for pydantic `EmailStr` on the follow endpoint) — 13 ms import, well
  clear of the import-time tax D9/D11/D12/D16 refused elsewhere.
- Share-card Devanagari depends on a host font (`Devanagari Sangam MN` on macOS, Noto/Lohit on
  Linux); if none is found the card degrades to English-only text rather than tofu boxes.

**Commit:** pending

---

## 2026-09-06 — Artisan can now edit the suggested price before publishing   [pre-Day 6]
**Done:** added a price confirm/edit step to `publish_screen.dart`, between verification and the
stock-type tiles. Prefilled with `PricingScreen`'s suggested price (so doing nothing still
works), editable via the same `NumericKeypad` widget used for phone/OTP/batch-count entry — no
free-text keyboard, consistent with the rest of the app's input pattern. If the edited amount
falls below the known fair-price floor, a plain amber warning names the floor amount but never
blocks (matches `floor.py`'s existing "warn, never block" design — see decision D19). The
suggested price was always meant to be advisory (the wireframe itself: the floor "warns without
seizing her decision"), but until today nothing let her actually change the number before it
published.

- `mobile/lib/screens/publish_screen.dart` — new `floorInr` param, new `_Step.priceConfirm`
  (entered right after the verification check, before stock type), `_priceConfirmView()`,
  `_finalPrice`/`_belowFloor` getters. `_publish()` now sends `_finalPrice` instead of
  `widget.priceInr`.
- `mobile/lib/screens/pricing_screen.dart` — passes `floorInr: quote.floor.known ? quote.floor.floorInr : null`
  into `PublishScreen` at the "List for sale" call site.

**How to run / verify:** verified live on the real Pixel 8 (same device as the bug-fix pass
below): captured a silver bangle, confirmed material+size, tapped "List for sale", and landed on
"आप किस कीमत पर बेचना चाहती हैं?" with the suggested price pre-filled and editable — confirmed
working after a force-stop + cold relaunch ruled out a stale process serving pre-fix code (worth
remembering: `flutter run`'s reinstall doesn't always kill an existing process on this device/
Android version combination — `adb shell am force-stop <pkg>` before retesting a rebuild is the
reliable way to be sure you're looking at the new code, not a leftover instance).

**Notes / gotchas:**
- No upper bound on the entered price — only the floor (lower bound) is checked. Not treated as a
  gap: the floor is the only number the pipeline actually derives and can speak to; an upper
  sanity check would need its own justification (e.g. band ceiling) that wasn't asked for.
- This is a UX/trust fix, not a roadmap line item — doesn't map to any Day N task, so it isn't a
  new tracker.md checkbox; recorded here and as decision D19 instead.

**Commit:** pending

---

## 2026-09-06 — Real-device pass on a physical Pixel 8 (USB debugging) — 3 real bugs found and fixed   [Day 4/5]
**Done:** all prior "live" verification of the pricing confirm loop and voice accept/decline had
only run on the Android emulator, whose fake camera and fake microphone can't exercise real
speech or a real photo. Connected an actual Pixel 8 over USB (`adb reverse tcp:8000 tcp:8000`,
since the emulator's `10.0.2.2` alias doesn't exist on real hardware — `api_base.dart` simplified
to always use `localhost`, relying on `adb reverse` for both emulator and device) and re-ran the
capture → describe → confirm → price flow with genuine spoken Hindi. Found three real bugs a
fake mic could never have surfaced:

1. **Glossary gap:** whisper transcribed "चांदी" (silver) as "चान्दी" — a legitimate alternate
   rendering, scoring 0.80 against the closest known variant, just under the 0.82 fuzzy-match
   threshold (same class of near-miss as the पीतल/पीटल fix from 5 Sep). Material silently came
   back empty, and the price fell back to a generic, material-blind estimate. Fixed by adding
   "चान्दी" as a known variant in `craft_glossary.csv`, same pattern as every prior glossary fix.
2. **Infinite confirm loop, real bug in the original Day-4 code:** `_confirmNext()` decided
   whether to (re-)ask about material using `_material.isNotEmpty && _materialSource == 'voice'`
   — a condition that stays true forever once material is voice-sourced, with nothing recording
   that it had already been *confirmed*. A definite spoken "हाँ" (yes) was correctly classified
   every time, but the screen kept re-asking the same question anyway. This never surfaced before
   because the emulator's silent fake audio only ever produced "unclear" or "no" verdicts, which
   happen to clear the field and break the loop by accident — a real "yes" from a real person was
   never exercised until today. Fixed with explicit `_materialConfirmed`/`_sizeConfirmed` flags in
   `pricing_screen.dart`, checked in `_confirmNext()` alongside the existing emptiness checks.
3. **Mic/speaker bleed-through:** a real phone's speaker output can leak into its own microphone
   recording if she taps the mic before the TTS prompt finishes — one captured "answer" literally
   contained "क्या यी सही है? हा या नहीं बोली? यस" (the tail of the spoken question itself,
   transcribed). Fixed by calling `_tts.awaitSpeakCompletion(true)` and gating the mic button on
   a `_ttsSpeaking` flag in both `pricing_screen.dart` and `offers_screen.dart`, so recording is
   blocked until the prompt audio has actually finished.

While fixing #2, also added the retry-on-unclear behaviour the user asked for: an unclear (not a
definite "no") confirm answer now re-asks once — using the exact `unclear` phrase already defined
in `readback.py`'s hi `_PHRASE` dict — before giving up and clearing the field, instead of
silently dropping a possibly-correct reading over one noisy recording. Matches
`config.yaml`'s `readback.max_confirm_attempts: 2`, which the mobile confirm loops hadn't
actually been using until now.

**How to run / verify:** connect a real Android device with USB debugging enabled, run
`adb reverse tcp:8000 tcp:8000` (needed after every reconnect — a phone lock screen or a flaky
cable both drop this and the whole adb session, seen twice this session), then
`flutter run -d <device-id>`. Verified live: a spoken "चान्दी का कड़ा, मध्यम साइज़" now correctly
prices as `material=silver`, confirms material once (not in a loop), confirms size after one
retry on an initially-unclear answer, and publishes with a real material-cost floor (₹250,000/kg
silver rate) correctly overriding a too-low market-comparable band (₹3,430–6,371) with a higher
floor-based price (~₹10,893) — the "floor visibly refuses an underpriced suggestion" behaviour
from Day 4, now demonstrated with a genuine high-value material rather than a synthetic case.

**Notes / gotchas:**
- Real hardware surfaces different failure modes than the emulator's fake camera/mic — worth a
  real-device pass before the actual demo, not just before submission, in case anything about the
  Pixel 8 specifically (vs. whatever demo device is used) doesn't generalize.
- A locked screen or a loose USB cable drops the whole `adb` connection, not just the app — both
  happened this session and looked identical to a hung network request until diagnosed via
  `adb devices`. Worth remembering during the actual demo: keep the phone unlocked and the cable
  seated, and check `adb devices` first if anything seems to hang.
- Temporary `print()` debug logging was added to `pricing.py`'s two endpoints to diagnose this,
  then removed once the root causes were found — not left in the shipped code.

**Commit:** pending

---

## 2026-09-06 — Day 5: onboarding, publish, and the offer/stock gate — verified live end to end   [Day 5]
**Done:** full Day 5 build — voice-first onboarding, deferred verification, publish flow with
stock type, and the artisan offer inbox with voice accept/decline — all built, unit-tested, and
then verified through the *actual* mobile app on an Android emulator (not just curl), including
the specific double-accept gate criterion.

**Backend (new):**
- `app/db/models.py` — `generate_short_id()` (frozen permanent-URL id format), `Artisan`,
  `Listing`, `Offer`, `IssueReport`.
- `app/services/stock.py` — `accept_offer_and_decrement()` via `.with_for_update()`.
- `app/services/offer_validation.py` — asking-price-minus-tolerance + stock-quantity auto-decline,
  rate limiting.
- `app/api/onboarding.py` — `register` / `send_otp` (mocked SMS, see D18) / `verify_otp`
  (deferred verification — only `listings.py`'s publish checks `Artisan.verified`).
- `app/api/listings.py` — `publish_listing` (verification-gated), `get_listing`,
  `list_artisan_listings`.
- `app/api/offers.py` — `submit_offer`, `list_offers_for_artisan` (hides buyer contact +
  auto-declined offers), `accept_offer` (the double-accept prevention), `decline_offer`,
  `report_issue`.
- `app/web/templates/listing.html` + `storefront_page.py` — the permanent public listing page
  (`GET /l/{listing_id}`), matching wireframe screen 6.
- `backend/tests/{conftest,test_stock,test_offer_validation}.py` — 12 tests, including
  `test_the_actual_no_double_accept_scenario`.

**Mobile (new):**
- `lib/widgets/numeric_keypad.dart` — `NumericKeypad` + `DigitDots`, shared by phone entry, OTP,
  and batch-count entry.
- `lib/screens/onboarding/{language,phone,otp}_screen.dart` + `services/{onboarding_client,
  artisan_session}.dart` — first-run flow (language tiles → phone keypad → unverified home) and
  the OTP screen (reached later, from publish).
- `lib/screens/publish_screen.dart` + `services/listings_client.dart` — reached from
  `PricingScreen`'s new "List for sale" button; checks verification (routes to `OtpScreen` if
  not verified), asks stock type as two tiles, asks a count for batch, calls `/listings`.
- `lib/screens/offers_screen.dart` + `services/offers_client.dart` — artisan's pending-offer
  inbox; TTS speaks each offer, mic + `classify_answer` (the same primitive Day 2's read-back
  gate and Day 4's attribute confirms use) drives voice accept/decline, with the two on-screen
  buttons as the always-available fallback per the wireframe.
- `lib/main.dart` — startup now routes to `LanguageScreen` (first run) or `HomeScreen` (returning
  artisan) based on local onboarding state, instead of always opening `HomeScreen`.

**How to run / verify:** `cd backend && PYTHONPATH=.. uvicorn app.main:app --reload` (or from repo
root: `PYTHONPATH=. .venv/bin/python -m uvicorn app.main:app --app-dir backend`), then
`PYTHONPATH=. .venv/bin/python -m pytest backend/tests/ -q` for the 12 unit tests. Live gate
walkthrough performed 6 Sep on a booted Android emulator (`flutter run -d emulator-5554`): fresh
install → language → phone → unverified home → capture → record → pricing round trip → "List for
sale" → OTP screen (correctly triggered since this artisan wasn't verified) → wrong-code error
path → correct OTP → stock-type tiles → batch count → publish succeeded, real
`kaarigar.in/l/<id>` URL shown → two competing offers submitted (curl, simulating buyers) → first
accepted through the app's `OffersScreen` (buyer contact revealed only then) → second correctly
rejected with a real `409` surfaced as a plain Hindi message, never a silent double-decrement.

**Notes / gotchas:**
- **DB is SQLite, not the architecture doc's Postgres** — see decision D17. Same ORM code,
  swappable via `DATABASE_URL`; the row-lock caveat is documented there and in the watchlist.
- **OTP delivery is mocked** — see decision D18. Genuinely generated + expiring, just returned
  in-band instead of sent by SMS; the app speaks it aloud.
- **`backend/app/main.py` needs `pipelines` on `sys.path`** (fixed 5 Sep, Day 4) for
  `cd backend && uvicorn app.main:app` to work as documented — still true and still fixed at the
  import-time root cause, not worked around per-call.
- **Manual/adb-driven UI testing pitfall (mine, not the app's):** curl calls used to fetch OTPs
  for manual entry must URL-encode the `+` in a phone number (`--data-urlencode`), or
  form-urlencoding silently turns it into a space, storing the OTP under a different key than the
  app's own request used — several genuine-looking "wrong OTP" failures during this session were
  this, not an app bug. Worth remembering for any future curl-based phone/OTP testing.
- **New watchlist item:** replaying the OTP (`send_otp` called again, whether by her tapping the
  speaker icon or an `initState` re-run) overwrites the previously-issued code server-side. Not
  a bug in front of her — the app re-speaks the new code immediately — but worth a deliberate
  look before demo day.
- **Not addressed this session:** `report_issue()` has no mobile screen yet (backend endpoint
  only); per-set vs per-piece pricing ambiguity for batch listings is still open (see watchlist).

**Commit:** pending

---

## 2026-09-06 — Day 4 fully closed: pricing wired into the app, on screen   [Day 4]
**Done:** the one gap left after Day 4's pipeline work — nothing rendered on a phone — is
closed. Built the bridge from `pipelines.pricing.*` to the Flutter app and verified the whole
chain live on an Android emulator, including a real spoken attribute confirmation (not a stub).

- **`backend/app/api/pricing.py`** (new) — 3 stateless endpoints: `/pricing/attributes` (image +
  audio → transcribe → glossary correct → PII strip → `describe()` for category → vision/voice
  attribute suggestion, all unconfirmed), `/pricing/classify_answer` (one recorded yes/no clip →
  True/False/None, reusing `readback.classify_answer` — the same primitive the Day-2 gate uses),
  `/pricing/quote` (confirmed category/material/size → floor + band + suggested price +
  comparables + SHAP bars). Region is never guessed — passed as `"unknown"` since Day 5's
  onboarding (where her location would actually be captured) doesn't exist yet, letting
  `model.py`'s own out-of-range-honesty widen the band instead of silently assuming a location.
- **`mobile/lib/screens/pricing_screen.dart`** (new), reached from `RecordScreen` right after a
  draft is saved+queued (Day 3's offline guarantee is untouched — pricing needs Gemini + the
  model, both server-side, so it has no offline path and fails gracefully with a plain "not
  available offline" message rather than blocking capture). Real spoken confirmation loop:
  `flutter_tts` speaks the question (phrasing copied verbatim from `attributes.py`'s own
  `_PHRASE` dict so the same words are used server- or client-side), `record` captures her
  answer, `/pricing/classify_answer` classifies it — a "no"/unclear clears the field rather than
  re-guessing. Result screen shows comparables **before** the price band (the roadmap's exact
  ordering requirement), the band with a plain-English low-confidence explanation when
  applicable, the reconciled suggested price, the floor with rate date+source, and the SHAP
  three bars as horizontal bars.
- **Bug found and fixed while wiring this up:** a real Hindi recording ("ये एक पीटल का बर्तन है")
  had whisper mishear पीतल (brass) as पीटल — one character off, below the glossary's 0.82 fuzzy-
  match threshold (measured: 0.75), so `material` came back empty despite a clear brass mention.
  Added `पीटल` as a variant to `craft_glossary.csv`'s existing `पीतल` row — the exact "add a row
  when a real recording surfaces a new mishear" pattern already established in Day 2.
- **Infra fix:** `pricing.py` imports the top-level `pipelines` package (a sibling of `backend/`),
  which crashed `cd backend && uvicorn app.main:app` with `ModuleNotFoundError` the first time —
  fixed at the source in `main.py` (adds the repo root to `sys.path` before the router imports)
  rather than telling everyone to remember a `PYTHONPATH` prefix.

**How to run / verify:**
```
cd backend && uvicorn app.main:app --reload      # works unmodified now
cd mobile && flutter run                          # capture -> record -> Price Estimate screen
```
Or hit the endpoints directly:
```
curl -X POST http://localhost:8000/api/pricing/quote -H "Content-Type: application/json" \
  -d '{"category":"clay pottery","material":"clay","size_class":"medium","region":"unknown"}'
```
`flutter analyze` clean (only pre-existing cosmetic infos); 119 Python tests pass repo-wide.

**Notes / gotchas:** testing this live surfaced how slow the full round trip actually is —
roughly 30-40s from stopping the recording to the confirm question appearing (whisper model
load + CPU inference + Gemini `describe()` + a full-resolution image upload over the emulator's
virtual network). `PricingScreen` shows a loading spinner throughout, but this is worth
profiling before the demo — a real artisan won't wait 40 seconds without feedback that something
is happening. The Android emulator has no real microphone, so every confirm answer recorded
during this session's testing was effectively silence, correctly classified as unclear and
handled by clearing the field rather than crashing — real device testing with an actual spoken
answer is still the more meaningful test of the classify step's accuracy.
**Commit:** pending

## 2026-09-06 — Day 3 gate closed: real device sync verified, live-refresh bug fixed   [Day 3]
**Done:** closed the one item that's kept Day 3 at `[!]` since 5 Sep — the actual
capture→record→queue→sync round trip, run for real against a live backend, not just the
individual screens.

- **Setup:** killed an unrelated orphaned `uvicorn` process from a trashed project that had
  claimed port 8000, started the real backend (`uvicorn app.main:app`), booted the Pixel 8
  emulator (this time cleanly — 5 Sep's crash during audio-recorder init didn't recur; looks
  like it was a transient resource issue that day, not a hard host limitation as feared).
- **Online path:** captured a photo, recorded ~3s of audio, confirmed the draft saved locally,
  queued, and synced — backend logged `POST /api/sync 200 OK` and wrote both files to
  `data/uploads/`.
- **Offline path:** disabled wifi + mobile data on the emulator (`adb shell svc wifi/data
  disable`, confirmed via `ping` returning "Network is unreachable"), captured a second draft —
  correctly held as "Pending Sync" with zero network attempts. Re-enabled connectivity;
  `SyncQueueService`'s `Connectivity().onConnectivityChanged` listener fired on its own and
  synced it with no manual action.
- **Verified at the source of truth:** pulled `kaarigar.db` off the device (`adb exec-out
  run-as ... cat ... > local.db` — must be `exec-out`, not `adb shell`, or the binary gets
  corrupted by CRLF translation) — all 3 drafts show `isSynced=1`, `sync_queue` is empty.
  Backend `data/uploads/` has exactly 3 distinct client_ids, no duplicates.
- **Bug found and fixed:** partway through, the backend confirmed a successful sync
  (`isSynced=1` in the DB) but `HomeScreen` still showed "Pending Sync" — `enqueue()` calls
  `processQueue()` without awaiting it (deliberately, so capture isn't blocked on a slow
  connection), so nothing told an already-rendered `HomeScreen` that a background sync had
  finished. Added `SyncQueueService.queueVersion` (`ValueNotifier<int>`, incremented on every
  sync success or queue-cap eviction); `HomeScreen` now listens to it in `initState` and removes
  the listener in `dispose`. Re-verified: a brand-new draft flipped to "Synced" live, no
  navigation away and back required.

**How to run / verify:**
```
cd backend && uvicorn app.main:app --reload
cd mobile && flutter run   # capture + record; toggle emulator network to test offline
```
Or inspect the on-device DB directly: `adb exec-out run-as com.example.kaarigar cat
/data/data/com.example.kaarigar/databases/kaarigar.db > local.db && sqlite3 local.db "SELECT id,
isSynced FROM drafts;"`

**Notes / gotchas:** the 5 Sep crash during audio-recorder init did not reproduce this session
on the same emulator image — treat that as inconclusive rather than "fixed," since the cause was
never identified. If it recurs, capture the emulator's own logs (`adb logcat`) at the moment of
the crash, not just the Flutter-side log. **Day 3's gate is now fully closed** — tracker.md
updated from `[!]` to `[x]`.
**Commit:** pending

## 2026-09-06 — Category-aware floor weights + a reconciled suggested price   [Day 4 follow-up]
**Problem:** the 100-scenario stress test (with size_score, previous entry) surfaced that 34 of
100 rows had the model's own market-comparable point estimate sitting BELOW its derived floor —
worst case a large `wooden toy` in `sandalwood`: the model priced it at ~₹1,138 (a plausible toy
price), but the floor came out at ~₹27,700, because `size_estimates.csv`'s `bulk` density class
assumes a "large" item can weigh up to 3kg — reasonable for a saree, absurd for a toy. Two
independently-built systems (comparable-price model vs. derived-cost floor) disagreeing by 21x
and just showing both numbers isn't a fix.

**Fix, two parts:**
- **`data/reference/category_weight_overrides.csv`** (new) — per-(category, size_class)
  weight_kg/hours for all 15 reference categories, reasoned from what each object actually
  weighs (a diya is ~50g, not 300g; a saree is ~0.3-0.9kg of fabric, not up to 3kg of raw silk
  yarn; a wooden toy is ~50-400g, not up to 3kg of timber). `floor.py`'s
  `derive_material_cost`/`derive_labour_cost`/`fair_price_floor` all gained an optional
  `category` param — a category with an override uses its own three anchor points for
  size_score interpolation instead of the generic density_class table; an unlisted category
  still falls back to the generic table (out-of-range honesty, not a hard failure). The
  sandalwood wooden toy dropped from ~₹27,700 to ~₹4,000 — still genuinely pricier than a plain
  wood toy (sandalwood really is ~₹10,000/kg), but no longer absurd. Floor-overrides-model
  dropped from 34/100 to 25/100 stress-test rows.
- **`pipelines/pricing/recommend.py`** (new) — rather than chase the remaining, smaller
  disagreements (mostly silver jewellery and silk sarees) by hand-tuning 58 synthetic reference
  prices to match a cost model they were never built from, `suggest_price(pricing, floor)`
  reconciles at query time: the model's point estimate, UNLESS it's below the floor, in which
  case the floor wins. Never blocks, same spirit as `check_against_floor` — it just decides
  which of two honestly-computed numbers to lead with. Wired into `day4_smoke.py`.

**How to run / verify:**
```
python -m pipelines.pricing.floor sandalwood large 0.6 "wooden toy"   # Rs.4,037, was Rs.27,700
python -m pipelines.pricing.recommend "wooden toy" sandalwood large east 1 0.556
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest pipelines/pricing/ -q   # 57 passed
python -m scripts.day4_smoke                                              # now prints a SUGGESTED PRICE line
```
119 tests pass repo-wide.

**Notes / gotchas:** `category_weight_overrides.csv` numbers are still reasoned estimates, not
measurements — same caveat as `size_estimates.csv`, just at finer granularity. The remaining
25/100 stress-test rows where the floor still wins are mostly precious-metal/silk items, where
the (live-verified) material rate is high enough that even a realistic weight estimate can
exceed the synthetic reference set's hand-authored "market" prices — `recommend.py` is the
right place to absorb that, not another round of hand-tuning 58 rows to chase a moving target.
**Commit:** pending

## 2026-09-06 — Continuous size_score alongside the spoken size bucket   [Day 4 follow-up]
**Done:** small/medium/large was flagged as too coarse — two items that both confirm as
"medium" by voice can differ 3x in actual frame coverage (16% vs 44%) and were priced/costed
identically. Added `size_score` (the raw 0-1 vision-coverage fraction behind `size_class`)
riding alongside the spoken bucket, without changing the voice interaction at all — a low-
literacy artisan still only ever confirms "small/medium/large" aloud; the continuous number is
just no longer thrown away afterward.

- **`attributes.py`**: `AttributeResult.size_score` (float | None), computed by vision alongside
  `size_class`, cleared to `None` alongside `size_class` if she rejects the size confirmation
  (same distrust — a rejected vision reading isn't reused for anything downstream). New public
  `SIZE_BOUNDS`/`SIZE_REPRESENTATIVE` constants so `floor.py`/`model.py` never duplicate the
  bucket boundaries.
- **`floor.py`**: `derive_material_cost`/`derive_labour_cost`/`fair_price_floor` gained an
  optional `size_score` param. Weight/hours now piecewise-linearly interpolate between the
  small/medium/large anchor points in `size_estimates.csv` instead of a flat per-bucket number.
  `size_score=None` (no vision reading, or a rejected confirmation) falls back to the exact old
  flat behaviour — a strict superset, not a breaking change.
- **`ml/train_pricing.py`/`model.py`/`shap_explain.py`**: `size_score` added as a 6th, numeric
  (non-categorical) feature alongside the 5 existing categorical ones (`ALL_COLS` is now the one
  shared column-order constant across training/inference/SHAP, replacing ad-hoc `FEATURE_COLS`
  reuse). Backfilled `pricing_reference.csv`'s 58 rows with a `size_score` per row — within each
  (category, size) group, rows are ranked by price and spread evenly across that bucket's
  coverage range, so the retrofit is consistent with prices that already varied for unexplained
  reasons, rather than inventing new numbers (documented in the CSV header, including the
  honest caveat that season/region can also move price, so this is a soft proxy).

**How to run / verify:**
```
python -m ml.train_pricing                          # retrain with the new feature
python -m pipelines.pricing.floor clay medium 0.16   # Rs.194 floor (was flat Rs.310 for ANY medium)
python -m pipelines.pricing.floor clay medium 0.44   # Rs.438 floor — same spoken bucket, 2.3x apart
python -m scripts.day4_smoke                         # still passes with size_score threaded through
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest pipelines/pricing/ -q   # 48 passed
```
110 tests pass repo-wide.

**Notes / gotchas:** `size_score` is still a frame-coverage proxy, not a physical measurement —
it inherits every limitation `size_class` already had (no scale reference in the photo). This
change makes the *existing* measurement more useful, it doesn't make the measurement itself more
accurate. The `pricing_reference.csv` backfill is a synthetic retrofit (see the CSV header) —
replace with real per-listing coverage data if it ever exists.
**Commit:** pending

## 2026-09-06 — Fix: silver/metal items were costed at pottery-scale weight   [Day 4 hardening]
**Problem:** asked to live-test the pricing model. `python -m pipelines.pricing.floor silver
medium 500` returned a floor of **₹250,300** — `size_estimates.csv` had one weight-by-size-class
table (small/medium/large → 0.3/1.0/3.0 kg) shared by every material, so a "medium" silver
pendant was costed as if it weighed a full kilogram of silver. A medium silver
necklace/jewellery piece actually weighs tens of grams.

**Fix:** `material_rates.csv` gained a `density_class` column (`precious` for silver, `metal`
for brass/copper, `bulk` for everything else). `size_estimates.csv` is now keyed by
`(density_class, size_class)` with three separate weight (and hours) scales — precious is
gram-scale (0.01–0.1kg), metal is in between (0.15–2.0kg), bulk keeps the original kg-scale
weights. `floor.derive_material_cost`/`derive_labour_cost` look up the material's
`density_class` first, then join. `derive_labour_cost` signature changed from `(size_class)` to
`(material, size_class)` since hours now vary by density_class too (silversmithing is slower,
more detailed work per size than shaping clay) — updated its one caller (`fair_price_floor`)
and its tests.

**How to run / verify:**
```
python -m pipelines.pricing.floor silver medium 500     # now Rs.10,480, not Rs.250,300
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest pipelines/pricing/test_floor.py -q   # 13 passed
```
Added 3 regression tests, including `test_precious_metal_weight_is_gram_scale_not_kg_scale`.
101 tests pass repo-wide.

**Notes / gotchas:** the underlying weight/hours numbers are still hand-compiled placeholders
(no scale reference in the photo, no on-site scale) — this fix corrects the *scale* they operate
on (grams vs kilograms), not their precision. If a demo item's material doesn't cleanly fit
precious/metal/bulk, add a row rather than guessing which bucket is closest.
**Commit:** pending

## 2026-09-05 — Dynamic pricing pipeline   [Day 4]
**Done:** The mandated pricing feature's pipeline, built the same way Day 1/2 were — Python
pipelines + smoke test + unit tests, not yet wired into the Flutter app.

- **`pipelines/pricing/attributes.py`** — vision suggests `size_class` (subject bbox coverage
  of frame, bucketed small/medium/large) and `finish` (glossy vs matte, via the gap between the
  subject mask's 99th-percentile brightness and its median — a real specular-highlight proxy,
  cheap, reuses the Day-1 u2netp/GrabCut mask through a new `enhance.subject_mask()` public
  wrapper). Deliberately does **not** suggest a category name from shape alone (decision D16) —
  see below. Material *type* is plain keyword matching of the (glossary-corrected) transcript
  against a materials vocabulary (`MATERIAL_TERMS`) — text matching, not image inference, so
  it's not the banned material classifier (D2). Added `silver`/`wood` (Latin + Devanagari) to
  `craft_glossary.csv` so the vocabulary covers what pricing needs. Up to 2 spoken,
  attribute-only confirmations (material only if voice found one; size always), reusing
  `readback.classify_answer` for the yes/no — a "no" clears the field rather than re-guessing.
  11 unit tests with a stubbed recorder/transcribe (Day-2 test pattern).
- **`pipelines/pricing/floor.py`** — the fair-price floor = derived material cost + labour cost,
  **never asked**. Material cost = material (voice) × rate (`data/reference/material_rates.csv`,
  dated + sourced) × weight_kg (`data/reference/size_estimates.csv`, by size_class — no scale in
  the photo, so this is a documented conservative placeholder). Labour cost = hours (same table)
  × `pricing.floor_wage_per_hour`. `check_against_floor()` only ever returns a warning — nothing
  in the module can block a listing. 10 unit tests, including one that asserts none of the three
  public functions even accept a cost/price argument.
- **`ml/train_pricing.py` + `pipelines/pricing/model.py`** — XGBoost regressor over 5 native
  categorical features (category/material/size/region/season — `enable_categorical=True`, no
  manual one-hot), trained on `log1p(price)` for stability across a ₹20-₹15,000 range, trained
  lazily on first use like the Day-1 u2netp download. Unseen category/material or fewer than
  `pricing.comparables_shown` real same-category comparables → `confidence="low"` and the band
  widens (out-of-range honesty) instead of a confident-looking number the data can't support.
  `find_comparables()` returns the 3 nearest reference rows, widening to the whole set when a
  category has too few. 7 unit tests.
- **`pipelines/pricing/shap_explain.py`** — the "SHAP three bars" (material / demand / region),
  computed via XGBoost's own `Booster.predict(..., pred_contribs=True)` instead of the separate
  `shap` package — see decision **D16**: `shap` took ~20s just to `import` on this machine (same
  class of import-time tax as rembg/transformers/the Gemini SDK), and XGBoost's native
  contribution output is the *exact* Shapley decomposition for a tree ensemble, not an
  approximation, so nothing is lost. Removed `shap` from `backend/requirements.txt`.
- **`pipelines/pricing/seasonal.py`** — a small, deterministic lookup (Diwali → pottery/brass/
  dhokra, wedding season → sarees/dupattas/jewellery/shawls), always clamped to
  `pricing.seasonal_multiplier_cap` (default ±25%) so a wrong match can't distort the band.
- **Reference data assembled** (`data/reference/`): `material_rates.csv` (silver and copper
  live-fetched and verified reachable — `goodreturns.in`, `tradingeconomics.com` via `xe.com`
  FX; the rest are hand-compiled typical-range figures, clearly flagged, since a
  `moneycontrol.com` fetch was blocked and a cotton-futures fetch returned a stale cached page);
  `size_estimates.csv` (weight_kg + hours by size_class, documented as a rough placeholder);
  `pricing_reference.csv` (58 rows / 15 categories, 100% synthesised within researched-plausible
  Indian handicraft price ranges — see `data_sources.md` for the full disclosure). All three are
  new files this session.
- **`scripts/day4_smoke.py`** — round-trips a synthetic photo + a fixed Hindi transcript through
  the whole chain and asserts the actual gate: an underpriced suggestion is flagged, no
  confirmation question ever mentions price/cost, and swapping in a blank photo with the same
  transcript leaves the extracted material unchanged (proves material comes from voice, not
  pixels). 36 pricing unit tests + this smoke test all pass; 98 tests pass repo-wide.

**How to run / verify:**
```
source .venv/bin/activate
python -m scripts.day4_smoke                                              # prints "Day 4 gate: PASS"
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest pipelines/pricing/ -q   # 36 passed
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest pipelines/ -q          # 98 passed, repo-wide
python -m pipelines.pricing.model "clay pottery" clay medium north 10
python -m pipelines.pricing.floor clay medium 150
```

**Notes / gotchas:** this is the pricing **pipeline** only — nothing in `mobile/` shows a price
band, a floor warning, or comparables yet, so the roadmap gate's "on screen" language is met at
the data level (every result carries what a screen would need) but not yet as an actual user
experience. See `tracker.md`'s `[!]` on the Day-4 gate and the new watchlist entries. The
pricing reference set is small (58 rows) and 100% synthesised — treat the price band as
directionally reasonable for a demo, not as ground truth; augment with real observed listings
before relying on it further. `derive_material_cost`/`derive_labour_cost` read
`size_estimates.csv` by `size_class` only (no absolute weight) because there's no scale
reference in the photo — this is D13's "size/weight (photo + voice)" satisfied about as
honestly as a single phone photo allows.
**Commit:** pending

## 2026-09-05 — Day 3 hardening: verification found the gate wasn't actually green   [Day 3]
**Done:** Asked to verify Day 3 before building further UI. It hadn't been: `flutter analyze`
and `flutter test` both failed outright, and two of the four checked-off tracker items were not
actually implemented. Fixed all of it.

- **`mobile/test/widget_test.dart` was unmodified `flutter create` boilerplate** — it built a
  `MyApp` widget that has never existed in this app (the app class is `KaarigarApp`), so the
  test failed to even compile. This means `flutter analyze`/`flutter test` were red the entire
  time Day 3 was marked "GATE PASSED". Rewrote it to pump `KaarigarApp` and assert the real home
  screen renders. `HomeScreen.initState` reads the local db immediately, and `sqflite` has no
  platform channel in the plain test VM, so also added `sqflite_common_ffi` as a dev dependency
  and point `databaseFactory` at it in `setUpAll` — this is now the pattern for any future
  widget test that touches `LocalDb`.
- **`sync_queue.dart` had a bare `// TODO: implement downscale`** and no queue-size cap, despite
  `tracker.md` checking off "SQLite + outbound queue (client ids, downscale, oldest-first,
  cap)" as done. Implemented both: `_downscaleForUpload()` resizes to 1600px on the longest side
  (via the already-declared `image` package) and caches the result as a `.upload.jpg` sibling so
  a retry doesn't redo the work — the original file is never touched, only the upload copy is
  smaller. `_enforceQueueCap()` caps pending drafts at 50 (`maxQueueSize`), evicting the oldest
  queue entry, its draft row, and its image/audio files once exceeded, so an artisan offline for
  days can't grow local storage unbounded.
- **No iOS platform had ever been generated** — `mobile/ios/` didn't exist, only `android/`.
  Ran `flutter create --platforms=ios .` and added the missing `NSCameraUsageDescription` /
  `NSMicrophoneUsageDescription` to `Info.plist` (without these, iOS kills the app on first
  camera/mic access instead of prompting — this would have surfaced the first time anyone tried
  an iOS build).
- **`capture_screen.dart` had an escaped-`$` bug** (`'\$e'` inside single quotes, twice) that
  printed the literal text `$e` instead of the actual exception on a camera-init or capture
  failure — silently useless error logs. Fixed to real string interpolation + `debugPrint`.
- **`api_client.dart` hardcoded `10.0.2.2`** (the Android-emulator-only loopback alias) as the
  backend host, which cannot work from iOS Simulator, a real device, or the desktop target.
  Now branches on `defaultTargetPlatform` (`10.0.2.2` on Android, `localhost` elsewhere).
- Removed the unused `provider` dependency (nothing in the app used it — `path_provider` is the
  one actually in use), added the `path` package explicitly to `pubspec.yaml` (`local_db.dart`
  was importing it on the strength of sqflite's transitive dependency only).

**How to run / verify:**
```
cd mobile
flutter analyze     # clean except cosmetic withOpacity/use_super_parameters info lints
flutter test        # 1 passed
```
Visual check (Android emulator, since this dev Mac has Xcode CLI tools only, not full Xcode):
booted a Pixel 8 emulator, ran `flutter run -d emulator-5554`, and drove it via `adb`/screenshots.
Confirmed correct: home screen empty state, camera+mic permission prompts, **live camera
preview** on the capture screen, capture→record navigation, and the record screen's blurred
background + mic button. The emulator crashed initialising the audio recorder (AAC encoder) the
moment recording was started, before a save-and-enqueue could be observed — see watchlist, this
is host environment instability (Android emulator support is flagged unsupported on this
machine), not an app bug found in review.

**Notes / gotchas:** the record→enqueue→sync round trip (the actual Day-3 gate criterion) is
still not independently confirmed end to end on a device — do that on a real phone or a stable
emulator before relying on it. `docs/tracker.md`'s Day-3 gate line is marked `[!]` (caveat)
rather than reverted to `[ ]`, since everything checkable without a working recorder path now
checks out.
**Commit:** pending

## 2026-09-05 — Flutter shell + offline queue   [Day 3]
**Done:** The foundation for the offline-first mobile app and the backend sync handler.

- **`mobile/lib/services/local_db.dart`**: Implemented SQLite setup using `sqflite`. Created `drafts` table for autosaved listings and `sync_queue` table for ordered background tasks.
- **`mobile/lib/services/sync_queue.dart`**: Created the `SyncQueueService` which listens to connectivity changes (via `connectivity_plus`) and processes the queue oldest-first when online.
- **`mobile/lib/services/api_client.dart`**: HTTP client to upload the captured image and audio bundle using `multipart/form-data`.
- **`mobile/lib/screens/*`**: Built a premium, polished UI. `home_screen.dart` is the dashboard showing drafts and sync status. `capture_screen.dart` utilizes the `camera` package for full-screen capture. `record_screen.dart` utilizes the `record` package for voice notes with a pulsing UI.
- **`backend/app/api/sync.py`**: A new FastAPI endpoint `/sync` that accepts the draft bundle. Implemented server-side deduplication using an in-memory set (rejects duplicate `client_id`s, returning a success status instantly).

**How to run / verify:**
```
# Terminal 1: Run the backend
cd backend
uvicorn app.main:app --reload

# Terminal 2: Run the app (requires emulator)
cd mobile
flutter run
```
Turn off the emulator's network, capture a craft and record audio, verify the draft is saved. Re-enable network, verify it automatically syncs to the backend and deduplicates if re-sent.

**Notes / gotchas:** The backend deduplication is currently in-memory (`synced_client_ids = set()`). This will need to be wired up to a proper database when the backend DB schema is locked in Day 4/5. 
**Commit:** pending

## 2026-09-01 — Voice → listing, step 5: spoken read-back confirmation   [Day 2]
**Done:** `pipelines/voice/readback.py` — the Day-2 exit gate. Nothing publishes until she has
heard it and said yes.

- **`build_script(transcript, lang, corrections, redactions, category, materials, title)`**
  composes the spoken text **in her language**, in this order: *"I heard: «her cleaned
  transcript»"* → every glossary correction (*"I corrected बर्दन to बर्तन"*) → every PII
  redaction (*"I removed a phone number"*) → the facts we actually extracted (category,
  material, price) → *"Is this correct? Say yes or no."* Only the wrapper phrases are
  templated per language (hi/bn/ta/mr/en); the content is her own words, which are already
  in her language. The generated Hindi title is read too, but only when she spoke Hindi.
- **`classify_answer(text, lang)`** → `True` / `False` / `None`. Per-language yes/no vocab in
  Devanagari, Bengali, Tamil and romanised forms, matched with `difflib` because a one-word
  answer transcribes noisily. Anything that is neither is `None` — never guessed.
- **`readback_and_confirm(...)`** speaks the read-back, takes her answer through an **injected**
  `recorder` (no mic code here — D14), and re-asks in her language on an unclear answer up to
  `readback.max_confirm_attempts` (2).
- **`ReadbackResult.may_publish` is True only on an explicit spoken yes (D15).** Silence, an
  unclear answer, a walked-away artisan, an exhausted retry budget, and a TTS failure all
  leave it False. Publish must gate on this property, never on `confirmed is not False`.

**Why we read back the transcript, not the listing copy (D15):** Gemini produces EN + HI only,
so a Tamil or Bengali speaker has no listing text in her own language to check — but her
*transcript* always is. She is confirming "did you understand me", not proofreading marketing
copy. Announcing our own edits aloud is the part that matters most: silently "fixing" her words
is exactly the failure a low-literacy user cannot catch.

**How to run / verify:**
```
source .venv/bin/activate
python -m pipelines.voice.readback "ये एक मिट्टी की मटकी है, कीमत चार सौ रुपये" hi
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest pipelines/voice/ -q     # 57 passed
python -m scripts.day2_smoke                                              # step-5 line: OK
```
Verified: script reads `मैंने यह सुना: ये एक मिट्टी की मटकी है… क्या यह सही है? हाँ या नहीं बोलिए।`,
audio written to `results/readback/readback_hi.aiff`, `may_publish=False` with no spoken answer.

**Notes / gotchas:** `tts.py` only maps a real macOS voice for Hindi (`Lekha`) — bn/ta/mr fall
back to an English voice and will *sound* wrong on the dev Mac even though the text is correct.
On device `flutter_tts` handles them; this is a dev-machine artefact, not a pipeline bug
(watchlist, ties to O3). Day 3 must supply the real `recorder` callable from Flutter before the
gate can be signed off on a device.
**Commit:** pending

## 2026-09-01 — Voice → listing, step 4: glossary · PII strip · re-record loop   [Day 2]
**Done:** the three guardrails that stand between a raw transcript and a published listing.

**`pipelines/voice/glossary.py`** — `correct(text, min_ratio=0.82)` → `GlossaryResult(text,
corrections[])`. Snaps misheard craft/material words to canonical spellings. Data:
`data/reference/craft_glossary.csv` (`canonical,variants`, pipe-separated; ~55 rows covering
techniques — ikat/bandhani/dhokra/kalamkari/ajrakh… — materials, and craft objects, in Latin
**and** Devanagari as separate rows so a correction never switches script). Per token: exact
variant hit → canonical, else `difflib.get_close_matches` above the ratio. stdlib only, no
fuzzy-match dependency (D14).
- **Bug found + fixed in verification:** Python's `\w` excludes Devanagari matras and the virama
  (they are `Mn` marks), so the first tokeniser shredded `मिट्टी` into `म` + `िट` + … and
  `str.isalnum()` returned False for any token containing a virama. Token class now spells out
  `\u0900-\u097F` and the "is this a word" guard is a regex, not `isalnum()`.
- Verified on the real recording: `बर्दन` → `बर्तन`, `मिटटी` → `मिट्टी`, `मटकि` → `मटकी`,
  `साडी` → `साड़ी`; `dokra`→`dhokra`, `bandani`→`bandhani`, `dupata`→`dupatta`.

**`pipelines/voice/pii_strip.py`** — `strip_pii(text, min_digits=7, placeholder="[removed]")`
→ `PIIResult(text, redactions[], changed)`. Removes `+91`/`0091` numbers with any spacing, and
any digit run ≥ 7 counted across spaces/dashes (covers 10-digit mobile, 12-digit Aadhaar), in
Latin **and** Devanagari digits. **Keeps** prices, dimensions, counts and years — pricing and
stock depend on those surviving. Returns what was removed so the read-back can say so out loud
rather than silently altering her words.

**`pipelines/voice/capture.py`** — `capture(audio, lang, recorder, max_retries)` →
`CaptureResult(transcript, attempts, still_low, prompt_audio, audio_used, history)`. Acts on
`needs_rerecord`: synthesises a per-language "आवाज़ साफ़ नहीं आई, दोबारा बोलिए" prompt with the
Day-1 TTS, then calls an **injected** `recorder(prompt_audio, attempt)` callable for the new
audio. **No microphone code lives here** (D14) — the same loop runs from Flutter, a CLI, and the
tests. Keeps the **best** take, not the last, because a retry can come out worse. Retry budget:
`models.transcribe.max_rerecords` (2).

**Pipeline order is now:** transcribe → glossary → PII strip → describe. `scripts/day2_smoke.py`
runs it in that order and prints `[gloss]` / `[pii]` lines.

**How to run / verify:**
```
source .venv/bin/activate
python -m pipelines.voice.glossary "ye ek dokra murti aur ek bandani dupata"
python -m pipelines.voice.glossary "ये एक क्ले का बर्दन है, मिटटी की मटकि"
python -m pipelines.voice.pii_strip "400 rupaye ki hai, call karo +91 98765 43210 par"
python -m pipelines.voice.capture clay-bartan.m4a hi
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest pipelines/voice/ -q     # 40 passed
```

**Notes / gotchas:** the glossary is the cheapest quality win in the whole voice pipeline — the
words whisper mangles are exactly the words buyers search for. Add a row whenever a real
recording surfaces a new mishear. `glossary.terms()` also exposes the canonical list, which is
the obvious future `initial_prompt` bias for whisper.
**Commit:** pending

## 2026-09-01 — Voice → listing, step 3: Gemini bilingual description   [Day 2]
**Done:** `pipelines/voice/describe.py` — `describe(transcript, lang="hi", attributes=None)`
→ `ListingDraft` (`title_en/hi`, `description_en/hi`, `bullets_en/hi`, `seo_keywords`,
`category`, `materials`, `source`, `error`). Turns a transcript (+ any confirmed attributes)
into a bilingual marketplace listing. Gemini also does the translation here (D11).

- **Gemini backend = plain REST** via `requests` (D12): `POST v1beta/models/{model}:generateContent`,
  `x-goog-api-key` header, `responseMimeType: application/json`. **No `google-generativeai` SDK** —
  it's deprecated and imports in ~156 s here (grpc/proto sys.path scan). The 24-package SDK tree
  was installed then removed with `rm -rf` (it also re-broke pytest, like transformers had).
  Model id is config-driven (`models.describe` → `_MODEL` map); default `gemini-3.6-flash`.
- **Prompt** pins the voice note as source of truth: never invent materials/dimensions/prices;
  short; EN + natural Hindi; 6–10 SEO terms; one-phrase category. Strict-JSON parse with a
  fence-strip + first-`{…}` fallback.
- **Disk cache** `data/processed/listing_cache/<sha1>.json` keyed by transcript+attributes —
  checked before any call, written on every success. This *is* the Day-7 pre-cache path
  (run once online → replays offline). API never called in a loop. Dir is gitignored.
- **Offline template fallback** — no key / 429 / offline / non-JSON → builds a serviceable
  bilingual listing from attributes + the transcript (Hindi side keeps the maker's own words
  rather than risk a bad offline translation). `.error` explains. Never blocks.
- `pipelines/common.py`: added `load_env()` / `env_get()` (loads repo `.env`; `python-dotenv`
  with a minimal hand-parser fallback). `.env.example` added.

**How to run / verify:**
```
source .venv/bin/activate
python -m pipelines.voice.describe "ये एक क्ले का बर्दन है" hi     # source=gemini (or template)
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest pipelines/voice/ -q   # 16 passed
python -m scripts.day2_smoke                                       # step-3 line: OK
```

**Verified 1 Sep:** `python -m pipelines.voice.describe "ये एक क्ले का बर्दन है, हाथ से बनी, कीमत चार सौ रुपये" hi`
→ `source=gemini`, model `gemini-3.6-flash`. Correct EN + HI listing, corrected the transcript
typo (बर्दन→बर्तन), pulled "400 rupees", used the passed attributes.

**Gemini key gotcha:** the free tier only works on a Google Cloud project with **no billing
account**. A key made in a billing-enabled project (e.g. one already used for Maps free-trial
credit) returns 429 "prepayment credits are depleted" once the trial credit is gone. Fix: make
the Gemini key in a *new* AI Studio project. Model names churn fast (`1.5`→404, `2.5`→"not for
new users", `3.6-flash` current) → `models.describe` in config is the one place to change it.
**Commit:** pending

## 2026-09-01 — Voice recognition fix: whisper-small, VAD off   [Day 2 hardening]
**Problem:** on-device transcription was garbled on a real Hindi voice note
("ye ek clay ka bartan hai"): `tiny` gave "Kali ka bardin hai" at confidence 0.25.

**Diagnosis:** `scripts/stt_probe.py` (new) — prints audio metadata then sweeps model
sizes × decode settings on one file. Results on the 6.5s note:

| trial | det-lang | conf | text |
|---|---|---|---|
| tiny  / vad+beam5      | hi/1.00 | 0.247 | `1. Kali ka bardin hai` |
| base  / vad+beam5      | hi/1.00 | 0.294 | `अे गे का बर्दन है` |
| base  / NO-vad         | hi/1.00 | 0.176 | `ں 1 CLAY Ka Barthin Hai` |
| small / vad+beam5      | hi/1.00 | 0.701 | `ये एक ख्ले का बर्दन है` |
| small / NO-vad + noprev| hi/1.00 | 0.642 | `ये एक क्ले का बर्दन है` |

`tiny` and `base` are simply too small for Hindi. `small` recovers the sentence
("ये एक क्ले का बर्तन है", minor त/द and English-loanword slips) at conf **0.70** —
comfortably above the 0.55 gate. The confidence heuristic was never the problem.

**Fixes (approved):**
- `config/config.yaml`: `models.transcribe.on_device` `whisper-tiny-q` → **`whisper-small`**
  (~465 MB first-run download; server path was already `whisper-small`).
- `pipelines/voice/transcribe.py` `_transcribe_fw`: `vad_filter=False` (Silero VAD clipped
  speech on short notes and added a one-time model download) + `condition_on_previous_text=False`
  (cleaner on single-utterance notes).

**Verify:** `python -m scripts.stt_probe <real_note.m4a> hi` — `small` rows correct, conf > 0.6.
`python -m pipelines.voice.transcribe <real_note.m4a> hi` — non-garbled Devanagari,
`needs_rerecord=False`. Steady-state ~2.6s for a 6.5s note on the Air.

**Notes / gotchas:** minor residual errors (बर्तन→बर्दन, code-switched English words) are
acceptable — Gemini reads them fine. Optional later: `initial_prompt` seeded with craft vocab.
Re-test bn/ta/mr before Day 7. `day2_smoke` still uses synthetic `say` audio so its conf stays
low there — that's the test input, not the pipeline.
**Commit:** pending

## 2026-09-01 — Voice → listing, step 2: translation = passthrough (Gemini does MT)   [Day 2]
**Done:** `pipelines/voice/translate.py` — `translate(text, source_lang)` → `TranslationResult`
(`text`, `source_text`, `source_lang`, `translated` bool, `backend`, `model`, `error`). Contract
kept so downstream code is stable, but there is **no standalone MT model**: `translate()` is a
passthrough that returns the source text unchanged (`translated=False`) and normalises/carries
`source_lang` so the Gemini step (step 3) knows what it's being handed. Gemini translates:
regional transcript → EN + HI in one call.

**Why the change (same day):** the first cut used IndicTrans2-200M via HF `transformers`.
`import transformers` hung for **~20 min** on this machine — it calls
`importlib.metadata.packages_distributions()` which enumerates every distribution on `sys.path`,
and the venv is built on the anaconda Python so that tree is enormous. `torch` (2.13.0, imported
fine at ~2 s) is a ~200 MB dep nothing else in the project uses. Removed all three
(`torch transformers IndicTransToolkit`) — see watchlist "conda base poisons package enumeration"
and decision D11 (revised).

An optional real path survives behind `KAARIGAR_MT=indictrans2` (lazy imports, untouched
otherwise) for later use on a clean non-conda machine. Not for the demo.

**How to run / verify:**
```
source .venv/bin/activate
python -m scripts.day2_smoke        # [mt] line now shows backend=passthrough, instant
pytest pipelines/voice/test_translate.py -q
python -m pipelines.voice.translate "यह हाथ से बनी नीली मिट्टी की मटकी है" hi
```
No model downloads. Tests are pure-Python, instant.

**Notes / gotchas:** `backend/requirements.txt` no longer lists torch/transformers/IndicTrans2.
`rm -rf .venv/lib/python3.12/site-packages/{torch*,transformers*,IndicTransToolkit*}` was used to
remove them (pip uninstall also hangs on the same sys.path scan). **Always `conda deactivate`
before working in this venv.**
**Commit:** pending

## 2026-09-01 — Voice → listing, step 1: transcription   [Day 2]
**Done:** `pipelines/voice/transcribe.py` — `transcribe(audio_path, lang=None, prefer_server=True)`
returns a `TranscriptResult` (text, detected language + prob, 0–1 `confidence`, `needs_rerecord`,
per-segment list, backend/model, `error`). Two backends, one return type:
- **server (default when online):** whisper.cpp `./server` at `KAARIGAR_WHISPER_SERVER=http://host:port`
  (`/inference`, `verbose_json`). Tried first when the env var is set.
- **on-device fallback:** `faster-whisper` (CTranslate2), `device=cpu compute_type=int8`, model
  `small` when the server path was intended else `tiny` (config `models.transcribe.*`). Any server
  failure silently falls back here and records a note in `.error`.
Both whisper imports are **lazy** (module import does nothing heavy — same rule as onnxruntime/rembg).
Confidence = duration-weighted mean of `exp(avg_logprob)` per segment, discounted by `no_speech_prob`;
below `models.transcribe.min_confidence` (0.55) → `needs_rerecord=True` (caller asks for a re-record).
Model cache: `~/.cache/kaarigar/whisper/`.

**How to run / verify:**
```
source .venv/bin/activate
pip install --disable-pip-version-check faster-whisper   # keyring already disabled globally
python -m scripts.day2_smoke        # TTS a known Hindi line -> transcribe it back -> PASS
pytest pipelines/voice/test_transcribe.py -q
```
`day2_smoke` needs no server and no recording: it synthesises a sentence via the Day-1 TTS and
round-trips it. First run downloads the `tiny` model (~75 MB) once.

**Notes / gotchas:** faster-whisper pulls `av` (PyAV) for decoding — handles the `.aiff` that macOS
`say` produces, no ffmpeg needed. whisper.cpp server is optional and not bundled; without the env var
the on-device path is always used. Translation/description/glossary/PII/read-back still TODO.

**Smoke result (1 Sep, on the Air):** `day2_smoke` passed step-1 gate. `tiny` model auto-downloaded,
`say`-synthesised Hindi line decoded via faster-whisper. Transcription **quality was poor**
(`"Yehav Sabani Nili midi keem atki hi..."` for `"Yeh haath se bani neeli mitti ki matki hai..."`) —
`tiny` + robotic TTS is the worst case. The **confidence gate worked**: 0.355 < 0.55 →
`needs_rerecord=True`. Real human audio + `tiny` does better; gate still needs a human voice note
per language before Day 7. Tests: `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest pipelines/voice/ -q`
→ 10 passed (the env var is required — see watchlist, conda/pytest).
**Commit:** pending

## 2026-09-01 — Perf fix: drop rembg, run u2netp via onnxruntime   [Day 1 hardening]
**Problem:** on the target MacBook Air (arm64, native — not Rosetta), the pipeline crawled/hung:
`import cv2` took **25 s** (OpenCV **5.0.0** beta had a bad arm64 build), and `import rembg`
stalled for minutes JIT-compiling **pymatting → numba** at import. Separately, `pip install`
froze indefinitely at 0% CPU — pip hanging on the **macOS Keychain (keyring)** lookup.

**Fixes:**
- **Background removal now runs u2netp directly through onnxruntime** (`pipelines/image/enhance.py`),
  no rembg wrapper — onnxruntime imports in ~0.1 s and u2netp is ~4.7 MB (auto-downloaded to
  `~/.cache/kaarigar/u2netp.onnx`). GrabCut stays as the offline fallback; `KAARIGAR_NO_REMBG=1`
  forces it. Mask is computed at ≤720px then upscaled (speed). `rembg_available()` →
  `bg_model_available()`.
- **Pinned OpenCV to `opencv-python-headless==4.10.0.84`** (imports in ~1 s vs 25 s).
- **Disabled pip's keyring globally:** `pip config set global.keyring-provider disabled` — this was
  the real cause of the multi-minute `pip install` freezes; it will bite every future install.

**Verify:** `python -m scripts.day1_smoke` (fast, `u2netp available: True`, `Day 1 gate: PASS`);
`python -m scripts.try_photo saree.jpeg` → clean cut-out on a real photo.

**Notes:** rembg/pymatting/numba are left installed but never imported (harmless); requirements.txt
updated to drop rembg and pin opencv. See decisions D9.

**Commit:** pending

## 2026-08-30 — Image pipeline + shared TTS   [Day 1]  ✅ gate passed
**Done:**
- `pipelines/image/enhance.py` — full enhancer: rembg U2-Net background removal (GrabCut
  fallback if rembg missing), scene-based white balance (Shades-of-Gray, gains clamped),
  CLAHE lighting, composite onto white, bbox/saliency crop to a 1000px square, texture
  close-up. Returns an `EnhanceResult` (status, coverage, subject_frac, separation, outputs).
- `pipelines/voice/tts.py` — shared offline TTS: `speak_to_file(text, out, lang)`, pyttsx3
  primary with a macOS `say` fallback. Everything downstream (read-back, onboarding, alerts)
  calls this.
- `pipelines/common.py` — config loader (`load_config`, `cfg_get`).
- `scripts/day1_smoke.py` — generates a synthetic bad phone photo, runs enhance + TTS, asserts
  the gate. `pipelines/image/test_enhance.py` — unit tests (ok + retake branches).

**How to run / verify:**
```
source .venv/bin/activate
pip install -r backend/requirements.txt          # first time
python -m scripts.day1_smoke                      # -> results/day1/, prints "Day 1 gate: PASS"
pytest pipelines/image/test_enhance.py -q
```

**Notes / gotchas:**
- **rembg downloads u2net.onnx (~176 MB) to `~/.rembg/` on first use** — first run is slow, then
  cached. On device (Flutter) this is a bundled/again-fetched model; different path, same idea.
- **Two bugs found and fixed in verification** (see decisions D7, D8): (1) the failure-aware
  check first gated on the subject's *internal* contrast, which wrongly rejected flat-coloured
  products (a plain pot/solid sari) — changed to mask sanity (coverage + largest-blob fraction);
  (2) white balance was gray-world *over the subject*, which desaturated strongly single-coloured
  products — changed to scene-based Shades-of-Gray with clamped gains, so a blue pot stays blue.
- Output visual check saved at `results/day1/_compare.png` (raw | enhanced | texture).

**Commit:** pending

## 2026-08-30 — Project scaffolding   [Day 0]
**Done:** Created the full project directory structure (backend/ FastAPI + workers, pipelines/
image·voice·pricing, mobile/ Flutter, ml/, scripts/, data/, config/, assets/). Moved the 9-day
roadmap into `docs/planning/` and the formal deliverables (proposal, deck, architecture,
wireframes, feature-decision note, and their editable sources) into `docs/deliverables/`.
Added the living docs — README, tracker, watchlist, this build log, decisions, data_sources —
plus `config/config.yaml`, `.gitignore`, `backend/requirements.txt`, `mobile/pubspec.yaml`.
Every source file is a stub with a docstring naming the roadmap day it belongs to.

**How to run / verify:** `find . -type f -not -path './.git/*'` shows the tree; no code runs yet.

**Notes / gotchas:** Nothing is implemented — all `.py`/`.dart` files are TODO stubs. Deliverables
were filed under `docs/deliverables/`, and only the roadmap under `docs/planning/`; if you want
everything consolidated under `planning/`, say so. Secrets belong in `.env` (git-ignored).

**Commit:** pending
