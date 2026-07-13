#!/usr/bin/env python3
# FILE: tools/benchmark_detect.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Benchmark canonical DetectionService runs and emit portable raw and derived evidence.
#   SCOPE: Environment/config capture, metrics collection, complete output signature, summary/report.
#   DEPENDS: DetectionService, M-DETECT-METRICS, NumPy, git
#   LINKS: M-DETECT-BENCHMARK, V-PERF-DETECT-SHORT-BENCHMARK
#   ROLE: SCRIPT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   compute_output_signature - hash complete detector scores and segments
#   compute_score_distribution - NumPy percentiles over the complete score series
#   evaluate_invariants - explicit metric and output artifact checks
#   rank_bottlenecks - rank measured non-overlapping detector stages
#   load_project_config - load canonical project config for runtime preflight
#   run_benchmark - execute the canonical DetectionService route with telemetry
#   main - CLI artifact writer
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Persist complete scores, resolved backend, invariants, and portable reports.
# END_CHANGE_SUMMARY
"""Phase 18 canonical detect benchmark tool."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


def _find_git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parent.parent,
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
    except Exception:
        return "unknown"


def _find_git_branch() -> str:
    try:
        return subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=Path(__file__).resolve().parent.parent,
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
    except Exception:
        return "unknown"


def _collect_environment(project_dir: Path) -> dict[str, Any]:
    import numpy as np
    env = {
        "head_sha": _find_git_head(),
        "branch": _find_git_branch(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_machine": platform.machine(),
        "cpu_count_logical": os.cpu_count(),
        "numpy_version": np.__version__,
        "project_description": project_dir.name,
    }
    # OpenCV
    try:
        import cv2
        env["opencv_version"] = cv2.__version__
    except Exception:
        env["opencv_version"] = None
    # PyAV
    try:
        import av
        env["pyav_version"] = av.__version__
    except Exception:
        env["pyav_version"] = None
    # PySide6
    try:
        from PySide6.QtCore import qVersion
        env["qt_version"] = qVersion()
    except Exception:
        env["qt_version"] = None
    # RAM (Windows)
    try:
        import psutil
        env["ram_total_gb"] = round(psutil.virtual_memory().total / 1e9, 1)
    except Exception:
        env["ram_total_gb"] = None
    return env


def compute_output_signature(
    score_timestamps: list[float],
    score_values: list[float],
    segments: list[dict],
) -> dict[str, Any]:
    """Canonical detector output signature for quality comparison."""
    canonical = {
        "score_timestamps": score_timestamps,
        "score_values": score_values,
        "segments": [
            {
                "start": s.get("start", 0),
                "end": s.get("end", 0),
                "representative_timestamp": s.get("representative_timestamp", 0),
                "image_path": s.get("image", ""),
            }
            for s in segments
        ],
    }
    raw = json.dumps(canonical, sort_keys=True, default=str).encode("utf-8")
    canonical["canonical_sha256"] = hashlib.sha256(raw).hexdigest()
    return canonical


def compute_score_distribution(score_values: list[float]) -> dict[str, float | int | None]:
    """Compute NumPy linear percentiles from the complete score series."""
    import numpy as np

    if not score_values:
        return {"count": 0, "p50": None, "p90": None, "p95": None, "p99": None, "max": None}
    values = np.asarray(score_values, dtype=np.float64)
    return {
        "count": int(values.size),
        "p50": float(np.percentile(values, 50)),
        "p90": float(np.percentile(values, 90)),
        "p95": float(np.percentile(values, 95)),
        "p99": float(np.percentile(values, 99)),
        "max": float(np.max(values)),
    }


def evaluate_invariants(metrics: dict[str, Any], png_count: int) -> dict[str, dict[str, Any]]:
    counters = metrics.get("counters", {})
    gauges = metrics.get("gauges", {})

    def check(passed: bool, detail: str) -> dict[str, Any]:
        return {"status": "PASS" if passed else "FAIL", "detail": detail}

    frames_sampled = counters.get("frames_sampled", 0)
    pass2_sampled = counters.get("pass2_frames_sampled", 0)
    conversions = counters.get("ndarray_conversions", 0)
    representative_frames = counters.get("representative_frames", 0)
    invariants = {
        "features_equal_frames_sampled": check(
            counters.get("features_full", 0) + counters.get("features_quick", 0) == frames_sampled,
            "features_full + features_quick == frames_sampled",
        ),
        "decoded_at_least_conversions": check(
            counters.get("frames_decoded", 0) >= conversions,
            "frames_decoded >= ndarray_conversions",
        ),
        "conversions_cover_sampled_passes": check(
            conversions >= frames_sampled + pass2_sampled,
            "valid for current OpenCV/PyAV full-frame sampling implementations",
        ),
        "representative_frames_positive": check(
            representative_frames > 0, "representative_frames > 0"
        ),
        "representative_bytes_positive": check(
            representative_frames == 0 or counters.get("representative_frame_bytes", 0) > 0,
            "representative_frame_bytes > 0 when representative frames exist",
        ),
        "screenshots_match_png_count": check(
            counters.get("screenshots_written", 0) == png_count,
            f"screenshots_written == PNG count ({png_count})",
        ),
    }
    before = gauges.get("rss_before_mb", 0)
    peak = gauges.get("rss_peak_mb", 0)
    after = gauges.get("rss_after_mb", 0)
    if before == 0 and peak == 0 and after == 0:
        invariants["rss_peak_bounds"] = {"status": "SKIPPED", "detail": "psutil unavailable"}
    else:
        invariants["rss_peak_bounds"] = check(
            peak >= before and peak >= after,
            "rss_peak_mb >= rss_before_mb and rss_peak_mb >= rss_after_mb",
        )
    return invariants


def rank_bottlenecks(metrics: dict[str, Any], detect_elapsed: float) -> list[dict[str, Any]]:
    """Rank measured non-overlapping stage timers against detect elapsed."""
    timers = metrics.get("timers", {})
    stage_names = [
        "roi", "extract_features", "visual_distance", "threshold", "debounce",
        "pass2_collect", "pass2_dedupe", "pass2_screenshots",
    ]
    ranked = sorted(
        ((name, float(timers.get(name, 0))) for name in stage_names),
        key=lambda item: item[1], reverse=True,
    )
    rows = [
        {
            "rank": rank,
            "stage": name,
            "elapsed_seconds": elapsed,
            "denominator": "detect_elapsed_seconds",
            "percentage": elapsed / detect_elapsed * 100 if detect_elapsed else 0,
            "measurement_type": "accumulated stage timer",
            "notes": "non-overlapping with the other listed detector stage timers",
        }
        for rank, (name, elapsed) in enumerate(ranked, 1)
    ]
    measured = sum(elapsed for _, elapsed in ranked)
    residual = max(0.0, detect_elapsed - measured)
    rows.append({
        "rank": len(rows) + 1,
        "stage": "unattributed_residual",
        "elapsed_seconds": residual,
        "denominator": "detect_elapsed_seconds",
        "percentage": residual / detect_elapsed * 100 if detect_elapsed else 0,
        "measurement_type": "derived residual",
        "notes": "decode/open/service/persistence and other uninstrumented work; not a measured timer",
    })
    return rows


def load_project_config(project_location: Path) -> dict[str, Any]:
    """Load canonical Project and extract effective detection config."""
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
    from video2pptx.infrastructure.persistence.file_project_repository import FileProjectRepository
    repo = FileProjectRepository()
    loaded = repo.load(project_location)
    p = loaded.project
    dc = p.detection
    return {
        "video_path": p.video_path,
        "sample_fps": dc.sample_fps,
        "decoder_backend": dc.decoder_backend,
        "slide_roi": dc.slide_roi,
        "ignore_rois": list(dc.ignore_rois),
        "threshold": dc.threshold,
        "min_slide_duration": dc.min_slide_duration,
        "min_stable_duration": dc.min_stable_duration,
        "dedupe_enabled": dc.dedupe_enabled,
    }


def run_benchmark(
    project_location: Path,
    output_dir: Path,
    *,
    profile: bool = False,
    keep_workdir: bool = False,
) -> dict[str, Any]:
    import sys as _sys
    _sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

    from video2pptx.application.base import ServiceContext
    from video2pptx.application.cancellation import CancellationToken
    from video2pptx.application.services.detection_service import DetectionService
    from video2pptx.bootstrap.application import ApplicationServices
    from video2pptx.detection_metrics import collect
    from video2pptx.infrastructure.persistence.file_project_repository import FileProjectRepository
    from video2pptx.video_decode import select_backend

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load source project
    repo = FileProjectRepository()
    source = repo.load(project_location)
    project = source.project
    effective_config = {
        "video_path": Path(project.video_path).name,
        "sample_fps": project.detection.sample_fps,
        "decoder_backend": project.detection.decoder_backend,
        "slide_roi": project.detection.slide_roi,
        "ignore_rois": list(project.detection.ignore_rois),
        "threshold": project.detection.threshold,
        "min_slide_duration": project.detection.min_slide_duration,
        "min_stable_duration": project.detection.min_stable_duration,
        "dedupe_enabled": project.detection.dedupe_enabled,
        "quick_mode": False,
        "effective_backend": select_backend(project.detection.decoder_backend),
    }

    # Save effective config
    (output_dir / "effective_config.json").write_text(
        json.dumps(effective_config, indent=2), encoding="utf-8"
    )

    # Create isolated benchmark project (preserve external video reference)
    bench_location = output_dir / "bench-project"
    if bench_location.exists():
        shutil.rmtree(bench_location)
    project.output_dir = str(bench_location)
    repo.create(bench_location, project)

    # Build services
    services = ApplicationServices()
    ctx = ServiceContext(repository=services.repository, cancellation=CancellationToken())
    detector = services.detection_service._detector
    service = DetectionService(detector=detector, context=ctx)

    # Run with metrics collection
    with collect() as metrics:
        start = time.perf_counter()
        try:
            result = service.execute(bench_location, video_path=None)
            elapsed = time.perf_counter() - start
        except Exception as e:
            elapsed = time.perf_counter() - start
            return {"error": str(e), "elapsed": elapsed}

    # Collect results
    data = result.data or {}
    completed = repo.load(bench_location).project
    score_ts = list(completed.score_timestamps)
    score_vals = list(completed.score_values)
    slides_count = data.get("slides_count", 0)
    video_dur = data.get("video_duration", 0)

    # Also read slides.json for post-run data
    slides_json_path = bench_location / "slides.json"
    slides_json_data = []
    if slides_json_path.exists():
        slides_json_data = json.loads(slides_json_path.read_text("utf-8")).get("slides", [])

    sig = compute_output_signature(score_ts, score_vals, slides_json_data)
    png_count = len(list((bench_location / "slides").glob("*.png")))
    metrics_data = metrics.to_dict()

    return {
        "elapsed": elapsed,
        "metrics": metrics_data,
        "effective_config": effective_config,
        "output_signature": sig,
        "slides_count": slides_count,
        "video_duration": video_dur,
        "score_timestamps_sample": score_ts[:10] if score_ts else [],
        "score_values_sample": score_vals[:10] if score_vals else [],
        "score_distribution": compute_score_distribution(score_vals),
        "change_count": None,
        "change_count_note": "not directly exposed by the canonical DetectionService result",
        "png_count": png_count,
        "invariants": evaluate_invariants(metrics_data, png_count),
        "ranked_bottlenecks": rank_bottlenecks(metrics_data, elapsed),
    }


def main():
    parser = argparse.ArgumentParser(description="Phase 18 detect benchmark")
    parser.add_argument("--project", required=True, help="Canonical project directory")
    parser.add_argument("--output", required=True, help="Benchmark output directory")
    parser.add_argument("--profile", action="store_true", help="Enable cProfile")
    parser.add_argument("--keep-workdir", action="store_true", help="Preserve benchmark workdir")
    parser.add_argument("--benchmark-id", default="", help="Stable benchmark identifier")
    parser.add_argument("--source-description", default="local source media")
    parser.add_argument("--clip-start-seconds", type=float, default=0.0)
    parser.add_argument("--clip-requested-duration-seconds", type=float, default=0.0)
    parser.add_argument("--clip-sha256", default="")
    args = parser.parse_args()

    project_path = Path(args.project).resolve()
    if not project_path.is_dir():
        print(f"ERROR: project directory not found: {project_path}", file=sys.stderr)
        sys.exit(1)

    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)

    print("=== Phase 18 Detect Benchmark ===")
    print(f"Project: {project_path}")
    print(f"Output:  {out}")

    # Check video file
    config = load_project_config(project_path)
    video_path = Path(config["video_path"])
    if not video_path.is_file() and not video_path.is_absolute():
        video_path = project_path / config["video_path"]
    if not video_path.is_file():
        print(f"ERROR: video not found: {video_path}", file=sys.stderr)
        print("Configured video_path in project:", config["video_path"])
        sys.exit(1)
    print(f"Video:   {video_path}")
    print(f"Config:  sample_fps={config['sample_fps']} threshold={config['threshold']} "
          f"backend={config['decoder_backend']}")

    # Environment
    env = _collect_environment(project_path)
    (out / "environment.json").write_text(json.dumps(env, indent=2), encoding="utf-8")

    # Profile
    if args.profile:
        import cProfile
        profiler = cProfile.Profile()
        profiler.enable()

    # Run benchmark
    start = time.perf_counter()
    result = run_benchmark(project_path, out, profile=args.profile, keep_workdir=args.keep_workdir)
    wall_clock = time.perf_counter() - start

    if args.profile:
        import pstats as _ps
        profiler.disable()
        stats_path = out / "profile.pstats"
        profiler.dump_stats(str(stats_path))
        txt_path = out / "profile.txt"
        with open(txt_path, "w") as f:
            ps = _ps.Stats(profiler, stream=f)
            ps.strip_dirs()
            ps.sort_stats("cumtime")
            ps.print_stats(40)

    # Write artifacts
    (out / "metrics.json").write_text(
        json.dumps(result.get("metrics", {}), indent=2, default=str), encoding="utf-8"
    )
    (out / "output_signature.json").write_text(
        json.dumps(result.get("output_signature", {}), indent=2, default=str), encoding="utf-8"
    )
    comparison = {
        "baseline": True,
        "compared_to": None,
        "wall_clock": wall_clock,
        "detect_elapsed": result.get("elapsed", 0),
    }
    if not args.keep_workdir:
        import shutil
        shutil.rmtree(out / "bench-project", ignore_errors=True)

    (out / "comparison.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")

    video_duration = float(result.get("video_duration", 0))
    detect_elapsed = float(result.get("elapsed", 0))
    frames_sampled = result.get("metrics", {}).get("counters", {}).get("frames_sampled", 0)
    summary = {
        "benchmark_id": args.benchmark_id or out.name,
        "source_description": args.source_description,
        "clip_start_seconds": args.clip_start_seconds,
        "clip_requested_duration_seconds": args.clip_requested_duration_seconds,
        "clip_actual_duration_seconds": video_duration,
        "clip_sha256": args.clip_sha256,
        "head_sha": env["head_sha"],
        "branch": env["branch"],
        "wall_clock_seconds": wall_clock,
        "detect_elapsed_seconds": detect_elapsed,
        "video_duration_seconds": video_duration,
        "real_time_multiplier": detect_elapsed / video_duration if video_duration else None,
        "processing_x_realtime": video_duration / detect_elapsed if detect_elapsed else None,
        "effective_sampled_fps": frames_sampled / video_duration if video_duration else None,
        "effective_backend": result.get("effective_config", {}).get("effective_backend"),
        "slides_count": result.get("slides_count", 0),
        "change_count": result.get("change_count"),
        "change_count_note": result.get("change_count_note"),
        "score_distribution": result.get("score_distribution", {}),
        "invariants": result.get("invariants", {}),
        "ranked_bottlenecks": result.get("ranked_bottlenecks", []),
        "decision": "PENDING_AGGREGATE",
    }
    (out / "benchmark_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_lines = [
        f"# {summary['benchmark_id']}", "",
        f"- Detect elapsed: {detect_elapsed:.6f} s",
        f"- Video duration: {video_duration:.6f} s",
        f"- Real-time multiplier: {summary['real_time_multiplier']}",
        f"- Effective backend: {summary['effective_backend']}",
        f"- Output signature: {result.get('output_signature', {}).get('canonical_sha256', 'N/A')}",
        "", "## Invariants", "",
    ]
    report_lines.extend(
        f"- {name}: {value['status']} - {value['detail']}"
        for name, value in summary["invariants"].items()
    )
    (out / "benchmark_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    # Summary
    sig = result.get("output_signature", {})
    metrics = result.get("metrics", {})
    timers = metrics.get("timers", {})
    counters = metrics.get("counters", {})

    print("\n=== Results ===")
    print(f"Wall clock:     {wall_clock:.1f}s")
    print(f"Detect elapsed: {result.get('elapsed', 0):.1f}s")
    print(f"Slides:         {result.get('slides_count', 0)}")
    print(f"Video duration: {result.get('video_duration', 0):.1f}s")
    print(f"Signature:      {sig.get('canonical_sha256', 'N/A')}")
    print("\nTimers (s):")
    for name, val in sorted(timers.items()):
        if val > 0:
            print(f"  {name}: {val:.2f}")
    print("\nCounters:")
    for name, val in sorted(counters.items()):
        if val > 0:
            print(f"  {name}: {val}")

    if "error" in result:
        print(f"\nERROR: {result['error']}", file=sys.stderr)


if __name__ == "__main__":
    main()
