"""Unit tests for the image enhancer (Day 1). Run: pytest pipelines/image/test_enhance.py -q

The cut-out *decision* is tested via the pure `cutout_reason` on synthetic masks (fast,
deterministic, no model). One integration test runs the full pipeline (loads the rembg
model on first use, ~176 MB, then cached).
"""
from __future__ import annotations

import cv2
import numpy as np

from pipelines.image.enhance import (
    TARGET_SIZE, _closeup_window, _composite_white, _refine_alpha, enhance, cutout_reason,
)


# --------------------------------------------------------- pure decision (fast)
def test_cutout_ok_solid_blob():
    alpha = np.zeros((200, 200), np.uint8)
    alpha[60:140, 60:140] = 255            # one solid blob, ~16% coverage
    reason, cov, frac = cutout_reason(alpha, 0.55)
    assert reason == ""
    assert 0.02 <= cov <= 0.98 and frac == 1.0


def test_cutout_retake_empty_mask():
    alpha = np.zeros((200, 200), np.uint8)  # nothing kept
    reason, cov, _ = cutout_reason(alpha, 0.55)
    assert reason and "coverage" in reason and cov < 0.02


def test_cutout_retake_full_mask():
    alpha = np.full((200, 200), 255, np.uint8)  # everything kept -> removal failed
    reason, cov, _ = cutout_reason(alpha, 0.55)
    assert reason and cov > 0.98


def test_cutout_retake_fragmented():
    alpha = np.zeros((200, 200), np.uint8)
    alpha[20:60, 20:60] = 255              # two equal, separated blobs
    alpha[140:180, 140:180] = 255
    reason, _, frac = cutout_reason(alpha, 0.55)
    assert reason and "fragmented" in reason and frac < 0.55


# --------------------------------------------------------- full pipeline (slow)
def test_enhance_ok_branch(tmp_path):
    h, w = 600, 800
    img = np.full((h, w, 3), 210, np.uint8)                     # plain light background
    cv2.rectangle(img, (300, 200), (520, 430), (140, 110, 40), -1)  # solid product
    src = tmp_path / "clean.png"
    cv2.imwrite(str(src), img)

    res = enhance(str(src), str(tmp_path / "out"))
    assert res.status == "ok", res.reason
    assert (tmp_path / "out" / "enhanced.png").exists()
    assert (tmp_path / "out" / "texture.png").exists()


# --------------------------------------------------------- colour (Day 7)
def test_product_colour_is_left_as_photographed(tmp_path):
    """A terracotta-orange product in a warm scene: the white balance this used
    to run turned exactly this into brown (clay-pot.jpg, 11 Sep)."""
    img = np.full((600, 800, 3), (70, 110, 160), np.uint8)          # warm brown surroundings (BGR)
    cv2.rectangle(img, (280, 180), (540, 440), (53, 99, 209), -1)    # orange pot
    src = tmp_path / "warm.png"
    cv2.imwrite(str(src), img)

    res = enhance(str(src), str(tmp_path / "out"))
    assert res.status == "ok", res.reason
    out = cv2.imread(res.outputs["enhanced"])
    centre = out[out.shape[0] // 2 - 20:out.shape[0] // 2 + 20, out.shape[1] // 2 - 20:out.shape[1] // 2 + 20]
    assert np.abs(centre.reshape(-1, 3).mean(0) - np.array([53, 99, 209])).max() <= 4


# --------------------------------------------------------- cut-out edge (Day 7)
def _soft_edged_product():
    """A red product on a dark background with a deliberately soft mask — the
    same shape u2netp produces, since it decides the mask at 320x320 and the
    result is stretched back up to the photo's size."""
    bgr = np.full((400, 400, 3), (40, 40, 40), np.uint8)     # dark surroundings
    cv2.circle(bgr, (200, 200), 120, (40, 40, 200), -1)      # red product
    alpha = np.zeros((400, 400), np.uint8)
    cv2.circle(alpha, (200, 200), 120, 255, -1)
    return bgr, cv2.blur(alpha, (25, 25))                    # ...with a wide soft ramp


def _rim_contamination(bgr, alpha, product_bgr, clean_edge):
    """How far the rim strays from a clean fade of the product's own colour to
    white — i.e. how much of the old background is still showing in it.

    Each version is judged against a fade at *its own* alpha, so this measures
    only the rim's colour; its width is a separate test below.
    """
    out = _composite_white(bgr, alpha, clean_edge=clean_edge).astype(np.float32)
    a = _refine_alpha(alpha) if clean_edge else alpha.astype(np.float32) / 255.0
    band = (a > 0.02) & (a < 0.98)
    av = a[band][:, None]
    ideal = np.array(product_bgr, np.float32)[None, :] * av + 255.0 * (1.0 - av)
    return float(np.abs(out[band] - ideal).mean())


def test_edge_cleanup_removes_the_grey_rim():
    """The old background must not survive in the part-transparent pixels: a red
    product cut off a dark backdrop used to fade out through grey."""
    bgr, alpha = _soft_edged_product()
    product = (40, 40, 200)
    before = _rim_contamination(bgr, alpha, product, clean_edge=False)
    after = _rim_contamination(bgr, alpha, product, clean_edge=True)
    assert after < before / 2        # the rim keeps the product's colour, not the backdrop's


def test_edge_cleanup_narrows_the_soft_band():
    bgr, alpha = _soft_edged_product()
    a = _refine_alpha(alpha)
    wide = ((alpha > 5) & (alpha < 250)).sum()
    narrow = ((a > 0.02) & (a < 0.98)).sum()
    assert narrow < wide / 3
    assert narrow > 0                # still anti-aliased, not cut with scissors


def test_edge_cleanup_never_touches_the_product_itself():
    """The colour promise (D8) is unchanged: a fully-opaque pixel is the photo's."""
    bgr, alpha = _soft_edged_product()
    out = _composite_white(bgr, alpha, clean_edge=True)
    opaque = alpha == 255
    assert np.abs(out.astype(int) - bgr.astype(int))[opaque].max() == 0


# --------------------------------------------------------- close-up (Day 7)
def _product_with_detail_patch():
    """A plain orange product filling most of a 1600×1200 frame, with one
    small patterned patch near its bottom-right corner."""
    bgr = np.full((1200, 1600, 3), (40, 90, 50), np.uint8)
    alpha = np.zeros((1200, 1600), np.uint8)
    cv2.rectangle(bgr, (200, 150), (1400, 1050), (53, 99, 209), -1)
    alpha[150:1051, 200:1401] = 255
    for y in range(850, 950, 10):                       # checkerboard: the "zari motif"
        for x in range(1150, 1250, 10):
            if (x // 10 + y // 10) % 2:
                bgr[y:y + 10, x:x + 10] = (240, 240, 240)
    return bgr, alpha, (200, 150, 1400, 1050)


def test_closeup_goes_to_the_most_detailed_part_not_the_centre():
    bgr, alpha, box = _product_with_detail_patch()
    x, y, side = _closeup_window(bgr, alpha, box)
    assert x <= 1200 <= x + side and y <= 900 <= y + side        # the patch's centre is in view
    assert alpha[y:y + side, x:x + side].mean() / 255 >= 0.97    # and it's all product, no background


def test_a_plain_product_falls_back_to_its_middle():
    bgr, alpha, box = _product_with_detail_patch()
    cv2.rectangle(bgr, (200, 150), (1400, 1050), (53, 99, 209), -1)  # paint the patch over
    x, y, side = _closeup_window(bgr, alpha, box)
    assert x <= 800 <= x + side and y <= 600 <= y + side


def test_the_main_image_is_never_blown_up_either(tmp_path):
    """A small crop stays at its own resolution: INTER_AREA asked to enlarge
    steps like nearest-neighbour, which put staircase edges on real photos."""
    img = np.full((600, 800, 3), 210, np.uint8)
    cv2.rectangle(img, (300, 200), (520, 430), (140, 110, 40), -1)   # small product
    src = tmp_path / "small_product.png"
    cv2.imwrite(str(src), img)
    out = cv2.imread(enhance(str(src), str(tmp_path / "out")).outputs["enhanced"])
    assert out.shape[0] == out.shape[1] < TARGET_SIZE     # square, and its own pixels


def test_a_big_photo_is_still_capped(tmp_path):
    img = np.full((2400, 2400, 3), 210, np.uint8)
    cv2.rectangle(img, (200, 200), (2200, 2200), (140, 110, 40), -1)
    src = tmp_path / "big.png"
    cv2.imwrite(str(src), img)
    out = cv2.imread(enhance(str(src), str(tmp_path / "out")).outputs["enhanced"])
    assert out.shape[0] == out.shape[1] == TARGET_SIZE


def test_closeup_is_never_blown_up(tmp_path):
    img = np.full((600, 800, 3), 210, np.uint8)
    cv2.rectangle(img, (300, 200), (520, 430), (140, 110, 40), -1)
    src = tmp_path / "small.png"
    cv2.imwrite(str(src), img)
    texture = cv2.imread(enhance(str(src), str(tmp_path / "out")).outputs["texture"])
    assert texture.shape[0] == texture.shape[1] < TARGET_SIZE      # the source's own pixels
