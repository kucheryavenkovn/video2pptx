# FILE: src/video2pptx/application/ports/alignment.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Port for computing alignment plans without applying aggregate mutations.
#   SCOPE: AlignmentPlan, AlignmentPort Protocol
#   DEPENDS: video2pptx.domain.slide
#   LINKS: M-PORT-ALIGNMENT, V-REF-APP-SERVICES
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   AlignmentPlan - immutable plan with aligned intervals and metrics
#   AlignmentPort - Protocol for computing alignment from slides and subtitles
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add alignment port and plan DTO
# END_CHANGE_SUMMARY

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class AlignmentPlan:
    aligned_intervals: list[tuple[float, float]] = field(default_factory=list)
    boundaries_total: int = 0
    boundaries_moved: int = 0
    avg_shift: float = 0.0
    max_shift: float = 0.0
    cue_crossings_before: int = 0
    cue_crossings_after: int = 0
    report: dict[str, Any] = field(default_factory=dict)


class AlignmentPort(Protocol):
    """Port for computing an alignment plan from slide intervals and subtitles."""

    def compute_plan(
        self,
        intervals: list[tuple[float, float]],
        subtitles_path: str,
        *,
        max_shift_sec: float = 3.0,
        include_manual: bool = False,
        video_duration: float = 0.0,
    ) -> AlignmentPlan:
        ...
