# Data Sources

Provenance for every reference figure and dataset the app depends on. Every row must be
sourced or flagged; nothing invented silently. Fill in as the reference data is assembled.

## Pricing reference set  (`data/reference/pricing_reference.csv`)
Category · material · size · region · season · price · **source** · **observed|synthesised**.
Sampled manually from public listings (GeM public listings, open handicraft marketplaces).
No seller-identifying data. Synthesised rows stay within observed real ranges and are flagged,
so the synthetic share per category can be reported.

- [x] rows assembled 5 Sep (Day 4) · row count: **58** across 15 categories · synthetic share:
      **100%** — every row is hand-compiled within researched-plausible Indian handicraft
      market ranges, not scraped from a live GeM/marketplace listing. Replace/augment with real
      observed listings before quoting these numbers as anything but a working default.

## Material-rate table  (`data/reference/material_rates.csv`)
Input cost by material + unit, with the **date** taken and the **source**. Conservative.
Only the five that move need refreshing: brass, copper, silver, silk, cotton.
Candidate sources to verify reachable+parseable before citing: Agmarknet, eNAM (fibres),
MCX (metals), WPI series (silk).

- [!] rates entered 5 Sep (Day 4) · **silver** (₹2,50,000/kg, goodreturns.in) and **copper**
      (~₹1,375/kg, tradingeconomics.com LME/COMEX converted via xe.com FX) are **live-fetched
      and verified reachable**. The rest (brass, clay/terracotta, cotton, silk, wool, jute,
      bamboo, sandalwood, wood) are **typical-range, hand-compiled, not live-fetched** — a
      `moneycontrol.com` fetch was blocked and a cotton-futures fetch returned a stale
      (April 2024) cached page, so those weren't used. Re-verify the typical-range rows against
      Agmarknet/eNAM/MCX/WPI before the demo; each row's `confidence` column already says which
      kind it is.

## Size-class physical estimates  (`data/reference/size_estimates.csv`)
weight_kg + hours by size_class (small/medium/large), used only to derive the fair-price
floor (material cost = weight x rate; labour cost = hours x floor_wage_per_hour). There is no
scale reference in the photo and no on-site scale, so these are deliberately conservative,
hand-compiled placeholders, not a time-and-motion study.

- [!] entered 5 Sep (Day 4) · not independently verified — replace with real measurements/
      artisan time-tracking if available before treating the floor as more than an estimate.

## Craft glossary  (`data/reference/glossary.json`)
Major named crafts + regional variants (ikat, bandhani, dhokra, madhubani, …). Hand-curated.

- [ ] glossary populated · term count: __

## Marketplace category maps  (`data/reference/category_maps/`)
Internal category → each platform's category names (GeM, ONDC, Amazon Karigar, ODOP). One file
per platform. Written once, cheap to extend.

- [ ] maps written for: [ ] GeM [ ] ONDC [ ] Karigar [ ] ODOP

## Distributions used by the simulator/demo
Acuity / condition / payer splits, hospital... *(N/A — that was the reference project.)*
Demo incident/listing seed data lives in `scripts/seed_demo.py`.
