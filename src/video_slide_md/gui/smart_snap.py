# FILE: src/video_slide_md/gui/smart_snap.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Smart snap strategies for manual markers — snap to nearest scene boundary
#   SCOPE: Three strategies: diff_only, fallback_analyze, hybrid. Load diff_scores CSV or decode video window.
#   DEPENDS: csv, pathlib, cv2, numpy, loguru, M-FRAME-FEATURES, M-MODELS
#   LINKS: M-GUI-SMART-SNAP
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   smart_snap - main entry: dispatch to strategy based on snap_mode
#   _snap_diff_only - find nearest local max in existing diff_scores
#   _snap_fallback_analyze - try diff_scores, decode window if none
#   _snap_hybrid - use diff_scores unless flat, then high-res decode
#   _load_diff_scores - parse diff_scores.csv from project debug dir
#   _find_peak_in_window - find nearest local max in score array
#   _decode_and_analyze_window - decode frame range, compute differences
# END_MODULE_MAP

from __future__ import annotations

import csv
from pathlib import Path

import cv2
import numpy as np
from loguru import logger

from video_slide_md.frame_features import extract_features, visual_distance
from video_slide_md.project_manager import Project

# Default window sizes per strategy
DIFF_WINDOW_SECONDS: float = 5.0
FALLBACK_WINDOW_SECONDS: float = 3.0
FALLBACK_SAMPLE_FPS: float = 5.0
HYBRID_WINDOW_SECONDS: float = 2.0
HYBRID_SAMPLE_FPS: float = 10.0


def smart_snap(
    timestamp: float,
    project: Project,
    snap_mode: str = "hybrid",
    snap_flat_threshold: float = 0.05,
) -> float:
    # START_CONTRACT: smart_snap
    #   PURPOSE: Main entry — snap a manual marker to the nearest scene boundary
    #   INPUTS: {
    #       timestamp: float — marker position in seconds,
    #       project: Project — for resolving video/data paths,
    #       snap_mode: str — "diff_only" | "fallback_analyze" | "hybrid",
    #       snap_flat_threshold: float — flatness threshold for hybrid mode
    #   }
    #   OUTPUTS: float — snapped timestamp
    #   SIDE_EFFECTS: may decode a small video window for fallback/hybrid
    #   LINKS: M-GUI-SMART-SNAP
    # END_CONTRACT: smart_snap

    # START_BLOCK_SMART_SNAP
    logger.info(
        f"[GUI-SmartSnap][smart_snap] Starting snap | "
        f"original={timestamp:.3f} mode={snap_mode}"
    )

    if snap_mode == "diff_only":
        result = _snap_diff_only(timestamp, project)
    elif snap_mode == "fallback_analyze":
        result = _snap_fallback_analyze(timestamp, project)
    elif snap_mode == "hybrid":
        result = _snap_hybrid(timestamp, project, snap_flat_threshold)
    else:
        logger.warning(f"[GUI-SmartSnap][smart_snap] Unknown snap_mode={snap_mode}, using hybrid")
        result = _snap_hybrid(timestamp, project, snap_flat_threshold)

    distance = abs(result - timestamp) if result != timestamp else 0.0
    logger.info(
        f"[GUI-SmartSnap][smart_snap] Snap result | "
        f"original={timestamp:.3f} snapped={result:.3f} distance={distance:.3f}"
    )
    return result
    # END_BLOCK_SMART_SNAP


def _load_diff_scores(project: Project) -> tuple[list[float], list[float]]:
    # START_CONTRACT: _load_diff_scores
    #   PURPOSE: Parse diff_scores.csv from project's debug directory
    #   INPUTS: { project: Project }
    #   OUTPUTS: (timestamps: list[float], scores: list[float]) — empty lists if file missing
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-SMART-SNAP
    # END_CONTRACT: _load_diff_scores

    # START_BLOCK_LOAD_DIFF_SCORES
    proj_dir = Path(project.output_dir)
    csv_path = proj_dir / "debug" / "diff_scores.csv"

    if not csv_path.is_file():
        logger.info(f"[GUI-SmartSnap][_load_diff_scores] No diff_scores.csv found | path={csv_path}")
        return [], []

    timestamps: list[float] = []
    scores: list[float] = []

    try:
        with csv_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    ts = float(row.get("timestamp", 0))
                    sc = float(row.get("score", 0))
                    timestamps.append(ts)
                    scores.append(sc)
                except (ValueError, TypeError):
                    continue
        logger.info(f"[GUI-SmartSnap][_load_diff_scores] Loaded | rows={len(timestamps)} path={csv_path}")
    except Exception as exc:
        logger.warning(f"[GUI-SmartSnap][_load_diff_scores] Failed to parse | error={exc}")
        return [], []

    return timestamps, scores
    # END_BLOCK_LOAD_DIFF_SCORES


def _find_peak_in_window(
    timestamps: list[float],
    scores: list[float],
    center: float,
    window: float,
) -> float | None:
    # START_CONTRACT: _find_peak_in_window
    #   PURPOSE: Find the timestamp of the maximum score within [center-window, center+window]
    #   INPUTS: { timestamps: list[float], scores: list[float], center: float, window: float }
    #   OUTPUTS: float | None — timestamp of peak, or None if no data in window
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-SMART-SNAP
    # END_CONTRACT: _find_peak_in_window

    # START_BLOCK_FIND_PEAK
    low = center - window
    high = center + window

    best_ts: float | None = None
    best_score: float = -1.0

    for ts, sc in zip(timestamps, scores):
        if low <= ts <= high:
            if sc > best_score:
                best_score = sc
                best_ts = ts

    return best_ts
    # END_BLOCK_FIND_PEAK


def _snap_diff_only(timestamp: float, project: Project) -> float:
    # START_CONTRACT: _snap_diff_only
    #   PURPOSE: Snap using existing diff_scores only. No fallback decode.
    #   INPUTS: { timestamp: float, project: Project }
    #   OUTPUTS: float — snapped or original timestamp if no diff_scores
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-SMART-SNAP
    # END_CONTRACT: _snap_diff_only

    # START_BLOCK_SNAP_DIFF_ONLY
    timestamps, scores = _load_diff_scores(project)
    if not timestamps:
        logger.info("[GUI-SmartSnap][_snap_diff_only] No diff_scores available, returning original")
        return timestamp

    peak = _find_peak_in_window(timestamps, scores, timestamp, DIFF_WINDOW_SECONDS)
    if peak is None:
        logger.info("[GUI-SmartSnap][_snap_diff_only] No peak found in window, returning original")
        return timestamp

    logger.info(
        f"[GUI-SmartSnap][_snap_diff_only] Snapped to diff peak | "
        f"original={timestamp:.3f} peak={peak:.3f}"
    )
    return peak
    # END_BLOCK_SNAP_DIFF_ONLY


def _snap_fallback_analyze(timestamp: float, project: Project) -> float:
    # START_CONTRACT: _snap_fallback_analyze
    #   PURPOSE: Try diff_scores first, decode window if none available
    #   INPUTS: { timestamp: float, project: Project }
    #   OUTPUTS: float — snapped timestamp
    #   SIDE_EFFECTS: may decode video window
    #   LINKS: M-GUI-SMART-SNAP
    # END_CONTRACT: _snap_fallback_analyze

    # START_BLOCK_SNAP_FALLBACK_ANALYZE
    timestamps, scores = _load_diff_scores(project)
    if timestamps:
        peak = _find_peak_in_window(timestamps, scores, timestamp, DIFF_WINDOW_SECONDS)
        if peak is not None:
            logger.info(
                f"[GUI-SmartSnap][_snap_fallback_analyze] Snapped to diff peak | "
                f"original={timestamp:.3f} peak={peak:.3f}"
            )
            return peak

    logger.info(f"[GUI-SmartSnap][_snap_fallback_analyze] No diff scores, decoding window | original={timestamp:.3f}")
    return _decode_and_analyze_window(timestamp, project, FALLBACK_WINDOW_SECONDS, FALLBACK_SAMPLE_FPS)
    # END_BLOCK_SNAP_FALLBACK_ANALYZE


def _snap_hybrid(timestamp: float, project: Project, flat_threshold: float) -> float:
    # START_CONTRACT: _snap_hybrid
    #   PURPOSE: Use diff_scores. If window is flat (max-min < threshold), fallback to high-res analysis.
    #   INPUTS: { timestamp: float, project: Project, flat_threshold: float }
    #   OUTPUTS: float — snapped timestamp
    #   SIDE_EFFECTS: may decode video window if diff graph is flat
    #   LINKS: M-GUI-SMART-SNAP
    # END_CONTRACT: _snap_hybrid

    # START_BLOCK_SNAP_HYBRID
    timestamps, scores = _load_diff_scores(project)
    if timestamps:
        # Check if window is flat
        low = timestamp - DIFF_WINDOW_SECONDS
        high = timestamp + DIFF_WINDOW_SECONDS
        window_scores = [sc for ts, sc in zip(timestamps, scores) if low <= ts <= high]

        if window_scores:
            min_s = min(window_scores)
            max_s = max(window_scores)
            spread = max_s - min_s
            logger.info(
                f"[GUI-SmartSnap][_snap_hybrid] Window analysis | "
                f"min={min_s:.6f} max={max_s:.6f} spread={spread:.6f} threshold={flat_threshold}"
            )

            if spread > flat_threshold:
                peak = _find_peak_in_window(timestamps, scores, timestamp, DIFF_WINDOW_SECONDS)
                if peak is not None:
                    logger.info(
                        f"[GUI-SmartSnap][_snap_hybrid] Snapped to diff peak | "
                        f"original={timestamp:.3f} peak={peak:.3f}"
                    )
                    return peak

        logger.info(
            f"[GUI-SmartSnap][_snap_hybrid] Flat graph detected, running high-res analysis | "
            f"original={timestamp:.3f}"
        )
    else:
        logger.info(
            f"[GUI-SmartSnap][_snap_hybrid] No diff scores, running high-res analysis | "
            f"original={timestamp:.3f}"
        )

    return _decode_and_analyze_window(timestamp, project, HYBRID_WINDOW_SECONDS, HYBRID_SAMPLE_FPS)
    # END_BLOCK_SNAP_HYBRID


def _decode_and_analyze_window(
    timestamp: float,
    project: Project,
    window: float,
    sample_fps: float,
) -> float:
    # START_CONTRACT: _decode_and_analyze_window
    #   PURPOSE: Decode a short window around timestamp, compute frame differences, find peak
    #   INPUTS: { timestamp: float, project: Project, window: float, sample_fps: float }
    #   OUTPUTS: float — snapped timestamp, or original if no difference found
    #   SIDE_EFFECTS: reads video file
    #   LINKS: M-GUI-SMART-SNAP
    # END_CONTRACT: _decode_and_analyze_window

    # START_BLOCK_DECODE_AND_ANALYZE
    video_path = Path(project.video)
    if not video_path.is_file():
        logger.warning(f"[GUI-SmartSnap][_decode_and_analyze_window] Video not found | path={video_path}")
        return timestamp

    low = max(0.0, timestamp - window)
    high = timestamp + window
    step = 1.0 / sample_fps

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.warning(f"[GUI-SmartSnap][_decode_and_analyze_window] Cannot open video | path={video_path}")
        return timestamp

    try:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 30.0

        frame_times: list[float] = []
        prev_features = None
        best_score: float = -1.0
        best_time: float = timestamp

        t = low
        while t <= high:
            frame_idx = int(t * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                t += step
                continue

            actual_t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            if actual_t <= 0:
                actual_t = t

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            features = extract_features(rgb)

            if prev_features is not None:
                score = visual_distance(prev_features, features)
                if score > best_score:
                    best_score = score
                    best_time = actual_t - (step / 2)  # midpoint between frames

            prev_features = features
            t += step

        logger.info(
            f"[GUI-SmartSnap][_decode_and_analyze_window] Analysis complete | "
            f"original={timestamp:.3f} snapped={best_time:.3f} best_score={best_score:.6f}"
        )
        return best_time

    finally:
        cap.release()
    # END_BLOCK_DECODE_AND_ANALYZE
