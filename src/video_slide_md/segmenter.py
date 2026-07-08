# FILE: src/video_slide_md/segmenter.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Convert change events to slide intervals with representative timestamps
#   SCOPE: Build SlideSegments from ChangeEvents, handle short segments, select representative timestamps
#   DEPENDS: models, loguru
#   LINKS: M-SEGMENTER
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   build_segments - convert change timestamps to slide intervals
#   choose_representative_timestamp - pick best frame timestamp for a segment
# END_MODULE_MAP

from __future__ import annotations

from loguru import logger

from video_slide_md.models import SlideSegment
from video_slide_md.slide_detector import ChangeEvent


def build_segments(
    changes: list[ChangeEvent],
    video_duration: float,
    min_slide_duration: float = 3.0,
) -> list[SlideSegment]:
    # START_CONTRACT: build_segments
    #   PURPOSE: Convert change timestamps to slide intervals
    #   INPUTS: { changes: list[ChangeEvent], video_duration: float, min_slide_duration: float }
    #   OUTPUTS: list[SlideSegment]
    #   SIDE_EFFECTS: none
    #   LINKS: M-SEGMENTER
    # END_CONTRACT: build_segments

    # START_BLOCK_BUILD_SEGMENTS
    segments: list[SlideSegment] = []

    # Build interval boundaries from changes
    boundaries = [0.0] + [c.timestamp for c in changes] + [video_duration]

    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        duration = end - start

        if duration < min_slide_duration:
            logger.warning(
                f"[Segmenter][build_segments] Short segment skipped | "
                f"index={len(segments) + 1} duration={duration:.2f}s"
            )
            continue

        rep_ts = choose_representative_timestamp(start, end)

        segment = SlideSegment(
            index=len(segments) + 1,
            start=start,
            end=end,
            duration=duration,
            representative_timestamp=rep_ts,
            confidence=0.9,
        )

        segments.append(segment)

    logger.info(
        f"[Segmenter][build_segments] Segments built | "
        f"count={len(segments)} video_duration={video_duration:.2f}"
    )
    return segments
    # END_BLOCK_BUILD_SEGMENTS


def choose_representative_timestamp(start: float, end: float) -> float:
    # START_CONTRACT: choose_representative_timestamp
    #   PURPOSE: Pick representative timestamp — near end for long slides, middle for short
    #   INPUTS: { start: float, end: float }
    #   OUTPUTS: float — timestamp in [start, end)
    #   SIDE_EFFECTS: none
    #   LINKS: M-SEGMENTER
    # END_CONTRACT: choose_representative_timestamp

    duration = end - start
    if duration >= 6.0:
        rep = start + duration * 0.80
    else:
        rep = start + duration * 0.50

    # Ensure rep doesn't exceed end
    rep = min(rep, end - 0.01)
    return rep
