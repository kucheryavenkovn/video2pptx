# FILE: src/video2pptx/application/ports/preview_analyzer.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Port for computing preview score data without mutating project or persistence.
#   SCOPE: PreviewOutput, PreviewAnalyzerPort Protocol
#   DEPENDS: none
#   LINKS: M-PORT-PREVIEW, V-REF-APP-SERVICES
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   PreviewOutput - immutable result with score timestamps, values, and video duration
#   PreviewAnalyzerPort - Protocol for computing preview scores from video
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add preview analyzer port and output DTO
# END_CHANGE_SUMMARY

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True, slots=True)
class PreviewOutput:
    score_timestamps: list[float] = field(default_factory=list)
    score_values: list[float] = field(default_factory=list)
    video_duration: float = 0.0


class PreviewAnalyzerPort(Protocol):
    """Port for computing quick preview score data from video."""

    def analyze(
        self,
        video_path: str,
        *,
        sample_fps: float,
        slide_roi: str,
        ignore_rois: list[str],
        threshold: float,
        min_stable_duration: float,
    ) -> PreviewOutput:
        ...
