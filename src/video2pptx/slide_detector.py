# FILE: src/video2pptx/slide_detector.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Slide change detection via frame comparison with threshold and debounce
#   SCOPE: Compare consecutive frames, detect significant changes, apply debounce via min_stable_duration
#   DEPENDS: frame_features, roi, models, numpy, loguru
#   LINKS: M-SLIDE-DETECTOR
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ChangeEvent - detected change with timestamp and score
#   detect_changes - scan frames, produce ChangeEvents
# END_MODULE_MAP

from __future__ import annotations

from typing import Callable, Iterator

import numpy as np
from loguru import logger

from video2pptx.frame_features import compute_threshold, extract_features, visual_distance
from video2pptx.models import FrameFeatures
from video2pptx.roi import SlideRegion


class ChangeEvent:
    # START_CONTRACT: ChangeEvent
    #   PURPOSE: A detected change point between frames
    #   INPUTS: { timestamp: float, score: float, features: FrameFeatures }
    #   OUTPUTS: ChangeEvent
    #   SIDE_EFFECTS: none
    #   LINKS: M-SLIDE-DETECTOR
    # END_CONTRACT: ChangeEvent
    def __init__(self, timestamp: float, score: float, features: FrameFeatures):
        self.timestamp = timestamp
        self.score = score
        self.features = features


def detect_changes(
    frames: Iterator[tuple[float, np.ndarray]],
    slide_region: SlideRegion | None = None,
    threshold: float | str = "auto",
    min_stable_duration: float = 1.5,
    sample_fps: float = 2.0,
    video_duration: float | None = None,
    progress_callback: Callable[[int, str], None] | None = None,
    extract_fn: Callable | None = None,
    distance_fn: Callable | None = None,
) -> tuple[list[ChangeEvent], list[FrameFeatures], list[float]]:
    # START_CONTRACT: detect_changes
    #   PURPOSE: Scan frames, compare consecutive, detect slide changes
    #   INPUTS: { frames: timestamp+image iterator, slide_region, threshold,
    #             min_stable_duration, sample_fps, video_duration }
    #   OUTPUTS: (changes: list[ChangeEvent], all_features: list[FrameFeatures], all_scores: list[float])
    #   SIDE_EFFECTS: none
    #   LINKS: M-SLIDE-DETECTOR
    # END_CONTRACT: detect_changes

    # START_BLOCK_DETECT_INIT
    slide_region = slide_region or SlideRegion(roi=None)
    changes: list[ChangeEvent] = []
    all_features: list[FrameFeatures] = []
    all_scores: list[float] = []
    # END_BLOCK_DETECT_INIT

    # START_BLOCK_PROCESS_FRAMES
    prev_features: FrameFeatures | None = None
    progress_step: float = max(30.0, (video_duration or 600.0) * 0.1)
    next_progress: float = progress_step
    for timestamp, image in frames:
        cropped = slide_region.process(image)
        _extract = extract_fn or extract_features
        _dist = distance_fn or visual_distance
        ff = _extract(cropped)
        ff.timestamp = timestamp
        all_features.append(ff)

        if prev_features is not None:
            score = _dist(prev_features, ff)
            all_scores.append(score)

            actual_threshold = _resolve_threshold(threshold, all_scores, timestamp)
            if score > actual_threshold:
                changes.append(ChangeEvent(timestamp=timestamp, score=score, features=ff))
                logger.debug(
                    f"[SlideDetector][detect_changes] Candidate change | "
                    f"ts={timestamp:.2f} score={score:.4f} threshold={actual_threshold:.4f}"
                )

        if timestamp >= next_progress:
            pct = f"{timestamp / video_duration * 100:.0f}%" if video_duration else f"{timestamp:.0f}s"
            logger.info(
                f"[SlideDetector][detect_changes] Progress | "
                f"{pct} ts={timestamp:.0f}s changes={len(changes)}"
            )
            if progress_callback and video_duration:
                progress_callback(
                    int(timestamp / video_duration * 100),
                    f"Pass 1/3 — {len(changes)} changes at {timestamp:.0f}s",
                )
            next_progress += progress_step

        prev_features = ff
    # END_BLOCK_PROCESS_FRAMES

    # START_BLOCK_DEBOUNCE
    stable_frames = max(1, int(round(sample_fps * min_stable_duration)))
    changes = _debounce_changes(changes, stable_frames)
    # END_BLOCK_DEBOUNCE

    logger.info(
        f"[SlideDetector][detect_changes] Detection complete | "
        f"changes={len(changes)} total_frames={len(all_features)}"
    )
    return changes, all_features, all_scores


def _resolve_threshold(threshold: float | str, scores: list[float], timestamp: float) -> float:
    if isinstance(threshold, (int, float)):
        return float(threshold)
    return compute_threshold(scores)


def _debounce_changes(changes: list[ChangeEvent], min_stable_frames: int) -> list[ChangeEvent]:
    """Remove changes that are too close together (debounce)."""
    if len(changes) < 2:
        return changes

    result: list[ChangeEvent] = [changes[0]]
    for i in range(1, len(changes)):
        gap_frames = int(round(
            (changes[i].timestamp - result[-1].timestamp)
            / max(0.5, 1.0 / 30.0)  # approximate frame duration
        ))
        if gap_frames >= min_stable_frames:
            result.append(changes[i])
        else:
            logger.debug(
                f"[SlideDetector][_debounce_changes] Removed change at {changes[i].timestamp:.2f}s "
                f"(gap too short)"
            )
    return result
