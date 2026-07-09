# FILE: tests/test_detect_slides.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for standalone detect-slides pipeline (no subtitles, no export)
#   SCOPE: run_detect_slides on synthetic video, verify SlidesDocument fields and screenshots
#   DEPENDS: pytest, video_slide_md.detect_slides, video_slide_md.config, loguru
#   LINKS: V-M-DETECT-SLIDES
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

from pathlib import Path

import pytest

from video_slide_md.config import AppConfig
from video_slide_md.detect_slides import run_detect_slides

FIXTURES = Path(__file__).parent / "fixtures"
TEST_VIDEO = FIXTURES / "test_slides.mp4"


class TestDetectSlides:
    def test_run_basic(self, tmp_path, loguru_sink):
        """run_detect_slides produces valid SlidesDocument with screenshots."""
        cfg = AppConfig()
        doc = run_detect_slides(
            video_path=TEST_VIDEO,
            out_dir=tmp_path,
            cfg=cfg,
        )

        assert doc.video is not None
        assert doc.video.duration > 0
        assert doc.video.width > 0
        assert doc.video.height > 0

        assert len(doc.slides) >= 1

        for seg in doc.slides:
            assert seg.image is not None
            img_path = tmp_path / seg.image
            assert img_path.is_file(), f"Screenshot missing: {img_path}"
            assert seg.start >= 0.0
            assert seg.end > seg.start

        slides_json = tmp_path / "slides.json"
        assert slides_json.is_file()

    def test_missing_video_raises(self, tmp_path):
        """Missing video path should raise FileNotFoundError or similar."""
        cfg = AppConfig()
        bogus = tmp_path / "does_not_exist.mp4"
        with pytest.raises((FileNotFoundError, RuntimeError)):
            run_detect_slides(video_path=bogus, out_dir=tmp_path, cfg=cfg)

    def test_custom_threshold(self, tmp_path):
        """Passing a custom threshold produces a valid result."""
        cfg = AppConfig()
        cfg.detection.threshold = 15.0
        doc = run_detect_slides(
            video_path=TEST_VIDEO,
            out_dir=tmp_path,
            cfg=cfg,
        )
        assert len(doc.slides) >= 1

    def test_dedupe_disabled(self, tmp_path):
        """Deduplication can be disabled without crashing."""
        cfg = AppConfig()
        cfg.detection.dedupe_enabled = False
        doc = run_detect_slides(
            video_path=TEST_VIDEO,
            out_dir=tmp_path,
            cfg=cfg,
        )
        assert len(doc.slides) >= 1

    def test_log_markers_present(self, tmp_path, loguru_sink):
        """Verify required log markers appear in output."""
        cfg = AppConfig()
        run_detect_slides(
            video_path=TEST_VIDEO,
            out_dir=tmp_path,
            cfg=cfg,
        )
        combined = " ".join(loguru_sink)
        assert "Pass 1/3: detecting changes" in combined
        assert "Pass 3/3: saving screenshots" in combined
        assert "Document saved" in combined
