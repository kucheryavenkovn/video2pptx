# FILE: src/video2pptx/slide_detector.py
# VERSION: 0.1.2
# START_MODULE_CONTRACT
#   PURPOSE: Slide change detection via frame comparison with threshold and debounce
#   SCOPE: Compare consecutive frames, detect significant changes, apply debounce, and expose an optional disabled evidence observer
#   DEPENDS: frame_features, roi, models, numpy, loguru, detection_metrics
#   LINKS: M-SLIDE-DETECTOR
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ChangeEvent - detected change with timestamp and score
#   detect_changes - scan frames, produce ChangeEvents
#   debounce_changes - time-based debounce in seconds (0 disables)
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v0.3.0 - Phase 21: time-based debounce_changes; min_stable_duration seconds, 0 disables
# END_CHANGE_SUMMARY

from __future__ import annotations

from collections.abc import Callable, Iterator

import numpy as np
from loguru import logger

from video2pptx.analysis_scale import scale_for_analysis
from video2pptx.detection_metrics import get as _get_metrics
from video2pptx.detection_metrics import measure
from video2pptx.frame_features import compute_threshold, extract_features, visual_distance
from video2pptx.models import FrameFeatures
from video2pptx.roi import SlideRegion


class ChangeEvent:
    # START_CONTRACT: ChangeEvent
    #   PURPOSE: Represent a detected change point between frames
    #   INPUTS: { timestamp: float, score: float, features: FrameFeatures }
    #   OUTPUTS: { ChangeEvent }
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
    quick_mode: bool = False,
    analysis_max_side: int | None = None,
    # evidence_observer contract (see EVIDENCE_OBSERVER_CONTRACT above):
    #   - disabled by default (None) -> production path unchanged when analysis_max_side is None
    #   - "sampled_frame" hands the callback the MUTABLE native cropped ndarray AFTER ROI
    #     and BEFORE analysis scale / extract
    #   - trusted intrusive diagnostic hook; CAN alter detection; not semantically inert
    #   - public production callers MUST NOT use it to mutate the image
    evidence_observer: Callable[[str, dict], None] | None = None,
) -> tuple[list[ChangeEvent], list[FrameFeatures], list[float]]:
    # START_CONTRACT: detect_changes
    #   PURPOSE: Scan consecutive frames and identify debounced slide changes
    #   INPUTS: { frames, slide_region, threshold, min_stable_duration, sample_fps, video_duration, progress_callback, extract_fn, distance_fn, quick_mode, analysis_max_side, evidence_observer }
    #   OUTPUTS: { tuple[list[ChangeEvent], list[FrameFeatures], list[float]] }
    #   SIDE_EFFECTS: emits progress logs and optional progress callbacks
    #   LINKS: M-SLIDE-DETECTOR, M-DETECT-METRICS, M-ANALYSIS-SCALE
    #   EVIDENCE_OBSERVER_CONTRACT:
    #     - Disabled by default (evidence_observer=None). When None and analysis_max_side is
    #       None, the production detection path matches pre-Phase-19 native semantics.
    #     - When enabled, the "sampled_frame" event is emitted AFTER ROI cropping and
    #       BEFORE analysis scale / feature extraction, and its payload dict carries the
    #       image under the key "image" as the MUTABLE native cropped ndarray (live ref).
    #     - analysis_max_side (Phase 19) scales for extract only; observer still sees the
    #       native crop so full-res retention diagnostics remain valid.
    #     - Because the ndarray is mutable, a callback CAN modify it and therefore CAN alter
    #       the detection result. The observer is a TRUSTED INTRUSIVE DIAGNOSTIC HOOK, NOT a
    #       semantically inert observation point.
    #     - Public/production callers MUST NOT use evidence_observer to mutate the image
    #       or otherwise change detection semantics; it exists for trusted diagnostics
    #       (e.g. Step 18.4 HWAccel/evidence probes) only.
    #     - The "candidate_change" and "debounced_changes" events are emitted for
    #       observation only and do not hand the callback mutable detection input.
    # END_CONTRACT: detect_changes

    # START_BLOCK_DETECT_INIT
    slide_region = slide_region or SlideRegion(roi=None)
    changes: list[ChangeEvent] = []
    all_features: list[FrameFeatures] = []
    all_scores: list[float] = []
    _extract = extract_fn or extract_features
    _dist = distance_fn or visual_distance
    analysis_metrics_set = False
    # END_BLOCK_DETECT_INIT

    # START_BLOCK_PROCESS_FRAMES
    prev_features: FrameFeatures | None = None
    progress_step: float = max(30.0, (video_duration or 600.0) * 0.1)
    next_progress: float = progress_step
    for timestamp, image in frames:
        m = _get_metrics()

        with measure("roi"):
            cropped = slide_region.process(image)
        # Intrusive observer hook: native ROI crop BEFORE analysis scale / extract.
        if evidence_observer is not None:
            evidence_observer("sampled_frame", {"timestamp": timestamp, "image": cropped})

        # START_BLOCK_ANALYSIS_SCALE
        analysis_frame, scale_factor = scale_for_analysis(cropped, analysis_max_side)
        if m is not None and not analysis_metrics_set:
            ah, aw = analysis_frame.shape[:2]
            m.gauge_analysis_height.value = ah
            m.gauge_analysis_width.value = aw
            m.gauge_analysis_scale_factor.value = scale_factor
            m.gauge_analysis_max_side.value = (
                int(analysis_max_side) if analysis_max_side is not None and analysis_max_side > 0 else 0
            )
            analysis_metrics_set = True
        # END_BLOCK_ANALYSIS_SCALE

        with measure("extract_features"):
            ff = _extract(analysis_frame)
        ff.timestamp = timestamp
        all_features.append(ff)

        if m is not None:
            if quick_mode:
                m.counter_features_quick.increment()
            else:
                m.counter_features_full.increment()

        if prev_features is not None:
            with measure("visual_distance"):
                score = _dist(prev_features, ff)
            all_scores.append(score)

            with measure("threshold"):
                actual_threshold = _resolve_threshold(threshold, all_scores, timestamp)
            if score > actual_threshold:
                event = ChangeEvent(timestamp=timestamp, score=score, features=ff)
                changes.append(event)
                if evidence_observer is not None:
                    evidence_observer(
                        "candidate_change", {"event": event, "candidates": tuple(changes)}
                    )
                logger.debug(
                    f"[SlideDetector][detect_changes] Candidate change | "
                    f"ts={timestamp:.2f} score={score:.4f} threshold={actual_threshold:.4f}"
                )

        if timestamp >= next_progress:
            local_pct = (
                int(timestamp / video_duration * 100)
                if video_duration and video_duration > 0
                else 0
            )
            logger.info(
                f"[SlideDetector][detect_changes] Progress | "
                f"{local_pct}% ts={timestamp:.0f}s changes={len(changes)} "
                f"frames={len(all_features)}"
            )
            if progress_callback is not None:
                progress_callback(
                    local_pct,
                    f"Pass 1/2: analyzed {len(all_features)} frames, "
                    f"{len(changes)} candidates",
                )
            next_progress += progress_step

        prev_features = ff
    # END_BLOCK_PROCESS_FRAMES

    # START_BLOCK_DEBOUNCE
    if progress_callback is not None:
        progress_callback(100, "Pass 1/2: frame analysis complete")
    candidate_count = len(changes)
    # Stash for callers that read attribute after return (detect_slides counts)
    detect_changes.last_candidate_count = candidate_count  # type: ignore[attr-defined]
    with measure("debounce"):
        # Time-based debounce in seconds; independent of sample_fps.
        # sample_fps only controls analysis density, not the unit of min_stable_duration.
        changes = debounce_changes(changes, min_stable_duration)
    if progress_callback is not None:
        progress_callback(
            50,
            f"Debounce / segment building: {len(changes)} stable change points",
        )
    if evidence_observer is not None:
        evidence_observer("debounced_changes", {"changes": tuple(changes)})
    # END_BLOCK_DEBOUNCE

    # Auto-threshold diagnostics (INFO summary only — not one line per candidate)
    if isinstance(threshold, str) and threshold == "auto" and all_scores:
        from video2pptx.detection_counts import score_distribution_summary
        from video2pptx.frame_features import compute_threshold

        dist = score_distribution_summary(all_scores)
        thr = compute_threshold(all_scores)
        logger.info(
            "[SlideDetector][detect_changes] Auto-threshold diagnostics | "
            "threshold={:.4f} score_count={} min={:.4f} median={:.4f} "
            "p90={:.4f} p95={:.4f} p99={:.4f} max={:.4f}",
            thr,
            dist["score_count"],
            dist["score_min"],
            dist["score_median"],
            dist["score_p90"],
            dist["score_p95"],
            dist["score_p99"],
            dist["score_max"],
        )

    logger.info(
        f"[SlideDetector][detect_changes] Detection complete | "
        f"candidates={candidate_count} after_debounce={len(changes)} "
        f"total_frames={len(all_features)}"
    )
    return changes, all_features, all_scores


def _resolve_threshold(threshold: float | str, scores: list[float], timestamp: float) -> float:
    if isinstance(threshold, (int, float)):
        return float(threshold)
    return compute_threshold(scores)


def debounce_changes(
    changes: list[ChangeEvent],
    min_stable_duration: float,
) -> list[ChangeEvent]:
    """Filter change events so consecutive retained events are ≥ min_stable_duration seconds apart.

    min_stable_duration <= 0 disables debounce (returns a shallow copy of changes).
    Semantics use wall-clock timestamps only — not sample_fps frame counts.
    """
    # START_CONTRACT: debounce_changes
    #   PURPOSE: Time-based debounce of ChangeEvents
    #   INPUTS: { changes: list[ChangeEvent], min_stable_duration: float seconds }
    #   OUTPUTS: { list[ChangeEvent] }
    #   SIDE_EFFECTS: debug logs for removed events
    # END_CONTRACT: debounce_changes
    if len(changes) < 2:
        return list(changes)
    if min_stable_duration <= 0:
        return list(changes)

    result: list[ChangeEvent] = [changes[0]]
    for change in changes[1:]:
        gap = change.timestamp - result[-1].timestamp
        if gap >= min_stable_duration:
            result.append(change)
        else:
            logger.debug(
                f"[SlideDetector][debounce_changes] Removed change at {change.timestamp:.2f}s "
                f"(gap={gap:.3f}s < min_stable={min_stable_duration:.3f}s)"
            )
    return result


# Backward-compatible private alias
def _debounce_changes(changes: list[ChangeEvent], min_stable_duration: float) -> list[ChangeEvent]:
    return debounce_changes(changes, min_stable_duration)
