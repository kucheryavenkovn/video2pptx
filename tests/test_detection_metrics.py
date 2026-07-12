# FILE: tests/test_detection_metrics.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for DetectionRunMetrics schema, round-trip, measure(), collect()
#   SCOPE: Metrics typed round-trip, to_dict/from_dict/to_json/from_json, measure() timing,
#          InstrumentedIterator, zero-cost when inactive
#   DEPENDS: pytest, video2pptx.detection_metrics
#   LINKS: V-PERF-DETECT-BASELINE
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import time

from video2pptx.detection_metrics import (
    DetectionRunMetrics,
    InstrumentedIterator,
    collect,
    get,
    measure,
    reset,
    set_active,
)


class TestMetricsSchema:
    def test_to_dict_canonical(self):
        m = DetectionRunMetrics()
        m.timer_total.elapsed = 12.5
        m.counter_frames_decoded.value = 100
        m.gauge_peak_ram_mb.value = 512
        d = m.to_dict()

        assert "timers" in d
        assert "counters" in d
        assert "gauges" in d

        assert d["timers"]["total"] == 12.5
        assert d["counters"]["frames_decoded"] == 100
        assert d["gauges"]["peak_ram_mb"] == 512

        # No nested raw dicts
        assert "elapsed" not in str(d["timers"])
        assert "value" not in str(d["counters"])

    def test_round_trip(self):
        m = DetectionRunMetrics()
        m.timer_extract_features.elapsed = 3.14
        m.counter_slides_detected.value = 7
        m.counter_screenshots_written.value = 7
        m.gauge_rgb_transfer_bytes.value = 500_000_000

        d = m.to_dict()
        m2 = DetectionRunMetrics.from_dict(d)

        assert m2.timer_extract_features.elapsed == 3.14
        assert m2.counter_slides_detected.value == 7
        assert m2.counter_screenshots_written.value == 7
        assert m2.gauge_rgb_transfer_bytes.value == 500_000_000

    def test_json_round_trip(self):
        m = DetectionRunMetrics()
        m.timer_pass2_dedupe.elapsed = 0.25
        m.counter_frames_sampled.value = 42
        j = m.to_json()
        m2 = DetectionRunMetrics.from_json(j)

        assert m2.timer_pass2_dedupe.elapsed == 0.25
        assert m2.counter_frames_sampled.value == 42

    def test_from_dict_partial(self):
        """Partial dict merges with defaults."""
        d = {"timers": {"total": 5.0}, "counters": {}, "gauges": {}}
        m = DetectionRunMetrics.from_dict(d)
        assert m.timer_total.elapsed == 5.0
        assert m.timer_extract_features.elapsed == 0.0
        assert m.counter_frames_decoded.value == 0

    def test_defaults_are_zero(self):
        m = DetectionRunMetrics()
        d = m.to_dict()
        for section in ("timers", "counters", "gauges"):
            for val in d[section].values():
                assert val == 0 or val == 0.0, f"non-zero default: {section} = {val}"


class TestMeasure:
    def test_measure_records_time(self):
        with collect() as m:
            with measure("extract_features"):
                time.sleep(0.01)
        assert m.timer_extract_features.elapsed >= 0.009

    def test_measure_inactive_zero_overhead(self):
        # No active collector — measure should be near-instant
        t0 = time.perf_counter()
        for _ in range(1000):
            with measure("nothing"):
                pass
        elapsed = time.perf_counter() - t0
        assert elapsed < 0.1, f"1000 inactive measure() calls took {elapsed:.3f}s"

    def test_measure_unknown_timer_no_error(self):
        with collect() as m:
            with measure("nonexistent"):
                pass
        assert m is not None

    def test_measure_records_multiple_calls(self):
        with collect() as m:
            for _ in range(5):
                with measure("roi"):
                    time.sleep(0.001)
        assert m.timer_roi.elapsed >= 0.004

    def test_collect_context(self):
        assert get() is None
        with collect() as m:
            assert get() is m
            assert m is not None
        assert get() is None

    def test_collect_reentrant(self):
        """Nested collect() reuses the same collector."""
        with collect() as outer:
            assert get() is outer
            with collect() as inner:
                assert inner is outer
                assert get() is outer
            assert get() is outer
        assert get() is None

    def test_reset_and_set_active(self):
        assert get() is None
        m1 = reset()
        assert get() is m1
        set_active(None)
        assert get() is None


class TestInstrumentedIterator:
    def test_counts_items(self):
        counter = DetectionRunMetrics().counter_frames_sampled
        items = list(InstrumentedIterator(iter([1, 2, 3]), counter))
        assert items == [1, 2, 3]
        assert counter.value == 3

    def test_empty_iterator(self):
        counter = DetectionRunMetrics().counter_frames_sampled
        items = list(InstrumentedIterator(iter([]), counter))
        assert items == []
        assert counter.value == 0


class TestBenchmarkContract:
    """Live detection -> metrics artifact contract tests."""

    def test_metrics_collected_on_tiny_video(self, tmp_path):
        """Run detection on test fixture, verify all metric sections are populated."""
        from pathlib import Path

        from video2pptx.config import AppConfig
        from video2pptx.detect_slides import run_detect_slides

        video = Path(__file__).parent / "fixtures" / "test_slides.mp4"
        with collect() as m:
            run_detect_slides(video_path=video, out_dir=tmp_path, cfg=AppConfig())

        d = m.to_dict()

        # Schema structure
        assert "timers" in d
        assert "counters" in d
        assert "gauges" in d

        # Core timers must be > 0
        assert d["timers"]["total"] > 0, "timer_total must be > 0"
        assert d["timers"]["extract_features"] > 0, "timer_extract_features must be > 0"
        assert d["timers"]["roi"] >= 0
        assert d["timers"]["pass2_collect"] > 0, "timer_pass2_collect must be > 0"

        # Core counters
        assert d["counters"]["frames_sampled"] > 0, "counter_frames_sampled must be > 0"
        assert d["counters"]["features_full"] > 0, "counter_features_full must be > 0"
        assert d["counters"]["screenshots_written"] >= 1
        assert d["counters"]["slides_detected"] >= 1

        # RGB bytes must be > 0 when frames are decoded/transferred
        assert d["gauges"]["rgb_transfer_bytes"] > 0, "gauge_rgb_transfer_bytes must be > 0"

        # Frame decoded is backend-specific; if PyAV used, ndarray_conversions > 0
        if d["counters"]["ndarray_conversions"] == 0:
            # May be OpenCV backend; just check frames_decoded then
            assert d["counters"]["frames_decoded"] > 0

        # Screenshots on disk must match counter
        slides_dir = tmp_path / "slides"
        png_count = len(list(slides_dir.glob("*.png"))) if slides_dir.is_dir() else 0
        assert png_count == d["counters"]["screenshots_written"], (
            f"screenshots_written={d['counters']['screenshots_written']} "
            f"but found {png_count} PNGs on disk"
        )

    def test_metrics_json_serializable(self, tmp_path):
        """to_dict() output must be JSON-serializable."""
        import json
        from pathlib import Path

        from video2pptx.config import AppConfig
        from video2pptx.detect_slides import run_detect_slides

        video = Path(__file__).parent / "fixtures" / "test_slides.mp4"
        with collect() as m:
            run_detect_slides(video_path=video, out_dir=tmp_path, cfg=AppConfig())

        text = json.dumps(m.to_dict(), indent=2)
        loaded = json.loads(text)
        assert loaded["timers"]["total"] > 0
        assert loaded["counters"]["frames_sampled"] > 0
