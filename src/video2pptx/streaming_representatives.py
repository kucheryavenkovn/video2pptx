# FILE: src/video2pptx/streaming_representatives.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Streaming Pass 2 — sequential full-res representative capture with online neighbor dedupe
#   SCOPE: O(frames + targets) target iterator; ≤2 live full-res frames; sequential PNG names
#   DEPENDS: cv2, numpy, loguru, frame_features, models, roi
#   LINKS: M-DETECT-SLIDES, M-DEDUPE, Phase-21 Wave 7
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   stream_representatives_and_dedupe - capture + optional streaming dedupe + write PNGs
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Phase 21 streaming Pass 2
# END_CHANGE_SUMMARY

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from loguru import logger

from video2pptx.frame_features import extract_features, visual_distance
from video2pptx.models import FrameFeatures, SlideSegment
from video2pptx.roi import SlideRegion


@dataclass
class StreamingPass2Result:
    segments: list[SlideSegment]
    decoded_frames: int
    target_count: int
    captured_count: int
    missing_count: int
    peak_live_fullres_frames: int
    peak_live_frame_bytes: int
    wall_seconds: float
    screenshots_written: int
    comparisons: int  # for O(frames+targets) evidence (not frames×targets)


def stream_representatives_and_dedupe(
    frames: Iterator,
    segments: list[SlideSegment],
    slide_region: SlideRegion,
    slides_dir: Path,
    *,
    sample_tolerance: float,
    dedupe_enabled: bool = True,
    max_distance: float = 0.03,
    progress_callback: Callable[[int, str], None] | None = None,
) -> StreamingPass2Result:
    """One sequential pass: capture reps near targets, stream-dedupe, write sequential PNGs.

    Peak live full-res frames ≤ 2 (pending retained + current candidate).
    Stops decoding after the last target is resolved.
    """
    t0 = time.perf_counter()
    slides_dir.mkdir(parents=True, exist_ok=True)

    if not segments:
        _cleanup_stale_pngs(slides_dir, keep_names=set())
        return StreamingPass2Result(
            segments=[],
            decoded_frames=0,
            target_count=0,
            captured_count=0,
            missing_count=0,
            peak_live_fullres_frames=0,
            peak_live_frame_bytes=0,
            wall_seconds=time.perf_counter() - t0,
            screenshots_written=0,
            comparisons=0,
        )

    # Sort by representative timestamp; keep original segment refs
    ordered = sorted(segments, key=lambda s: s.representative_timestamp)
    n_targets = len(ordered)
    next_i = 0

    # Nearest-frame tracking for current target
    best_frame: np.ndarray | None = None
    best_ts: float | None = None
    best_diff: float = float("inf")

    # Streaming dedupe state — at most two full-res images live
    pending_seg: SlideSegment | None = None
    pending_frame: np.ndarray | None = None
    pending_features: FrameFeatures | None = None
    finalized: list[tuple[SlideSegment, np.ndarray]] = []

    decoded = 0
    captured = 0
    missing = 0
    peak_live = 0
    peak_bytes = 0
    comparisons = 0

    def _live_count() -> int:
        return int(pending_frame is not None) + int(best_frame is not None)

    def _note_live() -> None:
        nonlocal peak_live, peak_bytes
        live = _live_count()
        peak_live = max(peak_live, live)
        b = 0
        if pending_frame is not None:
            b += int(pending_frame.nbytes)
        if best_frame is not None:
            b += int(best_frame.nbytes)
        peak_bytes = max(peak_bytes, b)

    def _commit_capture(frame: np.ndarray, seg: SlideSegment) -> None:
        nonlocal pending_seg, pending_frame, pending_features, captured, comparisons
        captured += 1
        if pending_seg is None:
            pending_seg = seg.model_copy(deep=True) if hasattr(seg, "model_copy") else seg
            pending_frame = frame
            pending_features = extract_features(frame)
            _note_live()
            return

        assert pending_frame is not None
        if dedupe_enabled:
            cur_feat = extract_features(frame)
            comparisons += 1
            dist = visual_distance(pending_features, cur_feat) if pending_features else 1.0
            if dist < max_distance:
                # Extend pending; drop current full-res immediately
                pending_seg.end = seg.end
                pending_seg.duration = pending_seg.end - pending_seg.start
                pending_seg.confidence = max(pending_seg.confidence, seg.confidence)
                logger.debug(
                    "[StreamingPass2] dedupe merge | into_start={:.2f} new_end={:.2f} dist={:.4f}",
                    pending_seg.start,
                    pending_seg.end,
                    dist,
                )
                return
            # Not duplicate: finalize pending, promote current
            finalized.append((pending_seg, pending_frame))
            pending_seg = seg.model_copy(deep=True) if hasattr(seg, "model_copy") else seg
            pending_frame = frame
            pending_features = cur_feat
        else:
            finalized.append((pending_seg, pending_frame))
            pending_seg = seg.model_copy(deep=True) if hasattr(seg, "model_copy") else seg
            pending_frame = frame
            pending_features = extract_features(frame)
        _note_live()

    def _resolve_target(seg: SlideSegment) -> None:
        nonlocal best_frame, best_ts, best_diff, missing
        if best_frame is not None:
            _commit_capture(best_frame, seg)
        else:
            missing += 1
            logger.warning(
                "[StreamingPass2] missing representative | index={} ts={:.3f} — no frame in tolerance",
                seg.index,
                seg.representative_timestamp,
            )
        best_frame = None
        best_ts = None
        best_diff = float("inf")

    last_report = -1
    for vf in frames:
        decoded += 1
        if next_i >= n_targets:
            break

        # Only compare against current target (O(1) per frame) — never full segments list
        comparisons += 1
        seg = ordered[next_i]
        target_ts = seg.representative_timestamp
        diff = abs(vf.timestamp - target_ts)

        if vf.timestamp + sample_tolerance < target_ts:
            # Still before target window
            continue

        if diff <= sample_tolerance:
            if diff < best_diff:
                cropped = slide_region.process(vf.image)
                best_frame = cropped
                best_ts = vf.timestamp
                best_diff = diff
                _note_live()
            # If frame is past target, we can commit this target and advance
            if vf.timestamp >= target_ts:
                # Peek: if next frame would be farther, commit now; else keep refining
                # Conservative: commit when at/past target with a candidate
                _resolve_target(seg)
                next_i += 1
                if progress_callback is not None and (
                    next_i == 1
                    or next_i == n_targets
                    or next_i - last_report >= max(1, n_targets // 20)
                ):
                    last_report = next_i
                    local = int(next_i * 100 / max(1, n_targets))
                    progress_callback(
                        local,
                        f"Pass 2/2: captured {captured}/{n_targets} representative frames",
                    )
            continue

        if vf.timestamp > target_ts + sample_tolerance:
            # Passed window — finalize with best or mark missing
            if best_frame is None:
                # Use current frame as nearest available after miss
                cropped = slide_region.process(vf.image)
                best_frame = cropped
                best_diff = abs(vf.timestamp - target_ts)
                missing += 1
                logger.warning(
                    "[StreamingPass2] late capture | index={} target={:.3f} got={:.3f}",
                    seg.index,
                    target_ts,
                    vf.timestamp,
                )
            _resolve_target(seg)
            next_i += 1
            # Re-check same frame against new target (rare stacked targets)
            if next_i < n_targets:
                comparisons += 1
                seg2 = ordered[next_i]
                d2 = abs(vf.timestamp - seg2.representative_timestamp)
                if d2 <= sample_tolerance:
                    cropped = slide_region.process(vf.image)
                    best_frame = cropped
                    best_diff = d2
                    _note_live()
            if progress_callback is not None and (
                next_i == n_targets or next_i - last_report >= max(1, n_targets // 20)
            ):
                last_report = next_i
                local = int(next_i * 100 / max(1, n_targets))
                progress_callback(
                    local,
                    f"Pass 2/2: captured {captured}/{n_targets} representative frames",
                )

    # Remaining unresolved targets
    while next_i < n_targets:
        if best_frame is not None:
            _resolve_target(ordered[next_i])
        else:
            missing += 1
            logger.warning(
                "[StreamingPass2] EOF missing | index={} ts={:.3f}",
                ordered[next_i].index,
                ordered[next_i].representative_timestamp,
            )
        next_i += 1

    if pending_seg is not None and pending_frame is not None:
        finalized.append((pending_seg, pending_frame))
        pending_seg = None
        pending_frame = None
        pending_features = None

    # Sequential re-index and write PNGs; remove stale files
    written = 0
    keep: set[str] = set()
    out_segments: list[SlideSegment] = []
    for i, (seg, frame) in enumerate(finalized, start=1):
        seg.index = i
        fname = f"slide_{i:03d}.png"
        keep.add(fname)
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        ok = cv2.imwrite(str(slides_dir / fname), bgr)
        if ok:
            written += 1
            seg.image = f"slides/{fname}"
        else:
            seg.image = None
        out_segments.append(seg)

    _cleanup_stale_pngs(slides_dir, keep_names=keep)

    wall = time.perf_counter() - t0
    logger.info(
        "[StreamingPass2] done | targets={} captured={} missing={} decoded={} "
        "final_slides={} peak_live_frames={} peak_bytes={} comparisons={} wall={:.2f}s",
        n_targets,
        captured,
        missing,
        decoded,
        len(out_segments),
        peak_live,
        peak_bytes,
        comparisons,
        wall,
    )
    return StreamingPass2Result(
        segments=out_segments,
        decoded_frames=decoded,
        target_count=n_targets,
        captured_count=captured,
        missing_count=missing,
        peak_live_fullres_frames=peak_live,
        peak_live_frame_bytes=peak_bytes,
        wall_seconds=wall,
        screenshots_written=written,
        comparisons=comparisons,
    )


def _cleanup_stale_pngs(slides_dir: Path, keep_names: set[str]) -> None:
    if not slides_dir.is_dir():
        return
    for p in slides_dir.glob("slide_*.png"):
        if p.name not in keep_names:
            try:
                p.unlink()
            except OSError as exc:
                logger.warning("[StreamingPass2] stale PNG remove failed | path={} err={}", p, exc)
