# FILE: src/video_slide_md/frame_features.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Frame feature extraction (hashes, histograms, grayscale) for slide comparison
#   SCOPE: Compute pHash, dHash, grayscale thumbnail, color histogram, weighted visual distance
#   DEPENDS: numpy, imagehash, opencv-python, Pillow, models, loguru
#   LINKS: M-FRAME-FEATURES
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   extract_features - compute FrameFeatures from an image
#   visual_distance - weighted similarity score between two FrameFeatures
#   compute_threshold - auto threshold from score distribution
# END_MODULE_MAP

from __future__ import annotations

import io
from typing import Sequence

import cv2
import imagehash
import numpy as np
from loguru import logger
from PIL import Image

from video_slide_md.models import FrameFeatures

# START_BLOCK_DEFAULT_WEIGHTS
DISTANCE_WEIGHTS: dict[str, float] = {
    "phash": 0.40,
    "dhash": 0.30,
    "mse": 0.20,
    "hist": 0.10,
}
# END_BLOCK_DEFAULT_WEIGHTS


def extract_features(image: np.ndarray) -> FrameFeatures:
    # START_CONTRACT: extract_features
    #   PURPOSE: Compute frame features for slide comparison
    #   INPUTS: { image: np.ndarray — RGB array (H, W, C) }
    #   OUTPUTS: FrameFeatures with timestamp=0 (caller sets it)
    #   SIDE_EFFECTS: none
    #   LINKS: M-FRAME-FEATURES
    # END_CONTRACT: extract_features

    # START_BLOCK_EXTRACT
    h, w = image.shape[:2]

    # Grayscale + downscale to 64x64
    gray = cv2_to_gray(image)
    small = cv2_resize(gray, 64)

    gray_mean = float(np.mean(small))

    # Perceptual hash via imagehash
    pil_img = array_to_pil(image)
    phash_str = str(imagehash.phash(pil_img))
    dhash_str = str(imagehash.dhash(pil_img))

    # Color histogram (256 bins per channel → 768 values)
    hist = compute_histogram(image)

    features = FrameFeatures(
        timestamp=0.0,
        phash=phash_str,
        dhash=dhash_str,
        hist=hist,
        gray_mean=gray_mean,
    )
    return features
    # END_BLOCK_EXTRACT


def visual_distance(a: FrameFeatures, b: FrameFeatures) -> float:
    # START_CONTRACT: visual_distance
    #   PURPOSE: Compute weighted visual distance between two frames
    #   INPUTS: { a: FrameFeatures, b: FrameFeatures }
    #   OUTPUTS: float in [0, 1] — higher means more different
    #   SIDE_EFFECTS: none
    #   LINKS: M-FRAME-FEATURES
    # END_CONTRACT: visual_distance

    # START_BLOCK_DISTANCE
    score = 0.0

    # pHash distance (normalized: max hamming distance is len(hash)*4 for hex)
    if a.phash and b.phash:
        ph_d = _hamming_hex(a.phash, b.phash)
        ph_norm = min(1.0, ph_d / (len(a.phash) * 4.0))
        score += DISTANCE_WEIGHTS["phash"] * ph_norm

    # dHash distance
    if a.dhash and b.dhash:
        dh_d = _hamming_hex(a.dhash, b.dhash)
        dh_norm = min(1.0, dh_d / (len(a.dhash) * 4.0))
        score += DISTANCE_WEIGHTS["dhash"] * dh_norm

    # MSE (normalized to 0-1 by dividing by 255^2)
    if a.hist and b.hist:
        mse_val = _mse(a.hist, b.hist)
        score += DISTANCE_WEIGHTS["mse"] * min(1.0, mse_val / (255.0 ** 2))

    # Histogram intersection distance
    if a.hist and b.hist:
        hist_dist = _histogram_distance(a.hist, b.hist)
        score += DISTANCE_WEIGHTS["hist"] * hist_dist
    # END_BLOCK_DISTANCE

    return score


def compute_threshold(scores: Sequence[float], k: float = 3.0) -> float:
    # START_CONTRACT: compute_threshold
    #   PURPOSE: Compute auto threshold from diff score distribution: median + k * MAD
    #   INPUTS: { scores: list[float], k: float }
    #   OUTPUTS: float — threshold value
    #   SIDE_EFFECTS: none
    #   LINKS: M-FRAME-FEATURES
    # END_CONTRACT: compute_threshold

    if len(scores) < 3:
        return 0.3
    arr = np.array(scores)
    median = float(np.median(arr))
    mad = float(np.median(np.abs(arr - median)))
    threshold = median + k * mad
    logger.debug(
        f"[FrameFeatures][compute_threshold] "
        f"median={median:.4f} mad={mad:.4f} k={k} threshold={threshold:.4f}"
    )
    return threshold


# --- Low-level helpers ---

def _hamming_hex(a: str, b: str) -> int:
    """Hamming distance between two hex strings."""
    if len(a) != len(b):
        return max(len(a), len(b)) * 4
    distance = 0
    for ca, cb in zip(a, b):
        distance += bin(int(ca, 16) ^ int(cb, 16)).count("1")
    return distance


def _mse(hist_a: list[float], hist_b: list[float]) -> float:
    """Mean squared error between two histograms."""
    if not hist_a or not hist_b:
        return 0.0
    a = np.array(hist_a, dtype=np.float32)
    b = np.array(hist_b, dtype=np.float32)
    return float(np.mean((a - b) ** 2))


def _histogram_distance(hist_a: list[float], hist_b: list[float]) -> float:
    """Normalized histogram distance using intersection."""
    if not hist_a or not hist_b:
        return 0.0
    a = np.array(hist_a, dtype=np.float32)
    b = np.array(hist_b, dtype=np.float32)
    intersection = np.sum(np.minimum(a, b))
    total = max(np.sum(a), np.sum(b))
    if total == 0:
        return 0.0
    return 1.0 - intersection / total


def compute_histogram(image: np.ndarray, bins: int = 256) -> list[float]:
    """Compute normalized 3-channel color histogram."""
    hists: list[float] = []
    for channel in range(3):
        hist = cv2_calc_hist(image, channel, bins)
        hists.extend(hist)
    return hists


# --- cv2-like helpers that work on RGB arrays ---
def cv2_to_gray(image: np.ndarray) -> np.ndarray:
    """Convert RGB to grayscale using luminance weights."""
    return np.dot(image[..., :3], [0.299, 0.587, 0.114]).astype(np.uint8)


def cv2_resize(image: np.ndarray, size: int) -> np.ndarray:
    """Resize image to (size x size) using linear interpolation."""
    h, w = image.shape[:2]
    scale = size / max(h, w)
    new_h, new_w = int(h * scale), int(w * scale)
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)


def cv2_calc_hist(image: np.ndarray, channel: int, bins: int = 256) -> list[float]:
    """Compute 1D histogram for a single channel."""
    channel_data = image[:, :, channel].ravel().astype(np.float32)
    hist, _ = np.histogram(channel_data, bins=bins, range=(0, 256))
    total = hist.sum()
    if total > 0:
        hist = hist / total
    return hist.tolist()


def array_to_pil(image: np.ndarray) -> Image.Image:
    """Convert numpy RGB array to PIL Image."""
    return Image.fromarray(image)
