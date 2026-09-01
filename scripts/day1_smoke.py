"""Day 1 smoke test — verifies the gate: a rough photo -> clean image, and TTS speaks.

Generates a synthetic 'bad phone photo' (a blue pottery vase on a cluttered, warm-lit,
off-centre background), runs the enhancer, then synthesises a read-back line.
Writes to results/day1/. Run:  python -m scripts.day1_smoke
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from pipelines.image.enhance import enhance, rembg_available
from pipelines.voice import tts

OUT = Path("results/day1")
OUT.mkdir(parents=True, exist_ok=True)


def _make_bad_photo(path: Path) -> None:
    """A messy, warm-tinted phone photo: textured background + a blue vase, off-centre."""
    rng = np.random.default_rng(7)
    h, w = 900, 1200
    # cluttered warm background (uneven lighting + noise)
    bg = rng.integers(150, 205, (h, w, 3), dtype=np.uint8)
    bg[:, :, 0] = np.clip(bg[:, :, 0].astype(int) - 35, 0, 255)   # less blue -> warm cast
    bg[:, :, 2] = np.clip(bg[:, :, 2].astype(int) + 25, 0, 255)   # more red
    grad = np.tile(np.linspace(0.6, 1.0, w), (h, 1))              # side lighting
    bg = np.clip(bg * grad[:, :, None], 0, 255).astype(np.uint8)
    # a blue vase (ellipse body + neck), off-centre
    cx, cy = int(w * 0.42), int(h * 0.55)
    cv2.ellipse(bg, (cx, cy), (150, 210), 0, 0, 360, (150, 90, 40), -1)
    cv2.rectangle(bg, (cx - 55, cy - 260), (cx + 55, cy - 150), (150, 90, 40), -1)
    # a little surface texture on the vase
    for _ in range(400):
        x = int(rng.normal(cx, 90)); y = int(rng.normal(cy, 130))
        if 0 <= x < w and 0 <= y < h:
            cv2.circle(bg, (x, y), 2, (175, 120, 70), -1)
    cv2.imwrite(str(path), bg)


def main() -> int:
    raw = OUT / "raw_input.png"
    _make_bad_photo(raw)
    print(f"[image] rembg available: {rembg_available()}")

    res = enhance(str(raw), str(OUT))
    print(f"[image] status={res.status} method={res.method} "
          f"coverage={res.coverage:.3f} subject_frac={res.subject_frac:.3f} sep={res.separation:.3f}")
    print(f"[image] outputs: {res.outputs}")

    ok = res.status == "ok" and Path(res.outputs.get("enhanced", "")).exists()
    print(f"[image] GATE (clean image produced): {'PASS' if ok else 'FAIL'}")

    print(f"[tts] engine available: {tts.available()}")
    line = "Aapke matke ki keemat panch sau bees rupaye. Yeh sahi hai?"
    audio = OUT / "readback.aiff"
    try:
        tts.speak_to_file(line, str(audio), lang="hi")
        tts_ok = audio.exists() and audio.stat().st_size > 0
    except tts.TTSUnavailable as e:
        print(f"[tts] {e}")
        tts_ok = False
    print(f"[tts] GATE (spoke a read-back line): {'PASS' if tts_ok else 'FAIL'} -> {audio}")

    print(f"\nDay 1 gate: {'PASS' if ok and tts_ok else 'CHECK ABOVE'}")
    return 0 if ok and tts_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
