"""AI Image Enhancer — mandated feature 1 (Roadmap Day 1).

A rough phone photo -> a clean e-commerce image:
  1. background removal        (rembg U2-Net; GrabCut fallback if rembg absent)
  2. composite onto white
  3. white balance             (gray-world, over the subject only)
  4. lighting / contrast       (CLAHE on L channel)
  5. failure-aware check       (bad cut-out -> keep original, ask for a retake)
  6. saliency crop             (subject bounding box -> target aspect ratio)
  7. texture close-up          (zoom crop of the subject centre, for textiles)

Deliberately NOT doing AI upscaling (cut list). Extras (blur/shake at capture,
synthetic shadow, perspective de-skew, angle coach) are separate, later functions.

CLI:  python -m pipelines.image.enhance <input_image> <out_dir>
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path

import cv2
import numpy as np

from pipelines.common import cfg_get

# ---- Background removal = U2-Net (u2netp) run DIRECTLY through onnxruntime. ----
# We deliberately do NOT use the `rembg` wrapper: it imports pymatting + numba, whose
# import-time JIT compilation stalls for minutes on first run. onnxruntime imports in
# ~0.1s and u2netp is ~4.7 MB. The session loads lazily on first use; set
# KAARIGAR_NO_REMBG=1 to force the GrabCut fallback and skip the model entirely.
import os
import urllib.request

_U2NETP_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx"
_MODEL_DIR = Path(os.path.expanduser("~/.cache/kaarigar"))
_MODEL_PATH = _MODEL_DIR / "u2netp.onnx"

_SESSION = None
_INPUT_NAME = None
_SESSION_TRIED = False

_MEAN = np.array([0.485, 0.456, 0.406], np.float32)
_STD = np.array([0.229, 0.224, 0.225], np.float32)


def _ensure_model() -> Path:
    if not _MODEL_PATH.exists():
        _MODEL_DIR.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(_U2NETP_URL, _MODEL_PATH)
    return _MODEL_PATH


def _load_u2net() -> bool:
    """Build the onnxruntime session on first call. Returns True if usable."""
    global _SESSION, _INPUT_NAME, _SESSION_TRIED
    if _SESSION_TRIED:
        return _SESSION is not None
    _SESSION_TRIED = True
    if os.environ.get("KAARIGAR_NO_REMBG") == "1":
        return False
    try:
        import onnxruntime as ort
        sess = ort.InferenceSession(str(_ensure_model()),
                                    providers=["CPUExecutionProvider"])
        _SESSION = sess
        _INPUT_NAME = sess.get_inputs()[0].name
        return True
    except Exception:  # pragma: no cover
        _SESSION = None
        return False


def bg_model_available() -> bool:
    """Whether the U2-Net onnx model is usable (triggers lazy load on first call)."""
    return _load_u2net()


def _u2net_alpha(bgr: np.ndarray) -> np.ndarray:
    """8-bit subject mask via u2netp: resize->normalise->infer->rescale mask to frame."""
    h, w = bgr.shape[:2]
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    x = cv2.resize(rgb, (320, 320)).astype(np.float32) / 255.0
    x = (x - _MEAN) / _STD
    x = np.transpose(x, (2, 0, 1))[None].astype(np.float32)  # (1,3,320,320)
    out = _SESSION.run(None, {_INPUT_NAME: x})[0]            # (1,1,320,320)
    m = out[0, 0]
    m = (m - m.min()) / (m.max() - m.min() + 1e-8)
    return cv2.resize((m * 255).astype(np.uint8), (w, h), interpolation=cv2.INTER_LINEAR)


TARGET_SIZE = 1000  # px, square e-commerce output


@dataclass
class EnhanceResult:
    status: str                     # "ok" | "retake"
    reason: str                     # why, when retake
    method: str                     # "rembg" | "grabcut"
    coverage: float                 # subject fraction of frame
    subject_frac: float             # largest connected blob / all subject pixels
    separation: float               # |mean luminance fg - bg| / 255 (informational)
    outputs: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- masks
def _grabcut_alpha(bgr: np.ndarray) -> np.ndarray:
    """Fallback background removal via GrabCut with a centred init rectangle."""
    h, w = bgr.shape[:2]
    mask = np.zeros((h, w), np.uint8)
    margin_x, margin_y = int(w * 0.08), int(h * 0.08)
    rect = (margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(bgr, mask, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
    except cv2.error:
        return np.full((h, w), 255, np.uint8)
    alpha = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    return alpha


def _subject_alpha(bgr: np.ndarray, mask_max_side: int = 720) -> tuple[np.ndarray, str]:
    """Compute the subject mask on a downscaled copy (fast), then upscale the alpha
    back to full resolution. Masking at ~720px is many times faster than full-res and
    the mask is smooth enough to upsample without visible loss."""
    h, w = bgr.shape[:2]
    scale = min(1.0, mask_max_side / max(h, w))
    small = cv2.resize(bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA) \
        if scale < 1.0 else bgr

    if _load_u2net():
        alpha_small = _u2net_alpha(small)
        method = "u2netp"
    else:
        alpha_small = _grabcut_alpha(small)
        method = "grabcut"

    if scale < 1.0:
        alpha = cv2.resize(alpha_small, (w, h), interpolation=cv2.INTER_LINEAR)
    else:
        alpha = alpha_small
    return alpha, method


def cutout_metrics(alpha: np.ndarray) -> tuple[float, float]:
    """(coverage, subject_frac): fraction of frame kept, and the largest connected
    blob as a fraction of all kept pixels."""
    m = alpha > 127
    coverage = float(m.mean())
    num, _, stats, _ = cv2.connectedComponentsWithStats(m.astype(np.uint8), 8)
    if num > 1:
        areas = stats[1:, cv2.CC_STAT_AREA].astype(float)
        subject_frac = float(areas.max() / max(areas.sum(), 1.0))
    else:
        subject_frac = 0.0
    return coverage, subject_frac


def cutout_reason(alpha: np.ndarray, min_frac: float) -> tuple[str, float, float]:
    """Pure decision: '' if the cut-out is sane, else a retake reason. Returns
    (reason, coverage, subject_frac). Gates on mask sanity, never on subject texture."""
    coverage, subject_frac = cutout_metrics(alpha)
    if coverage < 0.02 or coverage > 0.98:
        return "subject not isolated (coverage %.2f)" % coverage, coverage, subject_frac
    if subject_frac < min_frac:
        return ("cut-out fragmented (largest blob %.2f of subject)" % subject_frac,
                coverage, subject_frac)
    return "", coverage, subject_frac


# --------------------------------------------------------------- colour / lighting
def _white_balance(bgr: np.ndarray, p: int = 6, gain_clip=(0.6, 1.6)) -> np.ndarray:
    """Correct the *illuminant* using Shades-of-Gray over the whole frame.

    Estimating from the scene (not the subject) is what keeps a blue pot blue or a
    red sari red: it removes the lighting cast without neutralising the product's own
    colour. Gains are clamped so a strong cast can't over-correct.
    """
    out = bgr.astype(np.float32)
    illum = [(np.mean(out[:, :, c] ** p) ** (1.0 / p)) + 1e-6 for c in range(3)]
    gray = float(np.mean(illum))
    for c in range(3):
        gain = float(np.clip(gray / illum[c], gain_clip[0], gain_clip[1]))
        out[:, :, c] *= gain
    return np.clip(out, 0, 255).astype(np.uint8)


def _clahe_lighting(bgr: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
    return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)


# ------------------------------------------------------------------- composite/crop
def _composite_white(bgr: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    a = (alpha.astype(np.float32) / 255.0)[:, :, None]
    white = np.full_like(bgr, 255)
    return (bgr * a + white * (1 - a)).astype(np.uint8)


def _bbox(alpha: np.ndarray):
    ys, xs = np.where(alpha > 127)
    if len(xs) == 0:
        return None
    return int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())


def _crop_to_square(img: np.ndarray, box, pad_frac: float = 0.10) -> np.ndarray:
    """Crop to the subject box, padded, then letterbox to a white square."""
    h, w = img.shape[:2]
    if box is None:
        box = (0, 0, w - 1, h - 1)
    x0, y0, x1, y1 = box
    bw, bh = x1 - x0, y1 - y0
    px, py = int(bw * pad_frac), int(bh * pad_frac)
    x0, y0 = max(0, x0 - px), max(0, y0 - py)
    x1, y1 = min(w, x1 + px), min(h, y1 + py)
    crop = img[y0:y1, x0:x1]
    ch, cw = crop.shape[:2]
    side = max(ch, cw)
    canvas = np.full((side, side, 3), 255, np.uint8)
    oy, ox = (side - ch) // 2, (side - cw) // 2
    canvas[oy:oy + ch, ox:ox + cw] = crop
    return cv2.resize(canvas, (TARGET_SIZE, TARGET_SIZE), interpolation=cv2.INTER_AREA)


def _texture_closeup(img: np.ndarray, box) -> np.ndarray:
    """A zoomed square crop of the subject centre — weave / surface detail."""
    h, w = img.shape[:2]
    if box is None:
        cx, cy, r = w // 2, h // 2, min(h, w) // 4
    else:
        x0, y0, x1, y1 = box
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        r = int(min(x1 - x0, y1 - y0) * 0.28)
    r = max(r, 20)
    x0, y0 = max(0, cx - r), max(0, cy - r)
    x1, y1 = min(w, cx + r), min(h, cy + r)
    crop = img[y0:y1, x0:x1]
    if crop.size == 0:
        crop = img
    return cv2.resize(crop, (TARGET_SIZE, TARGET_SIZE), interpolation=cv2.INTER_CUBIC)


# --------------------------------------------------------------------------- public
def enhance(input_path: str, out_dir: str) -> EnhanceResult:
    """Run the full pipeline. Writes enhanced.png (+ texture.png) to out_dir."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    bgr = cv2.imread(str(input_path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(f"could not read image: {input_path}")

    alpha, method = _subject_alpha(bgr)
    box = _bbox(alpha)

    # --- failure-aware check (watchlist): is the CUT-OUT sane? ---
    # We do NOT gate on the subject's internal texture — a plain pot or a solid
    # dupatta is legitimately flat. A damaged cut-out shows up instead as a
    # degenerate mask: almost nothing kept, almost everything kept, or the subject
    # shattered into fragments. Separation (fg vs bg luminance) is reported, not gated.
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    m = alpha > 127
    if 0 < m.sum() < m.size:
        separation = float(abs(gray[m].mean() - gray[~m].mean()) / 255.0)
    else:
        separation = 0.0

    min_frac = float(cfg_get("image.min_subject_component_frac", 0.55))
    reason, coverage, subject_frac = cutout_reason(alpha, min_frac)
    if reason:
        # keep the ORIGINAL, do not publish a broken image — ask for a retake.
        orig_path = out / "original_kept.png"
        cv2.imwrite(str(orig_path), bgr)
        return EnhanceResult("retake", reason, method, coverage, subject_frac,
                             separation, {"original_kept": str(orig_path)})

    # --- enhancement path ---
    balanced = _white_balance(bgr)
    lit = _clahe_lighting(balanced)
    composited = _composite_white(lit, alpha)

    enhanced = _crop_to_square(composited, box)
    texture = _texture_closeup(lit, box)

    enhanced_path = out / "enhanced.png"
    texture_path = out / "texture.png"
    cv2.imwrite(str(enhanced_path), enhanced)
    cv2.imwrite(str(texture_path), texture)

    return EnhanceResult("ok", "", method, coverage, subject_frac, separation,
                         {"enhanced": str(enhanced_path), "texture": str(texture_path)})


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python -m pipelines.image.enhance <input_image> <out_dir>")
        raise SystemExit(2)
    res = enhance(sys.argv[1], sys.argv[2])
    print(res.as_dict())
