# FILE: src/video2pptx/adapters/legacy_aligner.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Wrap old align_slides_to_subtitles behind AlignmentPort
#   SCOPE: LegacyAligner.compute_plan — compute aligned intervals from interval pairs
#   DEPENDS: video2pptx.application.ports.alignment, video2pptx.auto_align,
#            video2pptx.models
#   LINKS: M-PORT-ALIGNMENT, M-ADAPTERS
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   LegacyAligner - adapt legacy subtitle alignment to AlignmentPort
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Complete Phase 16 MCP port adapter integration
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path

from video2pptx.application.ports.alignment import AlignmentPlan, AlignmentPort
from video2pptx.auto_align import align_slides_to_subtitles
from video2pptx.models import SlideSegment


class LegacyAligner(AlignmentPort):
    """Compute alignment plan using old align_slides_to_subtitles.

    Does NOT write any files. The returned AlignmentPlan carries the
    adjusted interval pairs and metrics for the service to apply.
    """

    def compute_plan(
        self,
        intervals: list[tuple[float, float]],
        subtitles_path: str,
        *,
        max_shift_sec: float = 3.0,
        include_manual: bool = False,
        video_duration: float = 0.0,
    ) -> AlignmentPlan:
        slides = [
            SlideSegment(
                uid=f"align-auto-{i}",
                index=i + 1,
                start=start,
                end=end,
                duration=end - start,
                representative_timestamp=(start + end) / 2,
                manual=False,
            )
            for i, (start, end) in enumerate(intervals)
        ]

        report = align_slides_to_subtitles(
            slides=slides,
            subtitles_path=Path(subtitles_path),
            max_shift_sec=max_shift_sec,
            dry_run=False,
            include_manual=include_manual,
            video_duration=video_duration,
        )

        aligned_intervals = [(s.start, s.end) for s in slides]

        return AlignmentPlan(
            aligned_intervals=aligned_intervals,
            boundaries_total=report.boundaries_total,
            boundaries_moved=report.boundaries_moved,
            avg_shift=report.avg_shift,
            max_shift=report.max_shift,
            cue_crossings_before=report.cue_crossings_before,
            cue_crossings_after=report.cue_crossings_after,
            report=report.to_dict(),
        )
