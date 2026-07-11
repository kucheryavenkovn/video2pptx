# FILE: src/video2pptx/application/ports/slide_detector.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Port for detecting slide candidates from video without aggregate mutation.
#   SCOPE: DetectionOutput, SlideDetectorPort Protocol
#   DEPENDS: video2pptx.domain.slide
#   LINKS: M-PORT-DETECTOR, V-REF-APP-SERVICES
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   DetectionOutput - immutable result with slides, scores, and video duration
#   SlideDetectorPort - Protocol for detecting slides from video
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add slide detector port and output DTO
# END_CHANGE_SUMMARY

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from video2pptx.domain.slide import Slide


@dataclass(frozen=True, slots=True)
class DetectionOutput:
    slides: list[Slide] = field(default_factory=list)
    score_timestamps: list[float] = field(default_factory=list)
    score_values: list[float] = field(default_factory=list)
    video_duration: float = 0.0
    screenshots_dir: Path | None = None


class SlideDetectorPort(Protocol):
    """Port for detecting a complete slide candidate set from video."""

    def detect(
        self,
        video_path: str,
        out_dir: Path,
        *,
        sample_fps: float,
        slide_roi: str,
        ignore_rois: list[str],
        threshold: float,
        min_stable_duration: float,
        min_slide_duration: float,
        dedupe_enabled: bool,
    ) -> DetectionOutput:
        ...
