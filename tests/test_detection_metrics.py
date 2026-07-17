# FILE: tests/test_detection_metrics.py
# VERSION: 1.3.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for DetectionRunMetrics schema, round-trip, measure(), collect(),
#            RssSampler, InstrumentedIterator, benchmark contract invariants
#   SCOPE: Metrics typed round-trip, to_dict/from_dict/to_json/from_json, measure() timing,
#          RssSampler lifecycle (start/stop/peak), InstrumentedIterator counting,
#          benchmark invariants: features_full+features_quick==frames_sampled,
#          frames_decoded>=ndarray_conversions>=frames_sampled+pass2_frames_sampled,
#          RSS gauges, representative frame evidence, exact OpenCV/PyAV telemetry
#   DEPENDS: pytest, video2pptx.detection_metrics
#   LINKS: V-M-PERF-DETECT-BASELINE
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   TestOpenCVMetrics - exact successful-read and yielded-frame telemetry checks
#   TestPyAVMetrics - exact telemetry and normal/exception container cleanup checks
#   TestBenchmarkContract - end-to-end metrics invariants for the synthetic fixture
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.3.0 - Added deterministic PyAV decode-failure cleanup coverage
# END_CHANGE_SUMMARY

from __future__ import annotations

import time

import pytest

from video2pptx.detection_metrics import (
    DetectionRunMetrics,
    InstrumentedIterator,
    MetricsTimer,
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

    def test_new_timers_present_and_zero(self):
        m = DetectionRunMetrics()
        d = m.to_dict()
        assert "pass1_decode_or_frame_advance" in d["timers"]
        assert "pass2_decode_or_frame_advance" in d["timers"]
        assert "pass2_match_and_collect" in d["timers"]
        assert d["timers"]["pass1_decode_or_frame_advance"] == 0.0
        assert d["timers"]["pass2_decode_or_frame_advance"] == 0.0
        assert d["timers"]["pass2_match_and_collect"] == 0.0

    def test_round_trip_new_timers(self):
        m = DetectionRunMetrics()
        m.timer_pass1_decode_or_frame_advance.elapsed = 12.5
        m.timer_pass2_decode_or_frame_advance.elapsed = 8.3
        m.timer_pass2_match_and_collect.elapsed = 3.1
        d = m.to_dict()
        m2 = DetectionRunMetrics.from_dict(d)
        assert m2.timer_pass1_decode_or_frame_advance.elapsed == 12.5
        assert m2.timer_pass2_decode_or_frame_advance.elapsed == 8.3
        assert m2.timer_pass2_match_and_collect.elapsed == 3.1

    def test_historical_metrics_parses_without_new_timers(self):
        historical = {
            "timers": {
                "total": 100.0, "roi": 0.5, "extract_features": 40.0,
                "visual_distance": 0.3, "threshold": 0.2, "debounce": 0.01,
                "pass2_collect": 30.0, "pass2_dedupe": 5.0, "pass2_screenshots": 0.1,
            },
            "counters": {"frames_sampled": 100, "features_full": 100},
            "gauges": {"rss_before_mb": 0},
        }
        m = DetectionRunMetrics.from_dict(historical)
        assert m.timer_total.elapsed == 100.0
        assert m.timer_extract_features.elapsed == 40.0
        assert m.timer_pass1_decode_or_frame_advance.elapsed == 0.0
        assert m.timer_pass2_decode_or_frame_advance.elapsed == 0.0
        assert m.timer_pass2_match_and_collect.elapsed == 0.0
        assert m.counter_frames_sampled.value == 100

    def test_new_timers_json_round_trip(self):
        m = DetectionRunMetrics()
        m.timer_pass1_decode_or_frame_advance.elapsed = 7.5
        j = m.to_json()
        m2 = DetectionRunMetrics.from_json(j)
        assert m2.timer_pass1_decode_or_frame_advance.elapsed == 7.5
        assert m2.timer_pass2_decode_or_frame_advance.elapsed == 0.0


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

    def test_timer_accumulates(self):
        c = DetectionRunMetrics().counter_frames_sampled
        t = DetectionRunMetrics().timer_pass1_decode_or_frame_advance
        items = list(InstrumentedIterator(iter([10, 20, 30]), c, timer=t))
        assert items == [10, 20, 30]
        assert c.value == 3
        assert t.elapsed > 0

    def test_timer_excludes_consumer_time(self):
        import time
        c = DetectionRunMetrics().counter_frames_sampled
        t = MetricsTimer()
        it = InstrumentedIterator(iter([1, 2]), c, timer=t)
        consumer_total = 0.0
        for item in it:
            t0 = time.perf_counter()
            time.sleep(0.01)
            consumer_total += time.perf_counter() - t0
        assert c.value == 2
        assert t.elapsed > 0
        assert t.elapsed < consumer_total * 0.5, (
            f"timer ({t.elapsed:.4f}) should be much less than consumer "
            f"sleep ({consumer_total:.4f})"
        )

    def test_exhaustion_stopiteration_timed(self):
        c = DetectionRunMetrics().counter_frames_sampled
        t = MetricsTimer()

        class SlowExhaustion:
            def __init__(self):
                self.calls = 0
            def __iter__(self):
                return self
            def __next__(self):
                if self.calls >= 2:
                    import time
                    time.sleep(0.01)
                    raise StopIteration
                self.calls += 1
                return self.calls

        items = list(InstrumentedIterator(SlowExhaustion(), c, timer=t))
        assert items == [1, 2]
        assert c.value == 2
        assert t.elapsed > 0.009, f"expected exhaustion time, got {t.elapsed:.4f}"

    def test_exception_propagates_and_timer_accumulates(self):
        c = DetectionRunMetrics().counter_frames_sampled
        t = MetricsTimer()

        class FailingIterator:
            def __init__(self):
                self.calls = 0
            def __iter__(self):
                return self
            def __next__(self):
                self.calls += 1
                if self.calls == 2:
                    import time
                    time.sleep(0.01)
                    raise ValueError("boom")
                return self.calls

        it = InstrumentedIterator(FailingIterator(), c, timer=t)
        with pytest.raises(ValueError, match="boom"):
            list(it)
        assert c.value == 1
        assert t.elapsed > 0.009, f"expected exception advancement time, got {t.elapsed:.4f}"

    def test_counter_increments_only_successful_yield(self):
        c = DetectionRunMetrics().counter_frames_sampled
        t = MetricsTimer()

        class Alternating:
            def __init__(self):
                self.idx = 0
            def __iter__(self):
                return self
            def __next__(self):
                self.idx += 1
                if self.idx == 3:
                    raise RuntimeError("fail")
                return self.idx

        it = InstrumentedIterator(Alternating(), c, timer=t)
        collected = []
        try:
            while True:
                collected.append(next(it))
        except RuntimeError:
            pass
        assert collected == [1, 2]
        assert c.value == 2
        assert t.elapsed > 0


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

    def test_decode_failure_closes_container_and_propagates(self, monkeypatch):
        import sys
        from types import SimpleNamespace

        from video2pptx.backends import pyav_backend

        class FakePacket:
            def decode(self):
                raise RuntimeError("decode failed")

        class FakeContainer:
            def __init__(self):
                stream = SimpleNamespace(average_rate=10.0)
                self.streams = SimpleNamespace(video=[stream])
                self.close_calls = 0

            def demux(self, stream):
                return [FakePacket()]

            def close(self):
                self.close_calls += 1

        container = FakeContainer()
        fake_av = SimpleNamespace(open=lambda path, hwaccel=None: container)
        monkeypatch.setitem(sys.modules, "av", fake_av)
        monkeypatch.setattr(pyav_backend, "_pick_hw_device", lambda: None)

        with pytest.raises(RuntimeError, match="decode failed"):
            list(pyav_backend.pyav_iter_frames("unused.mp4", sample_fps=2.0))

        assert container.close_calls == 1


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

    def test_pass1_decode_timer_positive(self, tmp_path):
        m = self._run_detect(tmp_path)
        assert m.timer_pass1_decode_or_frame_advance.elapsed > 0

    def test_pass2_decode_timer_positive(self, tmp_path):
        m = self._run_detect(tmp_path)
        assert m.timer_pass2_decode_or_frame_advance.elapsed > 0

    def test_pass2_match_and_collect_timer_positive(self, tmp_path):
        m = self._run_detect(tmp_path)
        assert m.timer_pass2_match_and_collect.elapsed > 0

    def test_new_timers_do_not_crash_full_detect(self, tmp_path):
        m = self._run_detect(tmp_path)
        d = m.to_dict()
        assert d["timers"]["pass1_decode_or_frame_advance"] > 0
        assert d["timers"]["pass2_decode_or_frame_advance"] > 0
        assert d["timers"]["pass2_match_and_collect"] > 0


class TestBenchmarkAccounting:
    """Tests for benchmark stage accounting — non-overlapping regions."""

    @staticmethod
    def _load_benchmark_module():
        import importlib.util
        import sys
        from pathlib import Path
        mod_path = Path(__file__).resolve().parent.parent / "tools" / "benchmark_detect.py"
        spec = importlib.util.spec_from_file_location("benchmark_detect", mod_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["benchmark_detect"] = mod
        spec.loader.exec_module(mod)
        return mod

    def test_pass2_collect_excluded_from_canonical_if_children_present(self):
        mod = self._load_benchmark_module()
        children = {"pass2_decode_or_frame_advance", "pass2_match_and_collect"}
        parent = "pass2_collect"
        assert parent not in mod.STAGE_NAMES, (
            f"STAGE_NAMES contains '{parent}' which would double-count when "
            f"its children {children} are also present"
        )
        for child in children:
            assert child in mod.STAGE_NAMES, (
                f"STAGE_NAMES missing child timer '{child}'"
            )
        assert "pass2_dedupe" in mod.STAGE_NAMES
        assert "pass2_screenshots" in mod.STAGE_NAMES

    def test_canonical_stages_are_pairwise_non_overlapping(self):
        mod = self._load_benchmark_module()
        timers = {
            "pass1_decode_or_frame_advance": 10.0,
            "roi": 1.0,
            "extract_features": 20.0,
            "visual_distance": 0.5,
            "threshold": 0.2,
            "debounce": 0.05,
            "pass2_decode_or_frame_advance": 8.0,
            "pass2_match_and_collect": 5.0,
            "pass2_dedupe": 2.0,
            "pass2_screenshots": 0.3,
        }
        detect_elapsed = sum(timers.values()) + 3.0
        accounting = mod.compute_stage_accounting(timers, detect_elapsed)
        expected_total = sum(timers.values())
        assert abs(accounting["measured_stage_total"] - expected_total) < 1e-9
        residual = detect_elapsed - expected_total
        assert abs(accounting["residual_seconds"] - residual) < 1e-9

    def test_pass2_collect_legacy_not_in_measured_total(self):
        mod = self._load_benchmark_module()
        timers = {
            "pass1_decode_or_frame_advance": 10.0,
            "roi": 1.0,
            "extract_features": 20.0,
            "visual_distance": 0.5,
            "threshold": 0.2,
            "debounce": 0.05,
            "pass2_decode_or_frame_advance": 8.0,
            "pass2_match_and_collect": 5.0,
            "pass2_dedupe": 2.0,
            "pass2_screenshots": 0.3,
            "pass2_collect": 13.0,
        }
        detect_elapsed = sum(timers.values()) + 3.0
        accounting = mod.compute_stage_accounting(timers, detect_elapsed)
        expected_total = sum(timers[stage] for stage in mod.STAGE_NAMES)
        assert abs(accounting["measured_stage_total"] - expected_total) < 1e-9
        assert accounting["measured_stage_total"] < sum(timers.values()), (
            "legacy pass2_collect must NOT be added to measured_stage_total"
        )
