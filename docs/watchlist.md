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

- [ ] **faster-whisper first-run download** (`tiny` ~75 MB, `small` ~250 MB) to
      `~/.cache/kaarigar/whisper/`. Pre-fetch for the demo/device path (ties into Day-7 pre-cache).
- [ ] **whisper.cpp server is optional and unbuilt.** Code prefers it via `KAARIGAR_WHISPER_SERVER`
      and falls back to on-device on any failure. If we want the server for the demo, build+test it
      before Day 7, not on the day.
- [!] **Voice recognition quality is currently poor — OPEN, must fix before the gate passes.**
      Smoke test (`tiny` model + robotic `say` voice) decoded Hindi garbled at conf 0.35. The
      confidence gate caught it (`needs_rerecord=True`), so bad text won't reach a listing, but the
      pipeline can't demo like this. Fix path: real-audio eval per language → bump `on_device` to
      `whisper-base`/`small` → or build the whisper.cpp server. Tracked in `logs.md`.
- [ ] **Confidence gate is heuristic** (`exp(avg_logprob)` × `1-no_speech_prob`, threshold 0.55).
      Tune the threshold against real regional-language notes so it re-records genuine mishears
      without nagging on clean audio.
- [ ] **`say`/pyttsx3 TTS is not a real speaker** — `day2_smoke` proves the plumbing, not accent
      robustness. Gate must still be checked with an actual human voice note per language.
- [!] **No standalone MT model (D11).** `translate()` is a passthrough; **Gemini (step 3) must do
      the actual regional→EN+HI translation.** Verify Gemini output quality per language against a
      real note. Offline, the listing text stays in the source language — acceptable degradation,
      but note it in the demo script.
- [ ] **Gemini now carries translation + description** — a single point of failure for the whole
      listing text and subject to free-tier caps. Pre-cache every demo item (Day 7); keep a
      templated fallback listing (attributes → sentence) for a hard API outage.

## Day 3 — offline queue

- [ ] **Queue must survive days offline.** Cap the queue, downscale before queueing, sync
      oldest-first, never drop a listing. Client-generated ids + server dedupe so a double sync
      can't duplicate a listing.
- [ ] **First run needs one brief connection** (OTP) and must *defer, not block* when offline —
      capture allowed unverified, publish blocked.

## Day 4 — pricing

- [ ] **No material classifier.** Material comes from the voice note; the photo only *suggests*
      category/size/finish. If any code tries to infer material from pixels, remove it.
- [ ] **Pricing quality rests on one spoken answer** (her material cost). If it's misheard the
      floor is wrong — confirm it by voice.
- [ ] **The floor is a warning, not a quote.** It must warn on an underpriced listing and then
      *allow the override*. Do not lock her out of her own pricing.
- [ ] **Material rates are a dated snapshot.** Print the rate's date + source on screen; the
      weekly refresh is described, not built (cut list). Verify the reference sources
      (Agmarknet/eNAM/MCX/WPI) are actually reachable before citing them.
- [ ] **Rewards / band sanity** — bands should be plausible ranges, never a false-precision single
      number; wider band + stated low confidence for unseen categories.

## Day 5 — listing page + offers + stock

- [ ] **Permanent URL id scheme is IRREVERSIBLE once a stall QR is printed.** Freeze the
      artisan/listing id format deliberately here; don't change it later in a migration.
- [ ] **Stock decrement must be atomic.** Decrement remaining_count under a row lock *inside* the
      acceptance transaction, or two buyers can both be accepted for the same batch.
- [ ] **Per-piece vs per-set ambiguity** — ask explicitly, or every price is wrong by the size of
      the set.
- [ ] **Two mechanisms pointed opposite ways:** the buyer-side auto-decline is *asking price −
      tolerance*; the fair-price floor is advice to *her*. Keep them separate, or an artisan who
      prices below the floor finds her own listing unbuyable.
- [ ] **Middleman capture** — bind account + stall QR to her own number; earnings visible only in
      her own view.

## Day 6 — storefront

- [ ] **Follower email** — collect email only, weekly batched digest, one-click unsubscribe,
      delete on unsubscribe. This is the only outbound channel to a buyer; keep it minimal (DPDP).
- [ ] **Stall QR points at the STOREFRONT**, not a single listing. Share card keeps a per-listing
      QR + storefront address underneath.

## Day 7–8 — demo

- [ ] **Decide + test the API fallback now, not on the day.** Live Google Maps at demo time, with
      a silent fall-back to the cached matrix if it fails.
- [ ] **Freeze before rehearsal.** No functional change after the Day-8 freeze/tag.
- [ ] **Languages:** four are tested end to end (Hindi/Bengali/Tamil/Marathi). For the live demo,
      lead with one; describe the rest as supported-but-unverified rather than faking them.
