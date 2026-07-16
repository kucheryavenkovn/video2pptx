#!/usr/bin/env python3
# FILE: tools/probe_pass2_retrieval.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: C1 diagnostic — compare sequential Pass 2 representative-frame
#            collection against a targeted seek-based retrieval candidate.
#   SCOPE: Shared Pass 1, reference sequential collection, candidate targeted
#          retrieval, exact frame parity, optional microbenchmark.
#   DEPENDS: video2pptx (VideoDecoder, detect_changes, build_segments, SlideRegion,
#            dedupe), av, numpy, cv2, hashlib, tools.discrimination_helpers
#   LINKS: M-DETECT-PERF-DECISION, V-PERF-DETECT-BOTTLENECK
#   ROLE: SCRIPT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   make_canonical_config - AppConfig matching the accepted benchmark config
#   run_shared_pass1 - one canonical Pass 1 to obtain changes/segments/rep timestamps
#   collect_reference_pass2 - current sequential Pass 2 representative-frame collection
#   collect_candidate_targeted - seek-based targeted representative-frame retrieval
#   main - CLI entry producing JSON evidence artifacts
# END_MODULE_MAP
"""C1 diagnostic: PASS2_TARGETED_REPRESENTATIVE_FRAME_RETRIEVAL."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import numpy as np

from video2pptx.config import AppConfig
from video2pptx.frame_features import extract_features as _extract
from video2pptx.frame_features import visual_distance as _dist
from video2pptx.roi import SlideRegion, parse_ignore_rois, parse_roi
from video2pptx.segmenter import build_segments
from video2pptx.slide_detector import detect_changes
from video2pptx.video_decode import VideoDecoder

sys.path.insert(0, str(Path(__file__).resolve().parent))
from discrimination_helpers import (  # noqa: E402
    check_frame_parity,
    compute_mean,
    compute_median,
    compute_median_reduction_percent,
    compute_paired_absolute_savings,
    compute_paired_percentage_reduction,
    compute_sample_stdev,
    compute_target_frame_index,
    compute_target_sampled_timestamp,
    directional_stability,
)

# =========================================================================
# Config
# =========================================================================


def make_canonical_config() -> AppConfig:
    cfg = AppConfig()
    cfg.video.sample_fps = 2.0
    cfg.video.decoder_backend = "auto"
    cfg.detection.slide_roi = "auto"
    cfg.detection.ignore_rois = []
    cfg.detection.threshold = "auto"
    cfg.detection.min_slide_duration = 2.0
    cfg.detection.min_stable_duration = 2.0
    cfg.detection.dedupe_enabled = True
    return cfg


# =========================================================================
# Shared Pass 1
# =========================================================================


class Pass1Result:
    __slots__ = (
        "segments", "slide_region", "info",
        "sample_tolerance", "video_fps", "frame_interval",
    )

    def __init__(
        self,
        segments: list,
        slide_region: SlideRegion,
        info: Any,
        sample_tolerance: float,
        video_fps: float,
        frame_interval: int,
    ):
        self.segments = segments
        self.slide_region = slide_region
        self.info = info
        self.sample_tolerance = sample_tolerance
        self.video_fps = video_fps
        self.frame_interval = frame_interval


def run_shared_pass1(video_path: Path, cfg: AppConfig) -> Pass1Result:
    """Execute one canonical Pass 1 using production functions."""
    decoder = VideoDecoder(
        video_path=video_path,
        sample_fps=cfg.video.sample_fps,
        backend=cfg.video.decoder_backend,
    )
    info = decoder.get_info()
    slide_region = SlideRegion(
        roi=parse_roi(cfg.detection.slide_roi).roi,
        ignore_rois=parse_ignore_rois(cfg.detection.ignore_rois),
    )
    sample_tolerance = 0.5 / max(cfg.video.sample_fps, 0.1)

    frames_iter = (
        (f.timestamp, f.image) for f in decoder.iter_frames()
    )
    changes, _, _ = detect_changes(
        frames=frames_iter,
        slide_region=slide_region,
        threshold=cfg.detection.threshold,
        min_stable_duration=cfg.detection.min_stable_duration,
        sample_fps=cfg.video.sample_fps,
        video_duration=info.duration,
        extract_fn=_extract,
        distance_fn=_dist,
        quick_mode=False,
    )

    segments = build_segments(
        changes=changes,
        video_duration=info.duration,
        min_slide_duration=cfg.detection.min_slide_duration,
    )

    video_fps = float(info.fps)
    if video_fps <= 0:
        video_fps = 30.0
    frame_interval = max(1, int(round(video_fps / cfg.video.sample_fps)))

    return Pass1Result(
        segments=segments,
        slide_region=slide_region,
        info=info,
        sample_tolerance=sample_tolerance,
        video_fps=video_fps,
        frame_interval=frame_interval,
    )


# =========================================================================
# Reference sequential Pass 2
# =========================================================================


def collect_reference_pass2(
    video_path: Path,
    cfg: AppConfig,
    pass1: Pass1Result,
) -> dict[str, Any]:
    """Run the current production sequential Pass 2 representative-frame collection."""
    decoder = VideoDecoder(
        video_path=video_path,
        sample_fps=cfg.video.sample_fps,
        backend=cfg.video.decoder_backend,
    )
    segments = pass1.segments
    slide_region = pass1.slide_region
    sample_tolerance = pass1.sample_tolerance

    rep_frames: dict[float, np.ndarray] = {}
    per_target: dict[float, dict[str, Any]] = {}

    frames_sampled = 0
    ndarray_conversions = 0
    rgb_transfer_bytes = 0

    start = time.perf_counter()
    for vf in decoder.iter_frames():
        frames_sampled += 1
        for s in segments:
            ts = s.representative_timestamp
            if ts not in rep_frames and abs(vf.timestamp - ts) < sample_tolerance:
                raw_sha = hashlib.sha256(vf.image.tobytes()).hexdigest()
                cropped = slide_region.process(vf.image)
                rep_frames[ts] = cropped
                sha = hashlib.sha256(cropped.tobytes()).hexdigest()
                per_target[ts] = {
                    "sampled_timestamp": float(vf.timestamp),
                    "shape": list(cropped.shape),
                    "rgb_sha256": sha,
                    "raw_bytes_sha256": sha,
                    "raw_img_sha256": raw_sha,
                }
                ndarray_conversions += 1
                rgb_transfer_bytes += cropped.nbytes
                break
    elapsed = time.perf_counter() - start

    return {
        "method": "SEQUENTIAL_PASS2_REFERENCE",
        "wall_clock_seconds": elapsed,
        "frames_sampled": frames_sampled,
        "ndarray_conversions": ndarray_conversions,
        "rgb_transfer_bytes": rgb_transfer_bytes,
        "representative_frames_collected": len(rep_frames),
        "per_target": per_target,
    }


# =========================================================================
# Candidate targeted retrieval
# =========================================================================


def _open_production_container(video_path: Path):
    """Open a PyAV container with the same hwaccel configuration as production."""
    import av

    from video2pptx.backends.pyav_backend import (
        _create_hwaccel_with_evidence,
        _pick_hw_device,
    )

    hw_device = _pick_hw_device()
    hwaccel = None
    if hw_device is not None:
        hwaccel, _, _ = _create_hwaccel_with_evidence(hw_device)
    container = av.open(str(video_path), hwaccel=hwaccel)
    return container


def collect_candidate_targeted(
    video_path: Path,
    cfg: AppConfig,
    pass1: Pass1Result,
) -> dict[str, Any]:
    """Run seek-based targeted representative-frame retrieval (C1 candidate)."""
    segments = pass1.segments
    slide_region = pass1.slide_region
    sample_tolerance = pass1.sample_tolerance
    video_fps = pass1.video_fps
    frame_interval = pass1.frame_interval

    rep_timestamps = [s.representative_timestamp for s in segments]

    targets: list[dict[str, Any]] = []
    skipped_no_match = 0
    for rep_ts in rep_timestamps:
        target_ts = compute_target_sampled_timestamp(
            rep_ts, video_fps, frame_interval, sample_tolerance
        )
        if target_ts is None:
            skipped_no_match += 1
            continue
        target_idx = compute_target_frame_index(target_ts, video_fps, frame_interval)
        targets.append({
            "rep_ts": float(rep_ts),
            "target_sampled_ts": float(target_ts),
            "target_frame_idx": int(target_idx),
        })

    targets.sort(key=lambda t: t["target_frame_idx"])

    # Compute PTS offset: the first sequentially-decoded frame's PTS.
    # Production uses current_frame_idx / video_fps for timestamps (starting at 0),
    # but the actual PTS of the first decoded frame has an encoder delay offset.
    # production_idx = round((frame.pts - pts_offset) * time_base * video_fps)
    probe_container = _open_production_container(video_path)
    probe_stream = probe_container.streams.video[0]
    pts_offset = 0
    for pkt in probe_container.demux(probe_stream):
        for fr in pkt.decode():
            if fr.pts is not None:
                pts_offset = int(fr.pts)
            break
        break
    probe_container.close()

    time_base = float(probe_stream.time_base) if probe_stream.time_base else 1.0 / video_fps

    per_target: dict[float, dict[str, Any]] = {}
    frames_decoded = 0
    ndarray_conversions = 0
    rgb_transfer_bytes = 0

    start = time.perf_counter()
    container_opens = 0
    try:
        remaining = list(targets)
        seek_margin_seconds = 2.0

        while remaining:
            target = remaining[0]
            target_idx = target["target_frame_idx"]
            target_ts = target["target_sampled_ts"]

            seek_ts = max(0.0, target_ts - seek_margin_seconds)
            seek_pts = int(seek_ts / time_base) + pts_offset
            container = _open_production_container(video_path)
            container_opens += 1
            stream = container.streams.video[0]
            container.seek(seek_pts, stream=stream)

            found = False
            for packet in container.demux(stream):
                for frame in packet.decode():
                    frames_decoded += 1
                    pts = frame.pts
                    if pts is None:
                        continue
                    production_idx = round((pts - pts_offset) * time_base * video_fps)

                    if production_idx == target_idx:
                        img = frame.to_ndarray(format="rgb24")
                        raw_sha = hashlib.sha256(img.tobytes()).hexdigest()
                        ndarray_conversions += 1
                        rgb_transfer_bytes += img.nbytes
                        cropped = slide_region.process(img)
                        sha = hashlib.sha256(cropped.tobytes()).hexdigest()
                        per_target[target["rep_ts"]] = {
                            "sampled_timestamp": float(target_ts),
                            "shape": list(cropped.shape),
                            "rgb_sha256": sha,
                            "raw_bytes_sha256": sha,
                            "raw_img_sha256": raw_sha,
                            "candidate_production_idx": int(production_idx),
                            "candidate_pts": int(pts),
                            "pts_offset": int(pts_offset),
                        }
                        found = True
                        break
                    if production_idx > target_idx:
                        break
                if found:
                    break

            container.close()

            if not found:
                per_target[target["rep_ts"]] = {
                    "error": "TARGET_FRAME_NOT_FOUND_AFTER_SEEK",
                    "target_frame_idx": int(target_idx),
                    "shape": [],
                    "rgb_sha256": "",
                    "raw_bytes_sha256": "",
                }

            remaining.pop(0)
    except Exception:
        try:
            container.close()
        except Exception:
            pass
        raise

    elapsed = time.perf_counter() - start

    return {
        "method": "TARGETED_RETRIEVAL_CANDIDATE",
        "wall_clock_seconds": elapsed,
        "frames_decoded": frames_decoded,
        "container_opens": container_opens,
        "ndarray_conversions": ndarray_conversions,
        "rgb_transfer_bytes": rgb_transfer_bytes,
        "representative_frames_collected": len(
            [v for v in per_target.values() if "error" not in v]
        ),
        "skipped_no_match": skipped_no_match,
        "per_target": per_target,
        "parity_error": False,
    }


# =========================================================================
# Main
# =========================================================================


def main():
    parser = argparse.ArgumentParser(
        description="C1 diagnostic: Pass 2 targeted representative-frame retrieval"
    )
    parser.add_argument("--video", required=True, help="Path to canonical video clip")
    parser.add_argument("--output", required=True, help="Output evidence directory")
    parser.add_argument(
        "--benchmark", action="store_true",
        help="Run 3-paired-run microbenchmark after parity check",
    )
    args = parser.parse_args()

    video_path = Path(args.video).resolve()
    if not video_path.is_file():
        print(f"ERROR: video not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    cfg = make_canonical_config()

    print(f"C1 diagnostic: {video_path.name}")
    print("Running shared Pass 1...")
    t0 = time.perf_counter()
    pass1 = run_shared_pass1(video_path, cfg)
    pass1_elapsed = time.perf_counter() - t0
    print(f"  Pass 1 done in {pass1_elapsed:.1f}s")
    print(f"  Segments: {len(pass1.segments)}")
    print(f"  video_fps={pass1.video_fps} frame_interval={pass1.frame_interval}")
    print(f"  sample_tolerance={pass1.sample_tolerance}")

    print("\nRunning reference sequential Pass 2...")
    ref_result = collect_reference_pass2(video_path, cfg, pass1)
    print(f"  Reference done in {ref_result['wall_clock_seconds']:.1f}s")
    print(f"  Frames sampled: {ref_result['frames_sampled']}")
    print(f"  Rep frames collected: {ref_result['representative_frames_collected']}")

    print("\nRunning candidate targeted retrieval...")
    cand_result = collect_candidate_targeted(video_path, cfg, pass1)
    if cand_result.get("parity_error"):
        print(f"  CANDIDATE ERROR: {cand_result.get('error')}")
    else:
        print(f"  Candidate done in {cand_result['wall_clock_seconds']:.1f}s")
        print(f"  Frames decoded: {cand_result.get('frames_decoded', 'N/A')}")
        print(f"  Rep frames collected: {cand_result['representative_frames_collected']}")

    parity = check_frame_parity(ref_result["per_target"], cand_result["per_target"])
    print(f"\nFrame parity: {'PASS' if parity['parity_pass'] else 'FAIL'}")

    (out / "c1_frame_parity.json").write_text(
        json.dumps(parity, indent=2, default=str), encoding="utf-8"
    )

    benchmark_results: dict[str, Any] = {"ran": False}

    if parity["parity_pass"] and args.benchmark and not cand_result.get("parity_error"):
        print("\n=== C1 Microbenchmark (3 paired runs) ===")
        ref_runs: list[float] = []
        cand_runs: list[float] = []

        for i in range(3):
            for method_name, collector, run_list in [
                ("reference", collect_reference_pass2, ref_runs),
                ("candidate", collect_candidate_targeted, cand_runs),
            ]:
                collector(video_path, cfg, pass1)  # warmup per method per round
                recorded = collector(video_path, cfg, pass1)
                run_list.append(recorded["wall_clock_seconds"])
                print(f"  Run {i+1} {method_name}: {recorded['wall_clock_seconds']:.1f}s")

        savings = compute_paired_absolute_savings(ref_runs, cand_runs)
        reductions = compute_paired_percentage_reduction(ref_runs, cand_runs)

        benchmark_results = {
            "ran": True,
            "reference_runs": ref_runs,
            "candidate_runs": cand_runs,
            "reference_median": compute_median(ref_runs),
            "candidate_median": compute_median(cand_runs),
            "reference_mean": compute_mean(ref_runs),
            "candidate_mean": compute_mean(cand_runs),
            "reference_stdev": compute_sample_stdev(ref_runs),
            "candidate_stdev": compute_sample_stdev(cand_runs),
            "paired_absolute_savings": savings,
            "paired_percentage_reductions": reductions,
            "median_seconds_saved": compute_median(savings),
            "median_reduction_percent": compute_median_reduction_percent(ref_runs, cand_runs),
            "directionally_faster_all_runs": directional_stability(ref_runs, cand_runs),
        }
        print(f"\n  Reference median: {benchmark_results['reference_median']:.1f}s")
        print(f"  Candidate median: {benchmark_results['candidate_median']:.1f}s")
        print(f"  Median reduction: {benchmark_results['median_reduction_percent']:.1f}%")
        print(f"  Directionally faster: {benchmark_results['directionally_faster_all_runs']}")

        (out / "c1_reference_runs.json").write_text(
            json.dumps({"runs": ref_runs}, indent=2), encoding="utf-8"
        )
        (out / "c1_candidate_runs.json").write_text(
            json.dumps({"runs": cand_runs}, indent=2), encoding="utf-8"
        )

    evidence: dict[str, Any] = {
        "schema_version": "1.0.0",
        "step": "18.4C",
        "candidate": "PASS2_TARGETED_REPRESENTATIVE_FRAME_RETRIEVAL",
        "shared_pass1_elapsed_seconds": pass1_elapsed,
        "segment_count": len(pass1.segments),
        "representative_timestamp_count": len(pass1.segments),
        "video_fps": pass1.video_fps,
        "frame_interval": pass1.frame_interval,
        "sample_tolerance": pass1.sample_tolerance,
        "reference_result": {k: v for k, v in ref_result.items() if k != "per_target"},
        "candidate_result": {k: v for k, v in cand_result.items() if k != "per_target"},
        "frame_parity_summary": {
            "parity_pass": parity["parity_pass"],
            "target_count_reference": parity["target_count_reference"],
            "target_count_candidate": parity["target_count_candidate"],
            "exact_sampled_timestamp_parity": parity["exact_sampled_timestamp_parity"],
            "exact_cropped_rgb_sha_parity": parity["exact_cropped_rgb_sha_parity"],
            "exact_byte_parity": parity["exact_byte_parity"],
        },
        "benchmark": benchmark_results,
    }
    (out / "c1_evidence.json").write_text(
        json.dumps(evidence, indent=2, default=str), encoding="utf-8"
    )

    print(f"\nEvidence written to {out}")


if __name__ == "__main__":
    main()
