#!/usr/bin/env python3
# FILE: tools/benchmark_detect.py
# VERSION: 2.2.0
# START_MODULE_CONTRACT
#   PURPOSE: Benchmark canonical DetectionService runs and emit portable raw and derived evidence.
#   SCOPE: Environment/config capture, metrics collection, complete output signature, summary/report,
#          aggregate evidence generation from artifact sets, deterministic pure helpers.
#   DEPENDS: DetectionService, M-DETECT-METRICS, NumPy, git
#   LINKS: M-DETECT-BENCHMARK, V-PERF-DETECT-SHORT-BENCHMARK
#   ROLE: SCRIPT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   HISTORICAL_CANONICAL_SIGNATURE - accepted sha256 from the historical recovered-tree run
#   STAGE_NAMES - canonical non-overlapping detector stage timer names
#   PROFILE_FUNCTION_MATCHERS - stable labels and cProfile descriptor markers
#   compute_output_signature - hash complete detector scores and segments
#   compute_score_distribution - NumPy percentiles over the complete score series
#   compute_derived_metrics - real_time_multiplier, processing_x_realtime, effective_sampled_fps
#   aggregate_signatures - run signature identity and historical match
#   select_median_run - median run selection by detect_elapsed_seconds
#   compute_stage_accounting - measured_stage_total, residual from metrics timers only
#   extract_profile_supporting_evidence - parse selected cumulative cProfile entries
#   resolve_recovered_master_base - validate claimed base against git merge-base
#   sanitize_committed_path - strip absolute prefix, return portable identifier
#   evaluate_invariants - explicit metric and output artifact checks
#   rank_bottlenecks - rank measured non-overlapping detector stages
#   load_project_config - load canonical project config for runtime preflight
#   run_benchmark - execute the canonical DetectionService route with telemetry
#   build_aggregate_evidence - consume artifact sets and produce complete aggregate document
#   main - CLI artifact writer
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v2.2.0 - Updated STAGE_NAMES: replaced pass2_collect with pass1_decode_or_frame_advance,
#                pass2_decode_or_frame_advance, pass2_match_and_collect; pass2_collect excluded from
#                canonical non-overlapping stages to prevent double-count.
# END_CHANGE_SUMMARY
"""Phase 18 canonical detect benchmark tool."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

HISTORICAL_CANONICAL_SIGNATURE = "8cc06c6accb055fb6fed461f2f4a96f0b288ef864b9423000b6f59d9ab56bc85"

# Canonical non-overlapping stage timers.
# pass2_collect is intentionally excluded — it is a legacy mixed timer whose
# children (pass2_decode_or_frame_advance + pass2_match_and_collect) are
# measured independently. Including pass2_collect here would double-count
# its work against detect_elapsed_seconds.
STAGE_NAMES = [
    "pass1_decode_or_frame_advance", "roi", "extract_features",
    "visual_distance", "threshold", "debounce",
    "pass2_decode_or_frame_advance", "pass2_match_and_collect",
    "pass2_dedupe", "pass2_screenshots",
]

PROFILE_FUNCTION_MATCHERS = {
    "Packet.decode": "decode' of 'av.packet.Packet' objects",
    "pyav_iter_frames": "(pyav_iter_frames)",
    "to_ndarray": "to_ndarray' of 'av.video.frame.VideoFrame' objects",
    "extract_features": "(extract_features)",
    "compute_histogram": "(compute_histogram)",
    "cv2_calc_hist": "(cv2_calc_hist)",
    "numpy histogram": "_histograms_impl.py:",
    "cv2_to_gray": "(cv2_to_gray)",
}

_PROFILE_LINE = re.compile(
    r"^\s*(?P<calls>\d+(?:/\d+)?)\s+"
    r"(?P<self_seconds>\d+(?:\.\d+)?)\s+"
    r"\d+(?:\.\d+)?\s+"
    r"(?P<cumulative_seconds>\d+(?:\.\d+)?)\s+"
    r"\d+(?:\.\d+)?\s+(?P<descriptor>.+?)\s*$"
)


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
    try:
        import cv2
        env["opencv_version"] = cv2.__version__
    except Exception:
        env["opencv_version"] = None
    try:
        import av
        env["pyav_version"] = av.__version__
    except Exception:
        env["pyav_version"] = None
    try:
        from PySide6.QtCore import qVersion
        env["qt_version"] = qVersion()
    except Exception:
        env["qt_version"] = None
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


def compute_derived_metrics(
    detect_elapsed: float,
    video_duration: float,
    frames_sampled: int,
) -> dict[str, float | None]:
    """Derive real_time_multiplier, processing_x_realtime, effective_sampled_fps."""
    return {
        "real_time_multiplier": detect_elapsed / video_duration if video_duration else None,
        "processing_x_realtime": video_duration / detect_elapsed
            if detect_elapsed and video_duration else None,
        "effective_sampled_fps": frames_sampled / video_duration if video_duration else None,
    }


def aggregate_signatures(
    signatures: list[dict[str, Any]],
    historical_canonical: str = HISTORICAL_CANONICAL_SIGNATURE,
) -> dict[str, Any]:
    """Check identity among run signatures and match against historical canonical."""
    run_shas = [s.get("canonical_sha256", "") for s in signatures]
    first = run_shas[0] if run_shas else ""
    return {
        "run_signatures": run_shas,
        "signature_identity": all(s == first for s in run_shas) if run_shas else False,
        "historical_signature": historical_canonical,
        "historical_signature_match": all(s == historical_canonical for s in run_shas) if run_shas else False,
    }


def select_median_run(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Return the run whose detect_elapsed_seconds is the median of all runs."""
    if not runs:
        return {}
    sorted_runs = sorted(runs, key=lambda r: r.get("detect_elapsed_seconds", 0))
    median_idx = len(sorted_runs) // 2
    return sorted_runs[median_idx]


def compute_stage_accounting(
    timers: dict[str, float],
    detect_elapsed: float,
    profile_evidence: Any = None,
) -> dict[str, Any]:
    """Calculate stage accounting from canonical timers only.

    profile_evidence is accepted but intentionally IGNORED — it must never
    alter measured_stage_total, residual, or stage percentages.
    """
    measured = [float(timers.get(name, 0)) for name in STAGE_NAMES]
    measured_total = sum(measured)
    residual = max(0.0, detect_elapsed - measured_total)
    return {
        "measured_stage_total": measured_total,
        "residual_seconds": residual,
        "residual_percentage": residual / detect_elapsed * 100 if detect_elapsed else 0,
        "_profile_evidence_ignored": True,
    }


# START_CONTRACT: extract_profile_supporting_evidence
#   PURPOSE: Extract selected cumulative-time entries from deterministic cProfile text.
#   INPUTS: { profile_text: str - pstats text sorted by cumulative time }
#   OUTPUTS: { dict[str, dict[str, Any]] - supporting entries keyed by stable function label }
#   SIDE_EFFECTS: none
#   LINKS: M-DETECT-BENCHMARK, V-PERF-DETECT-SHORT-BENCHMARK
# END_CONTRACT: extract_profile_supporting_evidence
def extract_profile_supporting_evidence(profile_text: str) -> dict[str, dict[str, Any]]:
    """Parse selected supporting entries without contributing to stage accounting."""
    evidence: dict[str, dict[str, Any]] = {}
    for line in profile_text.splitlines():
        match = _PROFILE_LINE.match(line)
        if not match:
            continue
        descriptor = match.group("descriptor")
        for function, marker in PROFILE_FUNCTION_MATCHERS.items():
            if marker not in descriptor:
                continue
            if function == "numpy histogram" and not descriptor.endswith("(histogram)"):
                continue
            evidence[function] = {
                "function": function,
                "cumulative_seconds": float(match.group("cumulative_seconds")),
                "calls": int(match.group("calls").split("/", 1)[0]),
                "self_seconds": float(match.group("self_seconds")),
            }
            break
    return evidence


# START_CONTRACT: resolve_recovered_master_base
#   PURPOSE: Validate a claimed recovered base as a commit and exact measurement/upstream merge-base.
#   INPUTS: { benchmark_code_head: str - measurement commit, claimed_base: str - provenance SHA, upstream_ref: str - comparison ref, repo_dir: Path | None - repository root }
#   OUTPUTS: { str - validated full recovered-master-base SHA }
#   SIDE_EFFECTS: invokes read-only git commands
#   LINKS: M-DETECT-BENCHMARK, V-PERF-DETECT-SHORT-BENCHMARK
# END_CONTRACT: resolve_recovered_master_base
def resolve_recovered_master_base(
    benchmark_code_head: str,
    claimed_base: str,
    upstream_ref: str = "origin/master",
    repo_dir: Path | None = None,
) -> str:
    """Return claimed_base only when git proves it is the exact merge-base commit."""
    cwd = repo_dir or Path(__file__).resolve().parent.parent
    if not re.fullmatch(r"[0-9a-f]{40}", claimed_base):
        raise ValueError("recovered master base must be a full lowercase commit SHA")
    subprocess.run(
        ["git", "cat-file", "-e", f"{claimed_base}^{{commit}}"],
        cwd=cwd,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    merge_base = subprocess.check_output(
        ["git", "merge-base", benchmark_code_head, upstream_ref],
        cwd=cwd,
        text=True,
    ).strip()
    if merge_base != claimed_base:
        raise ValueError(
            f"claimed recovered master base {claimed_base} does not match merge-base {merge_base}"
        )
    return claimed_base


def sanitize_committed_path(path: str, base_dir: str | None = None) -> str:
    """Strip absolute prefix, return a portable relative identifier."""
    p = Path(path)
    if p.is_absolute():
        return p.name
    if path.startswith("/"):
        return Path(path).name
    return str(Path(path).as_posix())


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
    ranked = sorted(
        ((name, float(timers.get(name, 0))) for name in STAGE_NAMES),
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
        "video_identifier": Path(project.video_path).name,
        "sample_fps": project.detection.sample_fps,
        "configured_backend": project.detection.decoder_backend,
        "slide_roi": project.detection.slide_roi,
        "ignore_rois": list(project.detection.ignore_rois),
        "threshold": project.detection.threshold,
        "min_slide_duration": project.detection.min_slide_duration,
        "min_stable_duration": project.detection.min_stable_duration,
        "dedupe_enabled": project.detection.dedupe_enabled,
        "quick_mode": False,
        "effective_backend": select_backend(project.detection.decoder_backend),
    }

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
    derived = compute_derived_metrics(elapsed, video_dur, metrics_data.get("counters", {}).get("frames_sampled", 0))

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
        "change_count": "NOT_EXPOSED",
        "change_count_note": "not directly exposed by the canonical DetectionService result",
        "png_count": png_count,
        "invariants": evaluate_invariants(metrics_data, png_count),
        "ranked_bottlenecks": rank_bottlenecks(metrics_data, elapsed),
        "derived_metrics": derived,
    }


def build_aggregate_evidence(
    benchmark_sequence: str,
    branch: str,
    benchmark_code_head: str,
    evidence_builder_head: str,
    benchmark_code_tree: str,
    recovered_master_base: str,
    clip: dict[str, Any],
    warmup_performed: bool,
    recorded_runs: list[dict[str, Any]],
    profile_run: dict[str, Any] | None,
    profile_text: str = "",
    historical_canonical: str = HISTORICAL_CANONICAL_SIGNATURE,
) -> dict[str, Any]:
    """Build complete aggregate evidence document from artifact sets."""
    if not recorded_runs:
        return {"error": "no recorded runs provided"}

    run_elapsed = [r.get("detect_elapsed_seconds", 0) for r in recorded_runs]
    median_run = select_median_run(recorded_runs)
    median_metrics = median_run.get("metrics", {})

    sigs = aggregate_signatures(
        [r.get("output_signature", {}) for r in recorded_runs],
        historical_canonical,
    )

    med_timers = median_metrics.get("timers", {})
    med_elapsed = median_run.get("detect_elapsed_seconds", 0)
    accounting = compute_stage_accounting(med_timers, med_elapsed)
    profile_sig = profile_run.get("output_signature", {}).get("canonical_sha256", "") if profile_run else ""

    def _counter_val(run: dict, name: str) -> int:
        return run.get("metrics", {}).get("counters", {}).get(name, 0)

    median_counters = median_metrics.get("counters", {})
    median_gauges = median_metrics.get("gauges", {})
    rss_available = any(
        median_gauges.get(k, 0) != 0
        for k in ("rss_before_mb", "rss_peak_mb", "rss_after_mb")
    )

    return {
        "benchmark_sequence": benchmark_sequence,
        "benchmark_code_head": benchmark_code_head,
        "evidence_builder_head": evidence_builder_head,
        "benchmark_code_tree": benchmark_code_tree,
        "recovered_master_base": recovered_master_base,
        "branch": branch,
        "clip": {
            "identifier": clip.get("identifier", ""),
            "sha256": clip.get("sha256", ""),
            "duration_seconds": clip.get("duration_seconds", 0),
            "resolution": clip.get("resolution", ""),
            "codec": clip.get("codec", ""),
            "fps": clip.get("fps", 0),
        },
        "warmup_performed": warmup_performed,
        "recorded_run_count": len(recorded_runs),
        "effective_config": median_run.get("effective_config", {}),
        "runs": [
            {
                "id": r.get("id", ""),
                "detect_elapsed_seconds": r.get("detect_elapsed_seconds", 0),
                "wall_clock_seconds": r.get("wall_clock_seconds", 0),
                "real_time_multiplier": r.get("derived_metrics", {}).get("real_time_multiplier"),
                "processing_x_realtime": r.get("derived_metrics", {}).get("processing_x_realtime"),
                "effective_sampled_fps": r.get("derived_metrics", {}).get("effective_sampled_fps"),
                "canonical_signature": r.get("output_signature", {}).get("canonical_sha256", ""),
            }
            for r in recorded_runs
        ],
        "summary": {
            "min_detect_elapsed_seconds": min(run_elapsed),
            "median_detect_elapsed_seconds": statistics.median(run_elapsed),
            "max_detect_elapsed_seconds": max(run_elapsed),
            "mean_detect_elapsed_seconds": statistics.mean(run_elapsed),
            "std_dev_seconds": statistics.stdev(run_elapsed) if len(run_elapsed) >= 2 else 0.0,
            "median_run_id": median_run.get("id", ""),
        },
        "signatures": {
            "run_signatures": sigs["run_signatures"],
            "signature_identity": sigs["signature_identity"],
            "historical_signature": historical_canonical,
            "historical_signature_match": sigs["historical_signature_match"],
            "profile_signature": profile_sig,
            "profile_signature_match": profile_sig == historical_canonical if profile_sig else False,
        },
        "quality": {
            "slides_count": median_run.get("slides_count", 0),
            "screenshots_written": median_counters.get("screenshots_written", 0),
            "actual_png_count": median_run.get("png_count", 0),
            "change_count": "NOT_EXPOSED",
            "score_distribution": median_run.get("score_distribution", {}),
        },
        "median_run_stage_accounting": {
            "stages": rank_bottlenecks(median_metrics, med_elapsed),
            "measured_stage_total": accounting["measured_stage_total"],
            "residual_seconds": accounting["residual_seconds"],
            "residual_percentage": accounting["residual_percentage"],
        },
        "profile_supporting_evidence": extract_profile_supporting_evidence(profile_text),
        "rss": {
            "availability": rss_available,
            "status": "SKIPPED_PSUTIL_UNAVAILABLE" if not rss_available else "AVAILABLE",
            "rss_before_mb": median_gauges.get("rss_before_mb", 0),
            "rss_peak_mb": median_gauges.get("rss_peak_mb", 0),
            "rss_after_mb": median_gauges.get("rss_after_mb", 0),
        },
        "counter_invariants": {
            "features_full": median_counters.get("features_full", 0),
            "features_quick": median_counters.get("features_quick", 0),
            "frames_sampled": median_counters.get("frames_sampled", 0),
            "frames_decoded": median_counters.get("frames_decoded", 0),
            "ndarray_conversions": median_counters.get("ndarray_conversions", 0),
            "pass2_frames_sampled": median_counters.get("pass2_frames_sampled", 0),
            "representative_frames": median_counters.get("representative_frames", 0),
            "representative_frame_bytes": median_counters.get("representative_frame_bytes", 0),
            "screenshots_written": median_counters.get("screenshots_written", 0),
            "rgb_transfer_bytes": median_gauges.get("rgb_transfer_bytes", 0),
        },
        "f0088": {
            "observed": median_run.get("slides_count", 0) > median_run.get("png_count", 0),
            "exact_fact": f"slides_count={median_run.get('slides_count', 0)} > png_count={median_run.get('png_count', 0)}",
            "finding_status": "OPEN",
        },
        "decision": "PENDING",
        "optimization_selected": False,
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
        shutil.rmtree(out / "bench-project", ignore_errors=True)

    (out / "comparison.json").write_text(json.dumps(comparison, indent=2), encoding="utf-8")

    video_duration = float(result.get("video_duration", 0))
    detect_elapsed = float(result.get("elapsed", 0))
    derived = result.get("derived_metrics", {})
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
        "real_time_multiplier": derived.get("real_time_multiplier"),
        "processing_x_realtime": derived.get("processing_x_realtime"),
        "effective_sampled_fps": derived.get("effective_sampled_fps"),
        "effective_backend": result.get("effective_config", {}).get("effective_backend"),
        "slides_count": result.get("slides_count", 0),
        "change_count": "NOT_EXPOSED",
        "change_count_note": result.get("change_count_note"),
        "score_distribution": result.get("score_distribution", {}),
        "invariants": result.get("invariants", {}),
        "ranked_bottlenecks": result.get("ranked_bottlenecks", []),
        "decision": "PENDING",
    }
    (out / "benchmark_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    report_lines = [
        f"# {summary['benchmark_id']}", "",
        f"- Detect elapsed: {detect_elapsed:.6f} s",
        f"- Video duration: {video_duration:.6f} s",
        f"- Real-time multiplier: {derived.get('real_time_multiplier')}",
        f"- Effective backend: {derived.get('effective_backend')}",
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
    print(f"Backend:        {result.get('effective_config', {}).get('effective_backend', 'unknown')}")
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
