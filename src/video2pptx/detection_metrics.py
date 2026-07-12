# FILE: src/video2pptx/detection_metrics.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Low-overhead aggregated performance telemetry for detector runs.
#   SCOPE: DetectionRunMetrics — typed timers, counters, gauges; JSON-serializable; zero-cost when disabled.
#   DEPENDS: time, dataclasses, json
#   LINKS: M-DETECT-METRICS, V-PERF-DETECT-BASELINE
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   DetectionRunMetrics - aggregated timers, counters, gauges for detection pass
#   MetricsTimer - context manager for timing blocks
#   MetricsCollector - optional collector to avoid overhead when not benchmarking
# END_MODULE_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Initial aggregated detection telemetry
# END_CHANGE_SUMMARY

from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class MetricsTimer:
    """Named elapsed time accumulator in seconds."""

    elapsed: float = 0.0

    def __iadd__(self, delta: float) -> MetricsTimer:
        self.elapsed += delta
        return self


@dataclass
class MetricsCounter:
    """Named integer counter."""

    value: int = 0

    def increment(self, n: int = 1) -> None:
        self.value += n


@dataclass
class MetricsGauge:
    """Named gauge (last-set value)."""

    value: float | int = 0

    def set(self, v: float | int) -> None:
        self.value = v


@dataclass
class DetectionRunMetrics:
    """Aggregated telemetry for one detection run.

    Thread-safe for concurrent timer/counter updates when used with external locking.
    """

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

    # Gauges
    gauge_peak_ram_mb: MetricsGauge = field(default_factory=MetricsGauge)
    gauge_peak_in_flight: MetricsGauge = field(default_factory=MetricsGauge)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    @classmethod
    def from_dict(cls, data: dict) -> DetectionRunMetrics:
        return cls(**data)


# -- optional zero-cost wrapper ------------------------------------------------

_COLLECTOR: DetectionRunMetrics | None = None


def reset() -> DetectionRunMetrics:
    """Create a fresh collector and set it as the global collector."""
    global _COLLECTOR
    _COLLECTOR = DetectionRunMetrics()
    return _COLLECTOR


def get() -> DetectionRunMetrics | None:
    """Return the global collector, or None if no collection is active."""
    return _COLLECTOR


def set_active(metrics: DetectionRunMetrics | None) -> None:
    """Enable or disable the global collector."""
    global _COLLECTOR
    _COLLECTOR = metrics


@contextmanager
def collect() -> DetectionRunMetrics:
    """Context manager that creates, activates, and returns a fresh collector.

    Usage::

        with collect() as m:
            run_detection(...)
        print(m.to_json())
    """
    m = reset()
    try:
        yield m
    finally:
        set_active(None)


# -- helper for counting anything callable --------------------------------------


class InstrumentedIterator:
    """Wrapper around an iterator to count yielded items."""

    def __init__(self, iterator, counter: MetricsCounter):
        self._it = iter(iterator)
        self._counter = counter

    def __iter__(self):
        return self

    def __next__(self):
        item = next(self._it)
        self._counter.increment()
        return item
