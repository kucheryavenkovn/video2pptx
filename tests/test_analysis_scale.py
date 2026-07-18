# FILE: tests/test_analysis_scale.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit and detect-path tests for analysis_max_side dual-resolution
#   SCOPE: scale_for_analysis identity/downscale/no-upscale; detect Pass2 full-res invariant
#   DEPENDS: pytest, numpy, cv2, video2pptx.analysis_scale, video2pptx.detect_slides
#   LINKS: V-M-ANALYSIS-SCALE, V-M-DETECT-ANALYSIS-SCALE, M-ANALYSIS-SCALE
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   TestScaleForAnalysis - pure helper contracts
#   TestDetectAnalysisScale - dual-res path on fixture video
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from video2pptx.analysis_scale import normalize_analysis_max_side, scale_for_analysis
from video2pptx.config import AppConfig, VideoConfig
from video2pptx.detect_slides import run_detect_slides
from video2pptx.detection_metrics import collect
from video2pptx.video_decode import VideoDecoder

FIXTURES = Path(__file__).parent / "fixtures"
TEST_VIDEO = FIXTURES / "test_slides.mp4"


class TestNormalizeAnalysisMaxSide:
    def test_none_and_zero(self):
        assert normalize_analysis_max_side(None) is None
        assert normalize_analysis_max_side(0) is None
        assert normalize_analysis_max_side(-5) is None

    def test_positive(self):
        assert normalize_analysis_max_side(640) == 640


class TestScaleForAnalysis:
    def test_identity_when_none(self):
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        out, factor = scale_for_analysis(img, None)
        assert factor == 1.0
        assert out is img

    def test_identity_when_already_smaller(self):
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        out, factor = scale_for_analysis(img, 640)
        assert factor == 1.0
        assert out is img
        assert out.shape[:2] == (100, 200)

    def test_no_upscale(self):
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        out, factor = scale_for_analysis(img, 1920)
        assert factor == 1.0
        assert out.shape[:2] == (100, 200)

    def test_downscale_landscape_max_side(self):
        img = np.zeros((1080, 1920, 3), dtype=np.uint8)
        img[10, 10] = (255, 128, 64)
        out, factor = scale_for_analysis(img, 640)
        h, w = out.shape[:2]
        assert max(h, w) == 640
        assert w == 640
        assert h == pytest.approx(360, abs=1)
        assert 0.0 < factor < 1.0
        assert out.dtype == img.dtype

    def test_downscale_portrait_max_side(self):
        img = np.zeros((1920, 1080, 3), dtype=np.uint8)
        out, factor = scale_for_analysis(img, 480)
        h, w = out.shape[:2]
        assert max(h, w) == 480
        assert h == 480
        assert w == pytest.approx(270, abs=1)

    def test_aspect_ratio_preserved(self):
        img = np.zeros((720, 1280, 3), dtype=np.uint8)
        out, _ = scale_for_analysis(img, 320)
        h, w = out.shape[:2]
        assert abs((w / h) - (1280 / 720)) < 0.02


class TestDetectAnalysisScale:
    def test_native_default_still_detects(self, tmp_path):
        cfg = AppConfig()
        assert cfg.video.analysis_max_side is None
        doc = run_detect_slides(TEST_VIDEO, tmp_path, cfg)
        assert len(doc.slides) >= 1
        for seg in doc.slides:
            assert (tmp_path / seg.image).is_file()

    def test_analysis_max_side_metrics_and_full_res_png(self, tmp_path):
        # Fixture is 640x480 / 12s — use short min durations so segments survive.
        cfg = AppConfig(
            video=VideoConfig(sample_fps=0.5, analysis_max_side=64),
            detection={
                "min_slide_duration": 1.0,
                "min_stable_duration": 0.5,
            },
        )
        with collect() as metrics:
            doc = run_detect_slides(TEST_VIDEO, tmp_path, cfg)

        assert len(doc.slides) >= 1
        assert metrics.gauge_analysis_max_side.value == 64
        assert metrics.gauge_analysis_width.value <= 64
        assert metrics.gauge_analysis_height.value <= 64
        assert metrics.gauge_analysis_scale_factor.value <= 1.0
        # Landscape 640x480 → analysis width should hit max_side=64
        assert metrics.gauge_analysis_width.value == 64
        assert metrics.gauge_analysis_scale_factor.value < 1.0

        # Pass2 screenshots must be native ROI (full fixture frame size for slide_roi=auto)
        native_h, native_w = doc.video.height, doc.video.width
        for seg in doc.slides:
            path = tmp_path / seg.image
            assert path.is_file()
            bgr = cv2.imread(str(path))
            assert bgr is not None
            ph, pw = bgr.shape[:2]
            assert (ph, pw) == (native_h, native_w), (
                f"PNG must stay full-res; got {pw}x{ph}, native {native_w}x{native_h}"
            )

    def test_iter_frames_still_twice_with_scale(self, tmp_path, monkeypatch):
        calls = {"n": 0}
        orig = VideoDecoder.iter_frames

        def counting(self, *args, **kwargs):
            calls["n"] += 1
            yield from orig(self, *args, **kwargs)

        monkeypatch.setattr(VideoDecoder, "iter_frames", counting)
        cfg = AppConfig(video=VideoConfig(sample_fps=1.0, analysis_max_side=80))
        run_detect_slides(TEST_VIDEO, tmp_path, cfg)
        assert calls["n"] == 2
