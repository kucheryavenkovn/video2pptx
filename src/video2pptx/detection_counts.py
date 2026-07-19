# FILE: src/video2pptx/detection_counts.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Candidate→final slide stage counts and score-distribution diagnostics
#   SCOPE: DetectionCounts, score_distribution_summary, format helpers
#   DEPENDS: numpy (optional for percentiles)
#   LINKS: M-DETECT-SLIDES, Phase-21 Wave 6
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   DetectionCounts - stage counters from sample to screenshots
#   score_distribution_summary - min/median/p90/p95/p99/max for auto-threshold diagnostics
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Phase 21 Wave 6 observability model
# END_CHANGE_SUMMARY

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class DetectionCounts:
    """Pipeline stage counts separating candidate changes from final slides."""

    sampled_frames: int = 0
    candidate_changes: int = 0
    debounced_changes: int = 0
    segments_before_min_duration: int = 0
    segments_after_min_duration: int = 0
    segments_before_dedupe: int = 0
    segments_after_dedupe: int = 0
    screenshots_written: int = 0
    # Pass 2 streaming metrics (Wave 7)
    pass2_decoded_frames: int = 0
    pass2_target_count: int = 0
    pass2_captured_count: int = 0
    pass2_missing_count: int = 0
    pass2_peak_live_fullres_frames: int = 0
    pass2_peak_live_frame_bytes: int = 0
    pass2_wall_seconds: float = 0.0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def score_distribution_summary(scores: list[float]) -> dict[str, float | int]:
    """Summarize visual-distance scores for auto-threshold diagnostics (no algorithm change)."""
    if not scores:
        return {
            "score_count": 0,
            "score_min": 0.0,
            "score_median": 0.0,
            "score_p90": 0.0,
            "score_p95": 0.0,
            "score_p99": 0.0,
            "score_max": 0.0,
        }
    import numpy as np

    arr = np.asarray(scores, dtype=np.float64)
    return {
        "score_count": int(arr.size),
        "score_min": float(np.min(arr)),
        "score_median": float(np.median(arr)),
        "score_p90": float(np.percentile(arr, 90)),
        "score_p95": float(np.percentile(arr, 95)),
        "score_p99": float(np.percentile(arr, 99)),
        "score_max": float(np.max(arr)),
    }
