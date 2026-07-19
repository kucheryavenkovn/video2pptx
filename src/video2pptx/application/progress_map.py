# FILE: src/video2pptx/application/progress_map.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Map local stage progress (0–100) into a global monotonic Detect progress scale
#   SCOPE: map_stage_progress, DETECT_STAGE_RANGES helpers (Qt-free)
#   DEPENDS: none
#   LINKS: M-APP-DETECT, Phase-21 Wave 3
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   map_stage_progress - linear map local 0–100 into [stage_start, stage_end]
#   DETECT_STAGE_RANGES - named global ranges for two-pass Detect
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Phase 21 Wave 3 monotonic two-pass progress scale
# END_CHANGE_SUMMARY

from __future__ import annotations

# Global Detect progress ranges (approximate, product contract Wave 3)
DETECT_STAGE_RANGES: dict[str, tuple[int, int]] = {
    "prepare": (0, 5),
    "pass1": (5, 65),
    "debounce": (65, 70),
    "pass2": (70, 93),
    "dedupe": (93, 97),
    "persist": (97, 100),
}


def map_stage_progress(stage_start: int, stage_end: int, local_percent: int) -> int:
    """Map a local 0–100 percent into the inclusive global [stage_start, stage_end] range.

    Local values are clamped to 0–100 before mapping. Result is clamped to stage bounds.
    """
    # START_CONTRACT: map_stage_progress
    #   PURPOSE: Linear interpolation of local progress into a global stage window
    #   INPUTS: { stage_start: int, stage_end: int, local_percent: int }
    #   OUTPUTS: { int - global percent in [stage_start, stage_end] }
    #   SIDE_EFFECTS: none
    # END_CONTRACT: map_stage_progress
    if stage_end < stage_start:
        stage_start, stage_end = stage_end, stage_start
    local = max(0, min(100, int(local_percent)))
    if stage_end == stage_start:
        return int(stage_start)
    span = stage_end - stage_start
    mapped = stage_start + int(round(span * local / 100.0))
    return max(stage_start, min(stage_end, mapped))
