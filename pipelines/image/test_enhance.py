"""Unit tests for the image enhancer (Day 1). Run: pytest pipelines/image/test_enhance.py -q

The cut-out *decision* is tested via the pure `cutout_reason` on synthetic masks (fast,
deterministic, no model). One integration test runs the full pipeline (loads the rembg
model on first use, ~176 MB, then cached).
"""
from __future__ import annotations

import cv2
import numpy as np

from pipelines.image.enhance import enhance, cutout_reason


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
