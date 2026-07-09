# FILE: tests/test_frame_features.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for frame feature extraction and visual distance
#   SCOPE: Feature extraction, hash computation, distance metrics, auto threshold
#   DEPENDS: pytest, numpy, video2pptx.frame_features
#   LINKS: V-M-FRAME-FEATURES
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

import numpy as np
import pytest

from video2pptx.frame_features import (
    DISTANCE_WEIGHTS,
    compute_threshold,
    extract_features,
    visual_distance,
)
from video2pptx.models import FrameFeatures


def make_solid_rgb(color: tuple[int, int, int], h: int = 100, w: int = 100) -> np.ndarray:
    return np.full((h, w, 3), color, dtype=np.uint8)


class TestExtractFeatures:
    def test_phash_is_string(self):
        img = make_solid_rgb((100, 150, 200))
        ff = extract_features(img)
        assert isinstance(ff.phash, str)
        assert len(ff.phash) > 0

    def test_dhash_is_string(self):
        img = make_solid_rgb((100, 150, 200))
        ff = extract_features(img)
        assert isinstance(ff.dhash, str)
        assert len(ff.dhash) > 0

    def test_gray_mean(self):
        img = make_solid_rgb((128, 128, 128))
        ff = extract_features(img)
        assert ff.gray_mean == pytest.approx(128.0, abs=5.0)

    def test_histogram_sum(self):
        img = make_solid_rgb((100, 150, 200))
        ff = extract_features(img)
        assert len(ff.hist) == 768  # 256 * 3 = 768 bins
        assert sum(ff.hist) == pytest.approx(3.0, abs=0.1)

    def test_same_image_same_hash(self):
        img = make_solid_rgb((100, 100, 100))
        ff1 = extract_features(img)
        ff2 = extract_features(img)
        assert ff1.phash == ff2.phash
        assert ff1.dhash == ff2.dhash

    def test_different_images_different_hash(self):
        img1 = make_solid_rgb((0, 0, 0))
        img2 = make_solid_rgb((255, 255, 255))
        ff1 = extract_features(img1)
        ff2 = extract_features(img2)
        assert ff1.phash != ff2.phash


class TestVisualDistance:
    def test_same_frames_zero_distance(self):
        img = make_solid_rgb((100, 150, 200))
        ff = extract_features(img)
        dist = visual_distance(ff, ff)
        assert dist == 0.0

    def test_different_frames_positive_distance(self):
        img1 = make_solid_rgb((0, 0, 0))
        img2 = make_solid_rgb((255, 255, 255))
        ff1 = extract_features(img1)
        ff2 = extract_features(img2)
        dist = visual_distance(ff1, ff2)
        assert dist > 0.0

    def test_distance_bounded(self):
        img1 = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        img2 = np.random.randint(0, 255, (50, 50, 3), dtype=np.uint8)
        ff1 = extract_features(img1)
        ff2 = extract_features(img2)
        dist = visual_distance(ff1, ff2)
        assert 0.0 <= dist <= 1.0

    def test_distance_missing_hash(self):
        ff1 = FrameFeatures(timestamp=0.0, phash="", dhash="", hist=[0.5], gray_mean=0.0)
        ff2 = FrameFeatures(timestamp=1.0, phash="abc", dhash="def")
        dist = visual_distance(ff1, ff2)
        assert dist == 0.0

    def test_partial_histogram_distance(self):
        ff1 = FrameFeatures(timestamp=0.0, phash="", dhash="", hist=[1.0, 0.0], gray_mean=0.0)
        ff2 = FrameFeatures(timestamp=1.0, phash="", dhash="", hist=[0.0, 1.0], gray_mean=0.0)
        # Only hist component matters: weight * (1 - intersection)
        expected = DISTANCE_WEIGHTS["hist"] * (1.0 - 0.0)
        assert visual_distance(ff1, ff2) == pytest.approx(expected, abs=0.001)


class TestComputeThreshold:
    def test_short_list_returns_default(self):
        t = compute_threshold([0.1, 0.2])
        assert t == 0.3

    def test_long_list_returns_reasonable(self):
        scores = [0.05, 0.06, 0.05, 0.07, 0.50, 0.55, 0.60]
        t = compute_threshold(scores)
        assert 0.05 < t < 0.6

    def test_with_k_parameter(self):
        scores = [0.1, 0.1, 0.1, 0.9]
        t1 = compute_threshold(scores, k=1.0)
        t2 = compute_threshold(scores, k=5.0)
        # Higher k = higher threshold
        assert t2 >= t1
