# FILE: src/video2pptx/dedupe.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Remove near-duplicate segments based on representative frame similarity
#   SCOPE: Compare representative features across segments, merge near-duplicates
#   DEPENDS: models, frame_features, loguru
#   LINKS: M-DEDUPE
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   deduplicate_segments - merge segments whose representative frames are similar
# END_MODULE_MAP

from __future__ import annotations

from loguru import logger

from video2pptx.frame_features import extract_features, visual_distance
from video2pptx.models import FrameFeatures, SlideSegment


def deduplicate_segments(
    segments: list[SlideSegment],
    frames: dict,
    max_distance: float = 0.03,
) -> list[SlideSegment]:
    # START_CONTRACT: deduplicate_segments
    #   PURPOSE: Remove near-duplicate segments based on representative frame similarity
    #   INPUTS: {
    #       segments: list[SlideSegment],
    #       frames: dict — timestamp to frame image,
    #       max_distance: float — max visual distance to consider duplicate
    #   }
    #   OUTPUTS: list[SlideSegment]
    #   SIDE_EFFECTS: none
    #   LINKS: M-DEDUPE
    # END_CONTRACT: deduplicate_segments

    if len(segments) < 2:
        return list(segments)

    # START_BLOCK_DEDUPE

    result: list[SlideSegment] = [segments[0]]
    prev_features: FrameFeatures | None = None

    # Pre-compute features for the first segment
    first_frame = frames.get(segments[0].representative_timestamp)
    if first_frame is not None:
        prev_features = extract_features(first_frame)

    for seg in segments[1:]:
        rep_frame = frames.get(seg.representative_timestamp)
        if rep_frame is None:
            result.append(seg)
            continue

        current_features = extract_features(rep_frame)

        if prev_features is not None:
            dist = visual_distance(prev_features, current_features)
            if dist < max_distance:
                # Merge: extend the previous segment
                logger.debug(
                    f"[Dedupe][deduplicate_segments] Merging segment {seg.index} "
                    f"into {result[-1].index} | distance={dist:.4f}"
                )
                result[-1].end = seg.end
                result[-1].duration = result[-1].end - result[-1].start
                result[-1].confidence = max(result[-1].confidence, seg.confidence)
                continue

        # Not a duplicate, keep
        result.append(seg)
        prev_features = current_features

    # Re-index
    for i, seg in enumerate(result, 1):
        seg.index = i

    logger.info(
        f"[Dedupe][deduplicate_segments] Deduplication done | "
        f"before={len(segments)} after={len(result)}"
    )
    return result
    # END_BLOCK_DEDUPE
