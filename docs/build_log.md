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
