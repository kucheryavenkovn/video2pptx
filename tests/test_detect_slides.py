# FILE: tests/test_detect_slides.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for standalone detect-slides pipeline (no subtitles, no export)
#   SCOPE: run_detect_slides on synthetic video, verify SlidesDocument fields and screenshots
#   DEPENDS: pytest, video2pptx.detect_slides, video2pptx.config, loguru
#   LINKS: V-M-DETECT-SLIDES
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from video2pptx.config import AppConfig
from video2pptx.detect_slides import run_detect_slides
from video2pptx.video_decode import VideoDecoder

FIXTURES = Path(__file__).parent / "fixtures"
TEST_VIDEO = FIXTURES / "test_slides.mp4"

# Canonical output signature for test_slides.mp4 at AppConfig defaults (sample_fps=0.5)
# Captured from approved v0.1.0 TwoPass detection.
# Changes to the detection algorithm must update this signature.
_APPROVED_SIGNATURE = "c11f0288e2861a5a16461a5c4987c4d2f15b6f7bb1ff4e24c00233137eb6b698"


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
        assert "Pass 1/2: detecting changes" in combined
        assert "Pass 2/2: saving screenshots" in combined
        assert "Pass 3/3" not in combined
        assert "Document saved" in combined

    def test_log_markers_dedupe_enabled(self, tmp_path, loguru_sink):
        """Verify 2-pass markers when dedup is enabled with multiple segments."""
        cfg = AppConfig()
        cfg.detection.threshold = 5.0
        run_detect_slides(
            video_path=TEST_VIDEO,
            out_dir=tmp_path,
            cfg=cfg,
        )
        combined = " ".join(loguru_sink)
        assert "Pass 1/2: detecting changes" in combined
        assert "Pass 2/2" in combined
        assert "Pass 3/3" not in combined

    # ------------------------------------------------------------------
    # Decoder call count tests
    # ------------------------------------------------------------------

    def test_iter_frames_called_exactly_twice(self, tmp_path, monkeypatch):
        """With 2-pass optimization, iter_frames must be called exactly 2 times."""
        call_count = 0
        original_iter_frames = VideoDecoder.iter_frames
        original_info = VideoDecoder.get_info

        def counting_iter_frames(self):
            nonlocal call_count
            call_count += 1
            yield from original_iter_frames(self)

        monkeypatch.setattr(VideoDecoder, "iter_frames", counting_iter_frames)

        cfg = AppConfig()
        run_detect_slides(
            video_path=TEST_VIDEO,
            out_dir=tmp_path,
            cfg=cfg,
        )
        assert call_count == 2, f"iter_frames called {call_count} times, expected 2"

    def test_iter_frames_called_twice_dedupe_disabled(self, tmp_path, monkeypatch):
        """Even with dedup disabled, iter_frames must still be called exactly 2 times."""
        call_count = 0
        original_iter_frames = VideoDecoder.iter_frames

        def counting_iter_frames(self):
            nonlocal call_count
            call_count += 1
            yield from original_iter_frames(self)

        monkeypatch.setattr(VideoDecoder, "iter_frames", counting_iter_frames)

        cfg = AppConfig()
        cfg.detection.dedupe_enabled = False
        run_detect_slides(
            video_path=TEST_VIDEO,
            out_dir=tmp_path,
            cfg=cfg,
        )
        assert call_count == 2, f"iter_frames called {call_count} times, expected 2"

    # ------------------------------------------------------------------
    # Output parity test
    # ------------------------------------------------------------------

    def test_output_signature_match(self, tmp_path):
        """Verify TwoPass output matches approved reference signature."""
        cfg = AppConfig()
        doc = run_detect_slides(
            video_path=TEST_VIDEO,
            out_dir=tmp_path,
            cfg=cfg,
        )

        canonical = {
            "score_timestamps": [round(t, 4) for t in doc.score_timestamps],
            "score_values": [round(v, 4) for v in doc.score_values],
            "segments": [
                {
                    "start": round(s.start, 4),
                    "end": round(s.end, 4),
                    "representative_timestamp": round(s.representative_timestamp, 4),
                    "image": s.image,
                }
                for s in doc.slides
            ],
            "screenshot_count": len(list((tmp_path / "slides").glob("*.png"))),
        }
        raw = json.dumps(canonical, sort_keys=True, default=str).encode("utf-8")
        actual_sig = hashlib.sha256(raw).hexdigest()
        assert actual_sig == _APPROVED_SIGNATURE, (
            f"Output signature mismatch: {actual_sig} != {_APPROVED_SIGNATURE}\n"
            f"This means the detection output changed. If intentional, "
            f"update _APPROVED_SIGNATURE in the test."
        )

    def test_screenshots_have_valid_pngs(self, tmp_path):
        """Every screenshot is a valid PNG file with non-zero size."""
        cfg = AppConfig()
        doc = run_detect_slides(
            video_path=TEST_VIDEO,
            out_dir=tmp_path,
            cfg=cfg,
        )
        for seg in doc.slides:
            assert seg.image is not None
            img_path = tmp_path / seg.image
            assert img_path.is_file(), f"Missing: {img_path}"
            assert img_path.stat().st_size > 0, f"Empty: {img_path}"
            # Verify PNG header
            header = img_path.read_bytes()[:4]
            assert header == b"\x89PNG", f"Not a valid PNG: {img_path}"
