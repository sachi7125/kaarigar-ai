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
