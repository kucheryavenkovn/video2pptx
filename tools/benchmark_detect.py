#!/usr/bin/env python3
"""Phase 18 detect benchmark tool.

Measures DetectionService wall-clock time, collects metrics/artifacts,
produces output signature for quality comparison.

Usage:
    python tools/benchmark_detect.py --project <path> --output <dir> [--profile] [--keep-workdir]
"""

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


def _collect_environment(project_dir: Path) -> dict[str, Any]:
    import numpy as np
    env = {
        "head_sha": _find_git_head(),
        "branch": os.environ.get("GIT_BRANCH", ""),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_machine": platform.machine(),
        "cpu_count_logical": os.cpu_count(),
        "numpy_version": np.__version__,
        "project_location": str(project_dir.resolve()),
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

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load source project
    repo = FileProjectRepository()
    source = repo.load(project_location)
    project = source.project
    effective_config = {
        "video_path": project.video_path,
        "sample_fps": project.detection.sample_fps,
        "decoder_backend": project.detection.decoder_backend,
        "slide_roi": project.detection.slide_roi,
        "ignore_rois": list(project.detection.ignore_rois),
        "threshold": project.detection.threshold,
        "min_slide_duration": project.detection.min_slide_duration,
        "min_stable_duration": project.detection.min_stable_duration,
        "dedupe_enabled": project.detection.dedupe_enabled,
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
    score_ts = data.get("score_timestamps", [])
    score_vals = data.get("score_values", [])
    slides_count = data.get("slides_count", 0)
    video_dur = data.get("video_duration", 0)

    # Also read slides.json for post-run data
    slides_json_path = bench_location / "slides.json"
    slides_json_data = []
    if slides_json_path.exists():
        slides_json_data = json.loads(slides_json_path.read_text("utf-8")).get("slides", [])

    sig = compute_output_signature(score_ts, score_vals, slides_json_data)

    return {
        "elapsed": elapsed,
        "metrics": metrics.to_dict(),
        "effective_config": effective_config,
        "output_signature": sig,
        "slides_count": slides_count,
        "video_duration": video_dur,
        "score_timestamps_sample": score_ts[:10] if score_ts else [],
        "score_values_sample": score_vals[:10] if score_vals else [],
    }


def main():
    parser = argparse.ArgumentParser(description="Phase 18 detect benchmark")
    parser.add_argument("--project", required=True, help="Canonical project directory")
    parser.add_argument("--output", required=True, help="Benchmark output directory")
    parser.add_argument("--profile", action="store_true", help="Enable cProfile")
    parser.add_argument("--keep-workdir", action="store_true", help="Preserve benchmark workdir")
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
