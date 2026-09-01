"""Run the Day 1 enhancer on your OWN photo and open a before/after image.

No web server — just processes the file and opens a comparison PNG.

Usage:  python -m scripts.try_photo <path-to-your-photo.jpg>
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from pipelines.image.enhance import enhance


def build(photo: str) -> str:
    out = Path("results/mytest")
    out.mkdir(parents=True, exist_ok=True)
    res = enhance(photo, str(out))

    if res.status == "ok":
        panels = [(photo, "raw"),
                  (res.outputs["enhanced"], "enhanced"),
                  (res.outputs["texture"], "texture close-up")]
        print(f"OK · method={res.method} coverage={res.coverage:.2f} "
              f"subject_frac={res.subject_frac:.2f}")
    else:
        panels = [(photo, "raw"), (res.outputs["original_kept"], "kept for retake")]
        print(f"RETAKE requested — {res.reason} (this is the failure-aware check working)")

    H = 380
    imgs = []
    for path, label in panels:
        im = Image.open(path).convert("RGB")
        im = im.resize((int(im.width * H / im.height), H))
        imgs.append((im, label))
    gap = 20
    W = sum(im.width for im, _ in imgs) + gap * (len(imgs) + 1)
    canvas = Image.new("RGB", (W, H + 34), (245, 245, 245))
    d = ImageDraw.Draw(canvas)
    x = gap
    for im, label in imgs:
        canvas.paste(im, (x, 28))
        d.text((x + 2, 8), label, fill=(60, 60, 60))
        x += im.width + gap
    compare = out / "_compare.png"
    canvas.save(compare)
    return str(compare)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: python -m scripts.try_photo <path-to-your-photo.jpg>")
        return 2
    photo = sys.argv[1]
    if not Path(photo).exists():
        print(f"file not found: {photo}")
        return 1
    compare = build(photo)
    print(f"wrote {compare}")
    if sys.platform == "darwin":
        subprocess.run(["open", compare])  # opens Preview
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
