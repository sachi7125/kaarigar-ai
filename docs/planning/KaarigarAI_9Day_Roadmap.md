# KaarigarAI — 9-Day Build Roadmap

*The AI Virtual Business Manager for Marginalized Artisans · SIH26090 · Team Algorhythm.
Nine days to a working prototype and a rehearsed demo. Docs (proposal, deck, architecture,
wireframes) are already revised — this covers the build.*

## The premise, stated honestly

The three mandated features — image enhancer, multilingual auto-cataloger, dynamic pricing —
are what get scored. Everything after them is the market-linkage half the problem statement
asks for and most submissions forget. Nine days is enough for a **near-full-time sprint**, not
a part-time one. Two ordering rules decide the whole plan:

- **The shared text-to-speech voice is built on Day 1**, because read-back confirmation,
  onboarding, spoken alerts and quality nudges all depend on it.
- **The public listing page is built before the offer inbox, and the storefront after it** —
  a buyer needs somewhere to send an offer from, and the storefront is aggregation over pages
  the listing work already produces.

Scope is locked by decisions already made: **no buyer marketplace** (permanent listing
page + storefront + direct offer instead), **no material classifier** (material *type* comes
from her voice, the photo only suggests category/size/finish), **the material cost is derived,
never asked** (type × dated rate table × photo-estimated size — D13), **dated + sourced
material rates on screen**, **listings carry stock** (unique or batch), and a **per-artisan
storefront** as the year-round channel.

## Non-negotiable gates (do not skip under time pressure)

| Gate | Day | If it fails |
|---|---|---|
| Photo **+** voice note → bilingual listing, **read back aloud**, on a real device | 3 | The low-literacy claim is the whole product. Fix the pipeline before pricing. |
| The floor visibly **refuses an underpriced** suggestion; **no cost question is ever asked**; material type is **never inferred from photo pixels** | 4 | Pricing logic is wrong — stop and fix before building on it. |
| A **batch** listing sells down with **no double-accept**; artisan accepts **by voice** | 5 | The stock/offer transaction is wrong. Don't demo it. |
| Full seven-beat demo runs **twice with no internet** | 7 | Record the video now and stop polishing the live path. |

## The long pole: cloud steps and free-tier caps

Transcription, translation, description and pricing publish are network steps, and the free
tiers (Gemini especially) carry daily caps. **Pre-cache every response for the demo items in
advance**, and keep the on-device speech model as the offline fallback. Never call any API
inside a training or batch loop.

**Emphasis legend:** ▲ what gets scored · ★ differentiator (protect the hours) · ⚠ highest risk · ○ supporting

---

## Day by day

### Day 1 — Image pipeline + the shared voice ▲ ⚠(dependency)
- **AI Image Enhancer** (mandated 1): rembg (U2-Net) background removal, OpenCV white-balance +
  histogram + saliency crop, **failure-aware retake** (keep original on a damaged cut-out),
  texture close-up for textiles. Add blur/shake detection at capture if time.
- **Shared TTS voice** — built here because everything downstream speaks. ⚠ If this slips,
  read-back, onboarding and nudges all slip with it.
- **Exit:** a raw phone photo → clean e-commerce image on a real device; TTS speaks a string aloud.

### Day 2 — Voice → listing ▲
- **Multilingual Auto-Cataloger** (mandated 2): whisper transcription (whisper.cpp server default,
  faster-whisper `small` on-device fallback), Gemini bilingual description — Gemini also does the
  regional→EN+HI translation, no standalone MT model (D11).
- Craft-glossary fuzzy-correct · **PI-strip** (identifier-like digit runs) · low-confidence
  re-record · **spoken read-back confirmation** — nothing published without it.
- **Exit:** a regional-language voice note → bilingual listing, read back aloud, confirmed by voice.

### Day 3 — Flutter shell + offline queue · GATE
- Camera capture, voice record, local SQLite, **outbound queue** (client-generated ids, image
  downscale, oldest-first sync, size cap), draft autosave, queued-state UI.
- Server-side dedupe so a repeated push can't duplicate a listing.
- **Exit gate:** capture + record + queue works **offline** on device and syncs with no duplicate;
  and the Day-2 pipeline runs end to end on a real device.

### Day 4 — Dynamic pricing ▲ · GATE
- **Attributes:** vision proposes category / size class / finish as a *suggestion*; the **material
  type comes from the voice note**; 0–2 spoken confirmations, **attribute-only** ("brass or
  bronze?"), never about price or cost. **No material classifier is trained.**
- **Material cost is derived, never asked (D13):** `type (voice) × ₹/unit (dated, sourced rate
  table) × size / weight (photo + voice)`. The rate table's **date + source printed on screen**.
- XGBoost price **band** · SHAP three bars · **comparables evidence strip** (3 similar listings +
  the **derived** material cost) shown *before* the model number · **fair-price floor** (warn,
  never block) · bounded seasonal multiplier · out-of-range honesty (wider band, stated low confidence).
- **Exit gate:** photo + voice → price band with a plain explanation, **no cost question asked**,
  the floor **visibly refusing** an underpriced suggestion, and the rate's **date + source on screen**.

### Day 5 — Onboarding + listing page + offer/stock ▲ · GATE
- **Voice-first onboarding:** language tiles that speak their own name, numeric keypad, OTP read
  aloud, **deferred verification** (unverified capture allowed, publish blocked).
- **Permanent public listing page.** **Offer inbox:** structured offer (price / quantity / date /
  contact), asking-price **auto-decline**, quantity validated against remaining count,
  **unique-vs-batch stock**, decrement under a row lock inside the acceptance transaction,
  sold-out state + **spoken restock**, expiry. Accept/decline **by voice**. Report-an-issue record.
- **Exit gate:** a buyer opens the listing page, offers for N of a batch, artisan accepts by voice,
  remaining count drops — no double-accept.

### Day 6 — Storefront + market linkage ★ — the half most forget
- **Artisan storefront** (permanent per-artisan URL): maker story on top, every live listing below,
  sold-out marked. **Follow** (email only, weekly batched digest, one-click unsubscribe),
  **returning-buyer flag** spoken with the offer, follower count on the dashboard.
- **Stall QR → storefront.** **Share card** (per-listing QR + storefront address). **Export bundle**
  (GeM / ONDC / Amazon Karigar / ODOP). **Maker story** pipeline (reuses Day-2 voice pipeline).
- ○ Spoken **scheme / mela / seasonal alerts** · **quality meter** + icon-driven **dashboard**
  (listings, offers, monthly earning, remaining stock, followers) · **voice order & status** (intent
  matcher over a few fixed questions).
- **Exit:** stall QR opens the storefront; one tap yields a valid export bundle; dashboard shows real aggregates.

### Day 7 — Edge-case hardening + offline rehearsal + pre-cache ⚠ · GATE
- Harden the register that causes visible failure: noisy audio → re-record · mis-heard craft word →
  glossary correct · PI digits stripped · pale-on-pale → retake · unseen category → wider band ·
  material not in the rate table → wider band + stated low confidence (never a cost prompt) ·
  per-piece vs per-set → ask · two buyers / one batch → locked decrement · no offers for a week →
  reasoned nudge · growing offline queue → cap + downscale + oldest-first · middleman → account &
  QR bound to her own number, earnings only in her view.
- **Offline rehearsal** with the network disabled; **pre-cache** Gemini + TTS responses for every demo item.
- **Exit gate:** the full seven-beat demo runs **twice with no internet**.

### Day 8 — Freeze + seven-beat rehearsal + video
- **Freeze the build. No functional change after this point.** Tag it.
- Rehearse the seven beats: first run → photograph → voice note → price → offline → **the buyer**
  (scan stall QR → storefront → maker story → offer → accept by voice) → **linkage** (export bundle +
  follow; close on a real scheme).
- **Live linkage API for the demo only**, with the **cached fallback tested now, not on the day**.
- Record a **90-second backup video** of the demo working.
- **Exit gate:** seven-beat demo runs end to end, twice, offline; video recorded.

### Day 9 — Final docs pass + submission + buffer
- Proposal, deck, architecture, wireframes are already revised — **final pass only**: README so the
  app runs from a clean clone, the demo script, and every section mapped to a problem-statement
  impact goal.
- **Lead with the measured story:** one photo + one voice note, in her own language, to a published
  listing and a buyer — the professional photographer, translator, copywriter and pricing analyst she
  could never afford to hire.
- Submit. Hold ~2 hrs as slack.

---

## Fallback ladder (spend these in order if a day slips)

1. **Image extras first** — drop synthetic shadow / perspective de-skew / angle coach; keep
   background removal + correction + crop + failure-aware retake. The core is mandated; the extras are not.
2. **Storefront before the follow** — ship the storefront (aggregation, cheap) and defer the email
   digest. The QR-opens-her-catalogue story survives without the digest.
3. **Demo on cached responses only**, skip the live linkage API — still shows the one decision.
4. **One tested language end to end** (Hindi) for the demo; describe the other three as supported-but-
   unverified rather than faking them live.

**Never cut:** the three mandated features working on a real device (Days 1–4), the offline capture +
read-back (the low-literacy claim), and the storefront + offer (the market-linkage half).

## Watch items

- **Free-tier caps + demo-day internet** — pre-cached responses and the on-device speech model are the
  mitigation. Decide and test the API fallback on Day 7, not on the day.
- **Permanent URL scheme is irreversible** once a stall QR is printed — freeze the artisan/listing id
  format deliberately (Day 5), not by accident later.
- **Pricing derives the material cost (D13), never asks for it** — the weak links are the material
  word in the transcript (glossary + an attribute confirm, not a price prompt) and the rate table's
  coverage (every demo craft needs a row). Floor is a warning (D3), so a wrong derived cost never
  locks her out.
- **Middleman capture** — bind account + stall QR to her own number, earnings visible only in her view.

## Cut list — still out (from the proposal)

payment · shipping · **dispute resolution** (the report-an-issue record only logs) · full live auctions ·
WhatsApp inbound listing · cooperative / self-help-group storefront · peer benchmarking · multi-angle
spin view · buyer accounts & order history · automated material-rate refresh · **asking the artisan
her material cost** (derived instead — D13) · a standalone IndicTrans2 MT model (Gemini does EN+HI — D11) ·
AI upscaling · the ~16 further languages the models support but that aren't tested.
