# Data Sources

Provenance for every reference figure and dataset the app depends on. Every row must be
sourced or flagged; nothing invented silently. Fill in as the reference data is assembled.

## Pricing reference set  (`data/reference/pricing_reference.csv`)
Category · material · size · region · season · price · **source** · **observed|synthesised**.
Sampled manually from public listings (GeM public listings, open handicraft marketplaces).
No seller-identifying data. Synthesised rows stay within observed real ranges and are flagged,
so the synthetic share per category can be reported.

- [ ] rows assembled · row count: __ · synthetic share per category: __

## Material-rate table  (`data/reference/material_rates.csv`)
Input cost by material + unit, with the **date** taken and the **source**. Conservative.
Only the five that move need refreshing: brass, copper, silver, silk, cotton.
Candidate sources to verify reachable+parseable before citing: Agmarknet, eNAM (fibres),
MCX (metals), WPI series (silk).

- [ ] rates entered · sources verified reachable: __

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
