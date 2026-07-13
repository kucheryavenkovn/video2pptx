# FILE: tests/test_detect_slides.py
# VERSION: 0.3.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for standalone detect-slides pipeline (no subtitles, no export)
#   SCOPE: Pipeline output, two-pass decode, and deterministic RSS lifecycle/peak semantics
#   DEPENDS: pytest, video2pptx.detect_slides, video2pptx.config, loguru
#   LINKS: V-M-DETECT-SLIDES
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   TestDetectSlides - integration and two-pass pipeline regression checks
#   TestRssLifecycle - deterministic sampler ordering, peak, and exception cleanup checks
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v0.3.0 - Completed RSS maximum branches and detector-work cleanup evidence
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from video2pptx import detect_slides
from video2pptx.config import AppConfig
from video2pptx.detect_slides import run_detect_slides
from video2pptx.detection_metrics import collect
from video2pptx.video_decode import VideoDecoder

FIXTURES = Path(__file__).parent / "fixtures"
TEST_VIDEO = FIXTURES / "test_slides.mp4"

# TwoPass output parity is verified against 3472e62 3-pass reference artifact
# in tests/test_twopass_parity.py.

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


class TestRssLifecycle:
    @staticmethod
    def _patch_pipeline(monkeypatch, events, sampled_peak):
        class FakeSampler:
            def __init__(self, interval):
                self.peak_mb = sampled_peak

            def start(self):
                events.append("sampler_start")

            def stop(self):
                events.append("sampler_stop")

        class FakeDecoder:
            def __init__(self, **kwargs):
                pass

            def get_info(self):
                return SimpleNamespace(duration=1.0, width=2, height=2, fps=10.0)

            def iter_frames(self):
                yield SimpleNamespace(
                    timestamp=0.0,
                    image=np.zeros((2, 2, 3), dtype=np.uint8),
                )

        class FakeDocument:
            def __init__(self, **kwargs):
                events.append("document")

            def model_dump_json(self, indent):
                return "{}"

        segment = SimpleNamespace(index=0, representative_timestamp=0.0, image=None)
        monkeypatch.setattr(detect_slides, "RssSampler", FakeSampler)
        monkeypatch.setattr(detect_slides, "VideoDecoder", FakeDecoder)
        monkeypatch.setattr(detect_slides, "SlidesDocument", FakeDocument)
        monkeypatch.setattr(
            detect_slides,
            "detect_changes",
            lambda **kwargs: ([], [], []),
        )
        monkeypatch.setattr(detect_slides, "build_segments", lambda **kwargs: [segment])
        monkeypatch.setattr(detect_slides.cv2, "cvtColor", lambda image, code: image)
        monkeypatch.setattr(detect_slides.cv2, "imwrite", lambda path, image: True)

    @pytest.mark.parametrize(
        ("rss_values", "sampled_peak", "expected_peak"),
        [
            pytest.param([200.0, 175.0], 150.0, 200.0, id="before-highest"),
            pytest.param([100.0, 120.0], 140.0, 140.0, id="sampled-highest"),
            pytest.param([100.0, 120.0], 80.0, 120.0, id="after-highest"),
        ],
    )
    def test_persistence_precedes_stop_and_peak_is_max(
        self, tmp_path, monkeypatch, rss_values, sampled_peak, expected_peak
    ):
        events = []
        self._patch_pipeline(monkeypatch, events, sampled_peak)
        rss_iter = iter(rss_values)
        monkeypatch.setattr(detect_slides, "_rss_now_mb", lambda: next(rss_iter))
        original_write_text = Path.write_text

        def recording_write_text(path, data, encoding=None):
            events.append("persist")
            return original_write_text(path, data, encoding=encoding)

        monkeypatch.setattr(Path, "write_text", recording_write_text)
        with collect() as metrics:
            run_detect_slides(tmp_path / "video.mp4", tmp_path, AppConfig())

        assert events == ["sampler_start", "document", "persist", "sampler_stop"]
        assert metrics.gauge_rss_peak_mb.value == expected_peak
        assert metrics.gauge_rss_after_mb.value == rss_values[1]

    def test_detector_work_exception_still_stops_sampler(self, tmp_path, monkeypatch):
        events = []
        self._patch_pipeline(monkeypatch, events, sampled_peak=150.0)
        rss_iter = iter([200.0, 175.0])
        monkeypatch.setattr(detect_slides, "_rss_now_mb", lambda: next(rss_iter))

        def failing_detect_changes(**kwargs):
            events.append("detector_work_exception")
            raise RuntimeError("detector work failed")

        def unexpected_persistence(path, data, encoding=None):
            events.append("persist")
            raise AssertionError("persistence must not execute")

        monkeypatch.setattr(detect_slides, "detect_changes", failing_detect_changes)
        monkeypatch.setattr(Path, "write_text", unexpected_persistence)
        with collect() as metrics, pytest.raises(
            RuntimeError, match="detector work failed"
        ):
            run_detect_slides(tmp_path / "video.mp4", tmp_path, AppConfig())

        assert events == [
            "sampler_start",
            "detector_work_exception",
            "sampler_stop",
        ]
        assert events.count("sampler_stop") == 1
        assert "document" not in events
        assert "persist" not in events
        assert metrics.gauge_rss_after_mb.value == 175.0
        assert metrics.gauge_rss_peak_mb.value == 200.0

    def test_persistence_exception_still_stops_sampler(self, tmp_path, monkeypatch):
        events = []
        self._patch_pipeline(monkeypatch, events, sampled_peak=90.0)
        rss_iter = iter([100.0, 120.0])
        monkeypatch.setattr(detect_slides, "_rss_now_mb", lambda: next(rss_iter))

        def failing_write_text(path, data, encoding=None):
            events.append("persist")
            raise OSError("persistence failed")

        monkeypatch.setattr(Path, "write_text", failing_write_text)
        with collect() as metrics, pytest.raises(OSError, match="persistence failed"):
            run_detect_slides(tmp_path / "video.mp4", tmp_path, AppConfig())

        assert events == ["sampler_start", "document", "persist", "sampler_stop"]
        assert events.count("sampler_stop") == 1
        assert metrics.gauge_rss_after_mb.value == 120.0
        assert metrics.gauge_rss_peak_mb.value == 120.0
