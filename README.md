# KaarigarAI

**The AI Virtual Business Manager for Marginalized Artisans** · Smart India Hackathon 2026 ·
Problem Statement **SIH26090** · Team **Algorhythm**.

One photo. One voice note. In her own language → a clean listing, a fair price, and a buyer.
KaarigarAI is the professional photographer, translator, copywriter and pricing analyst an
artisan could never afford to hire — and then it carries the finished listing to a buyer.

## Status

Pre-build. Documentation (proposal, deck, architecture, wireframes) is complete; the app is
not started. Work is tracked in [`docs/tracker.md`](docs/tracker.md) against the 9-day plan in
[`docs/planning/KaarigarAI_9Day_Roadmap.md`](docs/planning/KaarigarAI_9Day_Roadmap.md).

## What it does (three mandated features + the market-linkage half)

1. **AI Image Enhancer** — a rough phone photo → clean e-commerce image (rembg + OpenCV).
2. **Multilingual Auto-Cataloger** — a regional voice note → bilingual listing, read back aloud
   and confirmed by voice (whisper + Gemini; Gemini also does the EN+HI translation).
3. **Dynamic Pricing Assistant** — image + voice → a price *band* with a plain explanation and a
   fair-price floor (XGBoost + SHAP). She never enters a price or a cost: material *type* comes
   from her voice note, and the cost is derived from current rates — not a photo classifier, not a
   question.
4. **Market linkage** — permanent listing page, per-artisan **storefront**, structured **offer**
   inbox with stock, export bundle (GeM/ONDC/Karigar/ODOP), share card, stall QR.

## Repository layout

```
docs/            planning roadmap, deliverables, and the living project docs (below)
  planning/      the 9-day build roadmap (md + pdf)
  deliverables/  proposal, deck, architecture, wireframes, feature-decision note (+ sources/)
  tracker.md     what's done / in progress / next   ← updated every task
  watchlist.md   risks and things to verify later    ← updated when noticed
  build_log.md   dated narrative of what was built    ← updated when a task is done
  decisions.md   design decisions with rationale
  data_sources.md provenance for every reference figure
config/          config.yaml — all tunable parameters in one place
backend/         FastAPI (stateless): API + public storefront/listing pages + job-queue workers
pipelines/       AI workers: image/ · voice/ · pricing/
mobile/          Flutter app (voice-first, offline-first)
ml/              pricing model training + saved models
scripts/         export bundle, share card, stall QR, demo seeding
data/            raw/ · processed/ · reference/ (glossary, material rates, category maps)
assets/          generated share cards and QR posters
```

## Working protocol (how this repo is maintained)

Every task, in order:
1. Do the work.
2. **Update `docs/tracker.md`** — mark the task, note the commit.
3. **Append to `docs/build_log.md`** — what was built, how to run it, anything non-obvious.
4. **Add to `docs/watchlist.md`** anything that could break later or needs verifying at a
   specific point.
5. Record any real design choice in `docs/decisions.md`.

Read `docs/watchlist.md` at the start of each build day and clear anything now due.

## Getting started (once building)

```bash
# backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# mobile
cd mobile && flutter pub get
```

Secrets (Google Routes/Maps key, Gemini key, DB URL) live in `.env` — never committed.

## Locked scope (see docs/decisions.md)

No buyer marketplace (storefront + direct offer instead) · no material classifier (material type
from voice) · material cost derived, never asked (D13) · dated + sourced material rates on screen ·
listings carry stock · per-artisan storefront.
**Out:** payment, shipping, dispute resolution, live auctions, WhatsApp ingestion — full cut list
in the roadmap.
