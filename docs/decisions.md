# Decisions

Design decisions with rationale, so the boundary of the prototype is a record, not a gap.
Add a row when a real choice is made. `D#` ids are stable; reference them in commits.

| # | Decision | Rationale | When |
|---|---|---|---|
| D1 | **No buyer marketplace.** Permanent listing page + per-artisan storefront + a direct structured offer instead. | PS asks for B2B buyers *or* government e-marketplaces — an *or*; the export bundle satisfies the second alone. A catalogue of our own would launch with zero buyers (worst-case cold start). | 30 Aug |
| D2 | **No material classifier.** Material comes from the voice note; the photo only *suggests* category/size/finish, confirmed by 0–2 spoken questions. | No labelled dataset of Indian craft materials on entry-level phone photos; telling silk from polyester in a dim photo is hard for a person. The artisan is ground truth. | 30 Aug |
| D3 | **Material rates are a dated, sourced snapshot** printed on screen; weekly refresh described, not built. | Only ~5 inputs move enough to matter (brass, copper, silver, silk, cotton); the floor is a warning, not a quote, so staleness barely changes it. | 30 Aug |
| D4 | **Listings carry stock** (unique vs batch + remaining count); reserve-on-accept is the quantity-one case. | An exporter wants 200 diyas, not one; most output is a run, not a single object. | 30 Aug |
| D5 | **Per-artisan storefront** as the year-round channel; the stall QR points at it, not a single listing. | Cheap (aggregation over listing pages) and the largest single change to what a buyer sees; turns a one-day fair visitor into a returning contact. | 30 Aug |
| D6 | **Report-an-issue logs only** — no adjudication, refund, or delist. | Full dispute resolution needs the settlement machinery kept out of scope; a logged, two-sided record is the honest prototype version. | 30 Aug |
| D7 | **Failure-aware image check = mask sanity, not subject contrast.** Retake when coverage is degenerate or the cut-out is fragmented (largest blob < 0.55). | Gating on the subject's internal contrast wrongly rejected legitimately flat-coloured products (a plain pot, a solid dupatta). The real failure is a bad *cut-out*, which shows up in the mask. | 30 Aug (Day 1) |
| D8 | **White balance is scene-based Shades-of-Gray with clamped gains**, not gray-world over the subject. | Gray-world over the subject neutralises a strongly single-coloured product — a blue pot came out grey. Estimating the illuminant from the whole frame corrects the cast while keeping the product's colour. | 30 Aug (Day 1) |
| D9 | **Background removal runs u2netp directly via onnxruntime; the `rembg` wrapper is dropped.** OpenCV pinned to 4.10.x; pip keyring disabled. | rembg imports pymatting+numba whose JIT stalls for minutes on the dev machine; onnxruntime imports in ~0.1s. OpenCV 5.0.0 (beta) imported in 25s; 4.10 in ~1s. pip froze on the macOS Keychain until keyring was disabled. All verified on the target MacBook Air (arm64). | 1 Sep (Day 1) |

## Open decisions

| # | Question | Leaning | Decide by |
|---|---|---|---|
| O1 | Backend hosting tier that keeps a **permanent** domain (stall QR must resolve months later)? | managed free tier w/ stable domain, not a tunnel | Day 5 |
| O2 | Object storage provider for public product photos? | — | Day 1 |
| O3 | Which four languages are demo-tested end to end? | Hindi (lead) + Bengali/Tamil/Marathi | Day 2 |
