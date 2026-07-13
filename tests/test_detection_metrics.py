# FILE: tests/test_detection_metrics.py
# VERSION: 1.2.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for DetectionRunMetrics schema, round-trip, measure(), collect(),
#            RssSampler, InstrumentedIterator, benchmark contract invariants
#   SCOPE: Metrics typed round-trip, to_dict/from_dict/to_json/from_json, measure() timing,
#          RssSampler lifecycle (start/stop/peak), InstrumentedIterator counting,
#          benchmark invariants: features_full+features_quick==frames_sampled,
#          frames_decoded>=ndarray_conversions>=frames_sampled+pass2_frames_sampled,
#          RSS gauges, representative frame evidence, exact OpenCV/PyAV telemetry
#   DEPENDS: pytest, video2pptx.detection_metrics
#   LINKS: V-PERF-DETECT-BASELINE
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   TestOpenCVMetrics - exact successful-read and yielded-frame telemetry checks
#   TestPyAVMetrics - exact decode, conversion, transfer, and keyframe telemetry checks
#   TestBenchmarkContract - end-to-end metrics invariants for the synthetic fixture
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.2.0 - Added exact OpenCV and PyAV telemetry regression coverage
# END_CHANGE_SUMMARY

from __future__ import annotations

import time

import pytest

from video2pptx.detection_metrics import (
    DetectionRunMetrics,
    InstrumentedIterator,
    RssSampler,
    collect,
    get,
    measure,
    reset,
    set_active,
)


def _psutil_available() -> bool:
    try:
        import psutil
        psutil.Process()
        return True
    except Exception:
        return False


class TestMetricsSchema:
    def test_to_dict_canonical(self):
        m = DetectionRunMetrics()
        m.timer_total.elapsed = 12.5
        m.counter_frames_decoded.value = 100
        m.gauge_rss_before_mb.value = 512
        d = m.to_dict()
        assert "timers" in d and "counters" in d and "gauges" in d
        assert d["timers"]["total"] == 12.5
        assert d["counters"]["frames_decoded"] == 100
        assert d["gauges"]["rss_before_mb"] == 512
        assert "elapsed" not in str(d["timers"])

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
                assert val == 0 or val == 0.0

    def test_new_fields_present(self):
        m = DetectionRunMetrics()
        d = m.to_dict()
        assert "pass2_frames_sampled" in d["counters"]
        assert "representative_frame_bytes" in d["counters"]
        assert "rss_before_mb" in d["gauges"]
        assert "rss_peak_mb" in d["gauges"]
        assert "rss_after_mb" in d["gauges"]
        assert "peak_ram_mb" not in d["gauges"]


class TestMeasure:
    def test_measure_records_time(self):
        with collect() as m:
            with measure("extract_features"):
                time.sleep(0.01)
        assert m.timer_extract_features.elapsed >= 0.009

    def test_measure_inactive_zero_overhead(self):
        t0 = time.perf_counter()
        for _ in range(1000):
            with measure("nothing"):
                pass
        assert time.perf_counter() - t0 < 0.1

    def test_measure_unknown_timer_no_error(self):
        with collect():
            with measure("nonexistent"):
                pass

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
        assert get() is None

    def test_collect_reentrant(self):
        with collect() as outer:
            with collect() as inner:
                assert inner is outer
        assert get() is None

    def test_reset_and_set_active(self):
        m1 = reset()
        assert get() is m1
        set_active(None)
        assert get() is None


class TestRssSampler:
    def test_lifecycle(self):
        if not _psutil_available():
            pytest.skip("psutil not available")
        sampler = RssSampler(interval=0.05)
        sampler.start()
        time.sleep(0.15)
        sampler.stop()
        assert sampler.peak_mb > 0

    def test_stop_before_start_no_error(self):
        sampler = RssSampler()
        sampler.stop()
        assert sampler.peak_mb == 0

    def test_never_started_peak_zero(self):
        sampler = RssSampler()
        assert sampler.peak_mb == 0


class TestInstrumentedIterator:
    def test_counts_items(self):
        c = DetectionRunMetrics().counter_frames_sampled
        items = list(InstrumentedIterator(iter([1, 2, 3]), c))
        assert items == [1, 2, 3]
        assert c.value == 3

    def test_empty_iterator(self):
        c = DetectionRunMetrics().counter_frames_sampled
        items = list(InstrumentedIterator(iter([]), c))
        assert items == []
        assert c.value == 0


class TestOpenCVMetrics:
    def test_successful_source_reads_counted_once(self, monkeypatch):
        import numpy as np

        from video2pptx.backends import opencv_backend

        source_frames = [np.zeros((2, 3, 3), dtype=np.uint8) for _ in range(7)]

        class FakeCapture:
            def __init__(self, _path):
                self.frames = iter(source_frames)

            def isOpened(self):
                return True

            def get(self, prop):
                return 10.0 if prop == opencv_backend.cv2.CAP_PROP_FPS else 0.0

            def read(self):
                return next(((True, frame) for frame in self.frames), (False, None))

            def release(self):
                pass

        monkeypatch.setattr(opencv_backend.cv2, "VideoCapture", FakeCapture)
        with collect() as metrics:
            sampled = list(opencv_backend.opencv_iter_frames("unused.mp4", sample_fps=2.0))

        assert metrics.counter_frames_decoded.value == len(source_frames)
        assert metrics.counter_ndarray_conversions.value == len(sampled) == 2
        assert metrics.gauge_rgb_transfer_bytes.value == sum(
            frame.image.nbytes for frame in sampled
        )


class TestPyAVMetrics:
    @staticmethod
    def _install_fake_av(monkeypatch, key_frames):
        import sys
        from types import SimpleNamespace

        import numpy as np

        from video2pptx.backends import pyav_backend

        class FakeFrame:
            def __init__(self, key_frame):
                self.key_frame = key_frame
                self.conversions = 0

            def to_ndarray(self, format):
                assert format == "rgb24"
                self.conversions += 1
                return np.zeros((2, 3, 3), dtype=np.uint8)

        frames = [FakeFrame(key_frame) for key_frame in key_frames]

        class FakePacket:
            def decode(self):
                return frames

        class FakeContainer:
            def __init__(self):
                stream = SimpleNamespace(average_rate=10.0)
                self.streams = SimpleNamespace(video=[stream])
                self.closed = False

            def demux(self, stream):
                return [FakePacket()]

            def close(self):
                self.closed = True

        container = FakeContainer()
        fake_av = SimpleNamespace(open=lambda path, hwaccel=None: container)
        monkeypatch.setitem(sys.modules, "av", fake_av)
        monkeypatch.setattr(pyav_backend, "_pick_hw_device", lambda: None)
        return pyav_backend, frames, container

    @pytest.mark.parametrize(
        ("keyframes_only", "key_frames", "expected_yields"),
        [(False, [True] * 7, 2), (True, [True, False, True, False], 2)],
    )
    def test_exact_decode_conversion_and_transfer_metrics(
        self, monkeypatch, keyframes_only, key_frames, expected_yields
    ):
        backend, frames, container = self._install_fake_av(monkeypatch, key_frames)
        with collect() as metrics:
            sampled = list(
                backend.pyav_iter_frames(
                    "unused.mp4", sample_fps=2.0, keyframes_only=keyframes_only
                )
            )

        assert metrics.counter_frames_decoded.value == len(frames)
        assert metrics.counter_ndarray_conversions.value == len(sampled) == expected_yields
        assert sum(frame.conversions for frame in frames) == expected_yields
        assert metrics.gauge_rgb_transfer_bytes.value == sum(
            frame.image.nbytes for frame in sampled
        )
        assert container.closed


class TestBenchmarkContract:
    def _run_detect(self, tmp_path, cfg_override=None):
        from pathlib import Path

        from video2pptx.config import AppConfig
        from video2pptx.detect_slides import run_detect_slides
        video = Path(__file__).parent / "fixtures" / "test_slides.mp4"
        cfg = cfg_override() if callable(cfg_override) else AppConfig()
        with collect() as m:
            run_detect_slides(video_path=video, out_dir=tmp_path, cfg=cfg)
        return m

    def test_metrics_collected_on_tiny_video(self, tmp_path):
        m = self._run_detect(tmp_path)
        d = m.to_dict()
        psutil_ok = _psutil_available()

        assert "timers" in d and "counters" in d and "gauges" in d
        assert d["timers"]["total"] > 0
        assert d["timers"]["extract_features"] > 0

        fs = d["counters"]["frames_sampled"]
        ffull = d["counters"]["features_full"]
        fquick = d["counters"]["features_quick"]
        assert fs > 0
        assert ffull + fquick == fs

        assert d["counters"]["pass2_frames_sampled"] > 0

        fd = d["counters"]["frames_decoded"]
        nc = d["counters"]["ndarray_conversions"]
        assert fd >= nc
        assert nc >= fs + d["counters"]["pass2_frames_sampled"]

        assert d["counters"]["representative_frames"] > 0
        assert d["counters"]["representative_frame_bytes"] > 0

        if psutil_ok:
            assert d["gauges"]["rss_before_mb"] > 0
            assert d["gauges"]["rss_peak_mb"] >= d["gauges"]["rss_before_mb"]
            assert d["gauges"]["rss_peak_mb"] >= d["gauges"]["rss_after_mb"]
        else:
            assert d["gauges"]["rss_before_mb"] == 0

        assert d["counters"]["screenshots_written"] >= 1
        assert d["counters"]["slides_detected"] >= 1
        assert d["gauges"]["rgb_transfer_bytes"] > 0

        slides_dir = tmp_path / "slides"
        png_count = len(list(slides_dir.glob("*.png"))) if slides_dir.is_dir() else 0
        assert png_count == d["counters"]["screenshots_written"]

    def test_metrics_json_serializable(self, tmp_path):
        import json
        m = self._run_detect(tmp_path)
        loaded = json.loads(json.dumps(m.to_dict()))
        assert loaded["timers"]["total"] > 0
        assert loaded["counters"]["frames_sampled"] > 0

    def test_invariant_no_dedup(self, tmp_path):
        from video2pptx.config import AppConfig
        def cfg_no_dedup():
            c = AppConfig()
            c.detection.dedupe_enabled = False
            return c
        m = self._run_detect(tmp_path, cfg_no_dedup)
        d = m.to_dict()
        fs = d["counters"]["frames_sampled"]
        assert d["counters"]["features_full"] + d["counters"]["features_quick"] == fs
