# FILE: src/video2pptx/detection_metrics.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Low-overhead aggregated performance telemetry for detector runs.
#   SCOPE: DetectionRunMetrics — typed timers, counters, gauges; JSON-serializable
#          canonical {timers/ counters/ gauges/} schema; zero-cost when disabled.
#   DEPENDS: time, dataclasses, json
#   LINKS: M-DETECT-METRICS, V-PERF-DETECT-BASELINE
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   DetectionRunMetrics - aggregated timers/counters/gauges with canonical to_dict/from_dict
#   RssSampler - background daemon thread that tracks peak RSS
#   measure - optional zero-overhead context manager
#   collect - context manager to activate collection
#   reset, get, set_active - global collector API
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 — Canonical {timers/counters/gauges} schema; measure() context manager;
#                from_dict round-trip; gauge_rgb_transfer_bytes, gauge_peak_ram_mb,
#                counter_ndarray_conversions, counter_representative_frames
# END_CHANGE_SUMMARY

from __future__ import annotations

import json
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field, fields
from typing import Any

# =========================================================================
# Primitive wrappers
# =========================================================================




class RssSampler:
    def __init__(self, interval: float = 0.2):
        self._interval = interval
        self._peak = 0.0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._process = None

    def start(self) -> None:
        try:
            import psutil
            self._process = psutil.Process()
        except Exception:
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                rss = self._process.memory_info().rss / 1_000_000
                if rss > self._peak:
                    self._peak = rss
            except Exception:
                pass
            self._stop.wait(self._interval)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    @property
    def peak_mb(self) -> float:
        return self._peak


@dataclass
class MetricsTimer:
    elapsed: float = 0.0

    def __iadd__(self, delta: float) -> MetricsTimer:
        self.elapsed += delta
        return self


@dataclass
class MetricsCounter:
    value: int = 0

    def increment(self, n: int = 1) -> None:
        self.value += n


@dataclass
class MetricsGauge:
    value: float | int = 0

    def set(self, v: float | int) -> None:
        self.value = v


# =========================================================================
# Canonical field metadata — maps Python attr name → JSON key
# =========================================================================

_TIMER_PREFIX = "timer_"
_COUNTER_PREFIX = "counter_"
_GAUGE_PREFIX = "gauge_"


def _canonical_key(attr: str, prefix: str) -> str:
    return attr[len(prefix) :]


def _attr_name(key: str, prefix: str) -> str:
    return f"{prefix}{key}"


# =========================================================================
# Main metrics container
# =========================================================================


@dataclass
class DetectionRunMetrics:
    # Timers (seconds)
    timer_total: MetricsTimer = field(default_factory=MetricsTimer)
    timer_decoder_wait: MetricsTimer = field(default_factory=MetricsTimer)
    timer_roi: MetricsTimer = field(default_factory=MetricsTimer)
    timer_extract_features: MetricsTimer = field(default_factory=MetricsTimer)
    timer_visual_distance: MetricsTimer = field(default_factory=MetricsTimer)
    timer_threshold: MetricsTimer = field(default_factory=MetricsTimer)
    timer_debounce: MetricsTimer = field(default_factory=MetricsTimer)
    timer_pass2_collect: MetricsTimer = field(default_factory=MetricsTimer)
    timer_pass2_dedupe: MetricsTimer = field(default_factory=MetricsTimer)
    timer_pass2_screenshots: MetricsTimer = field(default_factory=MetricsTimer)

    # Counters
    counter_frames_decoded: MetricsCounter = field(default_factory=MetricsCounter)
    counter_frames_sampled: MetricsCounter = field(default_factory=MetricsCounter)
    counter_features_full: MetricsCounter = field(default_factory=MetricsCounter)
    counter_features_quick: MetricsCounter = field(default_factory=MetricsCounter)
    counter_slides_detected: MetricsCounter = field(default_factory=MetricsCounter)
    counter_screenshots_written: MetricsCounter = field(default_factory=MetricsCounter)
    counter_ndarray_conversions: MetricsCounter = field(default_factory=MetricsCounter)
    counter_representative_frames: MetricsCounter = field(default_factory=MetricsCounter)
    counter_pass2_frames_sampled: MetricsCounter = field(default_factory=MetricsCounter)
    counter_representative_frame_bytes: MetricsCounter = field(default_factory=MetricsCounter)

    # Gauges
    gauge_rgb_transfer_bytes: MetricsGauge = field(default_factory=MetricsGauge)
    gauge_rss_before_mb: MetricsGauge = field(default_factory=MetricsGauge)
    gauge_rss_peak_mb: MetricsGauge = field(default_factory=MetricsGauge)
    gauge_rss_after_mb: MetricsGauge = field(default_factory=MetricsGauge)
    gauge_peak_in_flight: MetricsGauge = field(default_factory=MetricsGauge)

    # ------------------------------------------------------------------
    # Schema conversion
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"timers": {}, "counters": {}, "gauges": {}}
        for f in fields(self):
            val = getattr(self, f.name)
            if f.name.startswith(_TIMER_PREFIX):
                result["timers"][_canonical_key(f.name, _TIMER_PREFIX)] = val.elapsed
            elif f.name.startswith(_COUNTER_PREFIX):
                result["counters"][_canonical_key(f.name, _COUNTER_PREFIX)] = val.value
            elif f.name.startswith(_GAUGE_PREFIX):
                result["gauges"][_canonical_key(f.name, _GAUGE_PREFIX)] = val.value
        return result

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> DetectionRunMetrics:
        kwargs: dict[str, Any] = {}
        sections = {"timers": _TIMER_PREFIX, "counters": _COUNTER_PREFIX, "gauges": _GAUGE_PREFIX}
        for section_name, prefix in sections.items():
            section = data.get(section_name, {})
            if not isinstance(section, dict):
                continue
            for key, val in section.items():
                attr = _attr_name(key, prefix)
                if prefix == _TIMER_PREFIX:
                    kwargs[attr] = MetricsTimer(elapsed=float(val))
                elif prefix == _COUNTER_PREFIX:
                    kwargs[attr] = MetricsCounter(value=int(val))
                elif prefix == _GAUGE_PREFIX:
                    kwargs[attr] = MetricsGauge(
                        value=float(val) if isinstance(val, float) else int(val)
                    )
        return cls(**kwargs)

    @classmethod
    def from_json(cls, text: str) -> DetectionRunMetrics:
        return cls.from_dict(json.loads(text))


# =========================================================================
# Global zero-cost collector
# =========================================================================

_collector: DetectionRunMetrics | None = None


def reset() -> DetectionRunMetrics:
    global _collector
    m = DetectionRunMetrics()
    _collector = m
    return m


def get() -> DetectionRunMetrics | None:
    return _collector


def set_active(metrics: DetectionRunMetrics | None) -> None:
    global _collector
    _collector = metrics


@contextmanager
def collect() -> Generator[DetectionRunMetrics, None, None]:
    if _collector is not None:
        yield _collector
        return
    m = reset()
    try:
        yield m
    finally:
        set_active(None)


# =========================================================================
# Low-overhead timer helper
# =========================================================================


@contextmanager
def measure(name: str) -> Generator[None, None, None]:
    metrics = _collector
    if metrics is None:
        yield
        return
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        timer = getattr(metrics, f"timer_{name}", None)
        if timer is not None:
            timer.elapsed += elapsed


# =========================================================================
# Instrumented iterator wrapper
# =========================================================================


class InstrumentedIterator:
    def __init__(self, iterator, counter: MetricsCounter):
        self._it = iter(iterator)
        self._counter = counter

    def __iter__(self):
        return self

    def __next__(self):
        item = next(self._it)
        self._counter.increment()
        return item
