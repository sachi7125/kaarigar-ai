# Watchlist

Things to verify, check, or watch out for — written when noticed, checked when the day
arrives. **Read this at the start of each build day and raise anything due.**

Status: `[ ]` open · `[x]` checked, fine · `[!]` checked, it was a problem.

---

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
- [ ] **Failure-aware enhancement must actually fire.** A pale product on a pale wall should keep
      the original and request a retake, not publish a damaged cut-out.

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
