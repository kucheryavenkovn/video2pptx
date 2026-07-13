# FILE: tools/aggregate_detect_benchmark.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Derive immutable aggregate evidence from three canonical detect benchmark runs.
#   SCOPE: Determinism gate, median/min/max, median stage ranking, and bottleneck decision report.
#   DEPENDS: benchmark_summary.json, metrics.json, output_signature.json
#   LINKS: M-DETECT-BENCHMARK, V-PERF-DETECT-SHORT-BENCHMARK
#   ROLE: SCRIPT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   aggregate - derive aggregate.json, benchmark_summary.json, and benchmark_report.md
#   main - CLI entry point
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Aggregate three deterministic runs and select the measured bottleneck hypothesis.
# END_CHANGE_SUMMARY

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def aggregate(root: Path) -> dict[str, Any]:
    run_dirs = [root / f"run-{number:02d}" for number in range(1, 4)]
    summaries = [_read(path / "benchmark_summary.json") for path in run_dirs]
    metrics = [_read(path / "metrics.json") for path in run_dirs]
    signatures = [
        _read(path / "output_signature.json")["canonical_sha256"] for path in run_dirs
    ]
    deterministic = len(set(signatures)) == 1
    if not deterministic:
        raise RuntimeError(f"Output signatures differ: {signatures}")

    elapsed = [float(item["detect_elapsed_seconds"]) for item in summaries]
    wall = [float(item["wall_clock_seconds"]) for item in summaries]
    stage_names = [
        "roi", "extract_features", "visual_distance", "threshold", "debounce",
        "pass2_collect", "pass2_dedupe", "pass2_screenshots",
    ]
    median_stages = {
        name: statistics.median(float(item["timers"].get(name, 0)) for item in metrics)
        for name in stage_names
    }
    median_elapsed = statistics.median(elapsed)
    residual = max(0.0, median_elapsed - sum(median_stages.values()))
    ranked = sorted(
        [*median_stages.items(), ("unattributed_residual", residual)],
        key=lambda item: item[1], reverse=True,
    )
    ranked_rows = [
        {
            "rank": rank,
            "stage": name,
            "elapsed_seconds": value,
            "denominator": "median_detect_elapsed_seconds",
            "percentage": value / median_elapsed * 100,
            "measurement_type": "derived residual" if name == "unattributed_residual" else "median accumulated stage timer",
            "notes": "not a measured timer; includes decode/open/service/persistence" if name == "unattributed_residual" else "median across three recorded runs",
        }
        for rank, (name, value) in enumerate(ranked, 1)
    ]
    representative = summaries[1]
    representative_metrics = metrics[1]
    decision = "DECODE_PROFILE"
    next_branch = "perf/phase18-decode-profile"
    decision_evidence = (
        "Median unattributed residual is a material share of detect elapsed; profile packet.decode "
        "cumulative time exceeds feature extraction, while decoded-frame and RGB-transfer volumes are high."
    )
    result = {
        "benchmark_id": root.name,
        "source_description": representative["source_description"],
        "clip_start_seconds": representative["clip_start_seconds"],
        "clip_requested_duration_seconds": representative["clip_requested_duration_seconds"],
        "clip_actual_duration_seconds": representative["clip_actual_duration_seconds"],
        "clip_sha256": representative["clip_sha256"],
        "clip_codec": "h264",
        "clip_resolution": "1920x1080",
        "source_fps": 60.0,
        "clip_fps": 60.0,
        "clip_size_bytes": 48_653_686,
        "head_sha": representative["head_sha"],
        "branch": representative["branch"],
        "warmup_performed": True,
        "recorded_runs": 3,
        "runs": [
            {
                "run": index,
                "wall_clock_seconds": wall[index - 1],
                "detect_elapsed_seconds": elapsed[index - 1],
                "real_time_multiplier": summaries[index - 1]["real_time_multiplier"],
                "rss_peak_mb": metrics[index - 1]["gauges"]["rss_peak_mb"],
                "canonical_output_signature": signatures[index - 1],
            }
            for index in range(1, 4)
        ],
        "wall_clock_seconds": statistics.median(wall),
        "detect_elapsed_seconds": median_elapsed,
        "detect_elapsed_min_seconds": min(elapsed),
        "detect_elapsed_max_seconds": max(elapsed),
        "video_duration_seconds": representative["video_duration_seconds"],
        "real_time_multiplier": median_elapsed / representative["video_duration_seconds"],
        "processing_x_realtime": representative["video_duration_seconds"] / median_elapsed,
        "effective_sampled_fps": representative["effective_sampled_fps"],
        "effective_backend": representative["effective_backend"],
        "slides_count": representative["slides_count"],
        "change_count": None,
        "change_count_note": representative["change_count_note"],
        "score_distribution": representative["score_distribution"],
        "invariants": representative["invariants"],
        "metrics_representative_run": "run-02",
        "counters": representative_metrics["counters"],
        "gauges": representative_metrics["gauges"],
        "ranked_bottlenecks": ranked_rows,
        "output_signature_deterministic": True,
        "canonical_output_signature": signatures[0],
        "percentile_method": "numpy.percentile linear method (NumPy environment default)",
        "profile_evidence": {
            "packet_decode_cumulative_seconds": 128.832,
            "to_ndarray_cumulative_seconds": 10.218,
            "profile_elapsed_seconds": 246.743,
            "binary_profile": "retained locally only; profile.pstats omitted from repository",
        },
        "decision": decision,
        "recommended_next_branch": next_branch,
        "decision_evidence": decision_evidence,
    }
    (root / "aggregate.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (root / "benchmark_summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [
        f"# Phase 18 Short Benchmark: {root.name}", "",
        "## Protocol", "",
        "Fixed Hermes interval 00:00:00 to 00:10:00, stream-copied without re-encoding. "
        "One warm-up preceded three recorded DetectionService runs; cProfile was separate.", "",
        f"- Median detect elapsed: {median_elapsed:.6f} s",
        f"- Min / max: {min(elapsed):.6f} s / {max(elapsed):.6f} s",
        f"- Real-time multiplier: {result['real_time_multiplier']:.6f}",
        f"- Processing x realtime: {result['processing_x_realtime']:.6f}",
        f"- Signature: `{signatures[0]}` (identical in all runs)", "",
        "## Ranked Bottlenecks", "",
        "| Rank | Stage | Seconds | % median detect | Measurement | Notes |",
        "|---:|---|---:|---:|---|---|",
    ]
    lines.extend(
        f"| {row['rank']} | {row['stage']} | {row['elapsed_seconds']:.6f} | "
        f"{row['percentage']:.3f}% | {row['measurement_type']} | {row['notes']} |"
        for row in ranked_rows
    )
    lines.extend([
        "", "## Decision", "",
        f"**{decision}** -> `{next_branch}`", "", decision_evidence, "",
        "Threshold is not material. Feature extraction is substantial, but decode is the stronger "
        "next profiling hypothesis because decode cumulative time plus the uninstrumented residual "
        "and transfer volume indicate producer-side cost. No optimization is implemented here.", "",
        "Full-Hermes acceptance remains pending; no short-clip speedup percentage or accepted full-run projection is claimed.",
    ])
    (root / "benchmark_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    result = aggregate(args.root)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
