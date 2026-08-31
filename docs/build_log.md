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
