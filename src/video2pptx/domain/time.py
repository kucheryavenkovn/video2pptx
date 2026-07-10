# FILE: src/video2pptx/domain/time.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Immutable validated time interval for slide segments.
#   SCOPE: TimeInterval with contains, overlaps, shift, with_start, with_end, clamp
#   DEPENDS: video2pptx.domain.errors
#   LINKS: M-DOMAIN-VALUE
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   TimeInterval - frozen validated start/end pair with interval algebra
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Initial TimeInterval implementation
# END_CHANGE_SUMMARY

from __future__ import annotations

import math
from dataclasses import dataclass

from video2pptx.domain.errors import ValidationError

TIME_EPSILON: float = 1e-6


@dataclass(frozen=True, slots=True)
class TimeInterval:
    """Immutable half-open time interval [start, end).

    Invariants:
        - start is a finite number
        - end is a finite number
        - start >= 0
        - end > start
    """

    start: float
    end: float

    def __post_init__(self) -> None:
        if math.isnan(self.start) or math.isnan(self.end):
            raise ValidationError("TimeInterval bounds must not be NaN")
        if math.isinf(self.start) or math.isinf(self.end):
            raise ValidationError("TimeInterval bounds must be finite")
        if self.start < 0:
            raise ValidationError(
                f"TimeInterval start must be >= 0, got {self.start}"
            )
        if self.end <= self.start:
            raise ValidationError(
                f"TimeInterval end ({self.end}) must be > start ({self.start})"
            )

    @property
    def duration(self) -> float:
        return self.end - self.start

    def contains(self, timestamp: float) -> bool:
        """Return True if timestamp is within [start, end]."""
        return self.start <= timestamp <= self.end

    def overlaps(self, other: TimeInterval) -> bool:
        """Return True if this interval shares any time with *other*."""
        return self.start < other.end and other.start < self.end

    def touches(self, other: TimeInterval, tolerance: float = TIME_EPSILON) -> bool:
        """Return True if intervals are adjacent within *tolerance*."""
        return (
            abs(self.end - other.start) <= tolerance
            or abs(other.end - self.start) <= tolerance
        )

    def intersection(self, other: TimeInterval) -> TimeInterval | None:
        """Return the overlapping portion, or None if disjoint."""
        start = max(self.start, other.start)
        end = min(self.end, other.end)
        if end > start:
            return TimeInterval(start, end)
        return None

    def shift(self, delta: float) -> TimeInterval:
        """Return a new interval shifted by *delta*."""
        return TimeInterval(self.start + delta, self.end + delta)

    def with_start(self, value: float) -> TimeInterval:
        """Return a new interval with the start boundary changed."""
        return TimeInterval(value, self.end)

    def with_end(self, value: float) -> TimeInterval:
        """Return a new interval with the end boundary changed."""
        return TimeInterval(self.start, value)

    def clamp(
        self,
        lower: float = 0.0,
        upper: float | None = None,
    ) -> TimeInterval:
        """Return a new interval clamped to [lower, upper]."""
        start = max(self.start, lower)
        end = self.end
        if upper is not None:
            end = min(self.end, upper)
        if end <= start:
            raise ValidationError(
                f"Clamp produced invalid interval [{start}, {end})"
            )
        return TimeInterval(start, end)
