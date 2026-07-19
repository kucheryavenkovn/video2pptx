#!/usr/bin/env python3
# FILE: tools/sweep_analysis_resolution.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Grid-sweep analysis_max_side × sample_fps with wall-clock, stage timers, and segment quality vs native reference
#   SCOPE: Pure helpers for interval matching/quality; CLI runner writing evidence under benchmarks/detect/evidence/phase19-*/
#   DEPENDS: video2pptx.detect_slides, video2pptx.config, video2pptx.detection_metrics
#   LINKS: M-GOLDEN-MEAN-SWEEP, V-M-GOLDEN-MEAN-SWEEP, Phase-19
#   ROLE: SCRIPT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   interval_iou - IoU of two [start,end) intervals
#   match_segments - greedy match ref segments to candidate by IoU
#   compute_quality_metrics - missed/false_split/timestamp_error vs reference
#   run_cell - one detect run with metrics + wall-clock
#   run_sweep - full grid with optional multi-run median
#   main - CLI
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Phase 19.5 golden-mean sweep with real timing evidence
# END_CHANGE_SUMMARY

"""Phase 19 analysis-resolution golden-mean sweep.

Example (fixture smoke):
  python tools/sweep_analysis_resolution.py ^
    --video tests/fixtures/test_slides.mp4 ^
    --out benchmarks/detect/evidence/phase19-fixture-smoke ^
    --max-sides none,320,160 --sample-fps 0.5,1.0 --runs 1 ^
    --min-slide-duration 1 --min-stable-duration 0.5

Example (Hermes measurements):
  python tools/sweep_analysis_resolution.py ^
    --video .benchmarks/phase18/media/hermes-0000-1000.mp4 ^
    --out benchmarks/detect/evidence/phase19-hermes-600s ^
    --max-sides none,960,640,480,320 --sample-fps 2.0 --runs 2
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow running as script from repo root
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from video2pptx.config import AppConfig, DetectionConfig, VideoConfig  # noqa: E402
from video2pptx.detect_slides import run_detect_slides  # noqa: E402
from video2pptx.detection_metrics import collect  # noqa: E402
from video2pptx.models import SlideSegment  # noqa: E402

STAGE_FOCUS = (
    "pass1_decode_or_frame_advance",
    "extract_features",
    "pass2_decode_or_frame_advance",
    "pass2_dedupe",
    "pass2_screenshots",
    "roi",
    "visual_distance",
    "threshold",
    "debounce",
    "pass2_match_and_collect",
)


# ---------------------------------------------------------------------------
# Pure quality helpers
# ---------------------------------------------------------------------------


def interval_iou(a: tuple[float, float], b: tuple[float, float]) -> float:
    # START_CONTRACT: interval_iou
    #   PURPOSE: Intersection-over-union of two half-open time intervals
    #   INPUTS: { a: (start,end), b: (start,end) }
    #   OUTPUTS: { float in [0,1] }
    #   SIDE_EFFECTS: none
    # END_CONTRACT: interval_iou
    a0, a1 = a
    b0, b1 = b
    inter = max(0.0, min(a1, b1) - max(a0, b0))
    union = max(a1, b1) - min(a0, b0)
    if union <= 0:
        return 0.0
    return inter / union


def match_segments(
    ref: list[tuple[float, float]],
    cand: list[tuple[float, float]],
    iou_threshold: float = 0.3,
) -> list[tuple[int, int, float]]:
    # START_CONTRACT: match_segments
    #   PURPOSE: Greedy 1-1 match of candidate segments to reference by max IoU
    #   INPUTS: { ref, cand, iou_threshold }
    #   OUTPUTS: { list of (ref_idx, cand_idx, iou) }
    #   SIDE_EFFECTS: none
    # END_CONTRACT: match_segments
    pairs: list[tuple[float, int, int]] = []
    for i, r in enumerate(ref):
        for j, c in enumerate(cand):
            iou = interval_iou(r, c)
            if iou >= iou_threshold:
                pairs.append((iou, i, j))
    pairs.sort(reverse=True)
    used_r: set[int] = set()
    used_c: set[int] = set()
    matches: list[tuple[int, int, float]] = []
    for iou, i, j in pairs:
        if i in used_r or j in used_c:
            continue
        used_r.add(i)
        used_c.add(j)
        matches.append((i, j, iou))
    return matches


def compute_quality_metrics(
    ref_segments: list[SlideSegment],
    cand_segments: list[SlideSegment],
    iou_threshold: float = 0.3,
) -> dict[str, Any]:
    # START_CONTRACT: compute_quality_metrics
    #   PURPOSE: missed_slide_rate, false_split_rate, timestamp errors vs reference
    #   INPUTS: { ref_segments, cand_segments, iou_threshold }
    #   OUTPUTS: { dict with rates and error stats }
    #   SIDE_EFFECTS: none
    # END_CONTRACT: compute_quality_metrics
    ref = [(s.start, s.end) for s in ref_segments]
    cand = [(s.start, s.end) for s in cand_segments]
    matches = match_segments(ref, cand, iou_threshold=iou_threshold)
    matched_ref = {m[0] for m in matches}
    matched_cand = {m[1] for m in matches}
    n_ref = len(ref)
    n_cand = len(cand)
    missed = n_ref - len(matched_ref)
    false_splits = n_cand - len(matched_cand)
    start_errs: list[float] = []
    end_errs: list[float] = []
    for ri, ci, _iou in matches:
        start_errs.append(abs(ref[ri][0] - cand[ci][0]))
        end_errs.append(abs(ref[ri][1] - cand[ci][1]))
    all_errs = start_errs + end_errs

    def _stat(xs: list[float]) -> dict[str, float | None]:
        if not xs:
            return {"mean": None, "median": None, "max": None}
        return {
            "mean": float(statistics.mean(xs)),
            "median": float(statistics.median(xs)),
            "max": float(max(xs)),
        }

    return {
        "ref_count": n_ref,
        "cand_count": n_cand,
        "matched": len(matches),
        "missed": missed,
        "false_splits": false_splits,
        "missed_slide_rate": (missed / n_ref) if n_ref else 0.0,
        "false_split_rate": (false_splits / n_cand) if n_cand else 0.0,
        "mean_iou": float(statistics.mean([m[2] for m in matches])) if matches else None,
        "timestamp_error_start": _stat(start_errs),
        "timestamp_error_end": _stat(end_errs),
        "timestamp_error_all": _stat(all_errs),
        "iou_threshold": iou_threshold,
    }


def passes_quality_gates(
    quality: dict[str, Any],
    *,
    max_missed: float = 0.05,
    max_false_split: float = 0.10,
    max_timestamp_error: float | None = 1.5,
) -> dict[str, Any]:
    te = quality.get("timestamp_error_all") or {}
    median_te = te.get("median")
    gates = {
        "missed_slide_rate": quality["missed_slide_rate"] <= max_missed,
        "false_split_rate": quality["false_split_rate"] <= max_false_split,
    }
    if max_timestamp_error is not None and median_te is not None:
        gates["timestamp_error_median"] = median_te <= max_timestamp_error
    elif max_timestamp_error is not None:
        gates["timestamp_error_median"] = True  # no matched segs edge case handled elsewhere
    return {
        "pass": all(gates.values()),
        "gates": gates,
        "thresholds": {
            "missed_slide_rate": max_missed,
            "false_split_rate": max_false_split,
            "timestamp_error_median": max_timestamp_error,
        },
    }


# ---------------------------------------------------------------------------
# Run helpers
# ---------------------------------------------------------------------------


@dataclass
class CellKey:
    analysis_max_side: int | None
    sample_fps: float

    def label(self) -> str:
        side = "native" if self.analysis_max_side is None else str(self.analysis_max_side)
        return f"side={side}_fps={self.sample_fps:g}"


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=_ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "unknown"


def _png_shapes(out_dir: Path, segments: list[SlideSegment]) -> list[list[int]]:
    import cv2

    shapes: list[list[int]] = []
    for seg in segments:
        if not seg.image:
            continue
        path = out_dir / seg.image
        if not path.is_file():
            continue
        img = cv2.imread(str(path))
        if img is not None:
            h, w = img.shape[:2]
            shapes.append([h, w])
    return shapes


def run_cell(
    video: Path,
    out_dir: Path,
    *,
    analysis_max_side: int | None,
    sample_fps: float,
    min_slide_duration: float,
    min_stable_duration: float,
    decoder_backend: str = "auto",
) -> dict[str, Any]:
    # START_CONTRACT: run_cell
    #   PURPOSE: One instrumented detect run; return wall-clock, stage timers, segments summary
    #   SIDE_EFFECTS: writes slides under out_dir
    # END_CONTRACT: run_cell
    if out_dir.exists():
        import shutil

        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = AppConfig(
        video=VideoConfig(
            sample_fps=sample_fps,
            decoder_backend=decoder_backend,
            analysis_max_side=analysis_max_side,
        ),
        detection=DetectionConfig(
            min_slide_duration=min_slide_duration,
            min_stable_duration=min_stable_duration,
            dedupe_enabled=True,
            threshold="auto",
            slide_roi="auto",
        ),
    )

    t0 = time.perf_counter()
    with collect() as metrics:
        doc = run_detect_slides(video, out_dir, cfg)
    wall = time.perf_counter() - t0
    mdict = metrics.to_dict()
    timers = {k: float(v) for k, v in mdict.get("timers", {}).items()}
    gauges = mdict.get("gauges", {})
    counters = mdict.get("counters", {})
    focus = {name: timers.get(name, 0.0) for name in STAGE_FOCUS}
    png_shapes = _png_shapes(out_dir, list(doc.slides))

    return {
        "wall_clock_seconds": wall,
        "detect_timer_total": timers.get("total", wall),
        "video_duration": doc.video.duration if doc.video else None,
        "video_width": doc.video.width if doc.video else None,
        "video_height": doc.video.height if doc.video else None,
        "slides_count": len(doc.slides),
        "score_count": len(doc.score_values),
        "segments": [
            {
                "index": s.index,
                "start": s.start,
                "end": s.end,
                "representative_timestamp": s.representative_timestamp,
            }
            for s in doc.slides
        ],
        "segment_objects": list(doc.slides),  # not JSON-serialized
        "timers_focus": focus,
        "timers_all": timers,
        "gauges": gauges,
        "counters": counters,
        "png_shapes": png_shapes,
        "analysis_max_side": analysis_max_side,
        "sample_fps": sample_fps,
    }


def _median_of(values: list[float]) -> float:
    return float(statistics.median(values))


def aggregate_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    walls = [r["wall_clock_seconds"] for r in runs]
    totals = [r["detect_timer_total"] for r in runs]
    focus_keys = STAGE_FOCUS
    focus_med: dict[str, float] = {}
    for k in focus_keys:
        focus_med[k] = _median_of([r["timers_focus"].get(k, 0.0) for r in runs])

    # pick run with median wall for segment snapshot
    ordered = sorted(range(len(runs)), key=lambda i: runs[i]["wall_clock_seconds"])
    mid = ordered[len(ordered) // 2]
    med_run = runs[mid]

    return {
        "n_runs": len(runs),
        "wall_clock_seconds": {
            "values": walls,
            "median": _median_of(walls),
            "mean": float(statistics.mean(walls)),
            "stdev": float(statistics.stdev(walls)) if len(walls) > 1 else 0.0,
            "min": min(walls),
            "max": max(walls),
        },
        "detect_timer_total": {
            "values": totals,
            "median": _median_of(totals),
        },
        "timers_focus_median": focus_med,
        "slides_count": med_run["slides_count"],
        "score_count": med_run["score_count"],
        "segments": med_run["segments"],
        "segment_objects": med_run["segment_objects"],
        "gauges": med_run["gauges"],
        "counters": med_run["counters"],
        "png_shapes": med_run["png_shapes"],
        "video_duration": med_run["video_duration"],
        "video_width": med_run["video_width"],
        "video_height": med_run["video_height"],
        "median_run_index": mid,
        "per_run": [
            {
                "wall_clock_seconds": r["wall_clock_seconds"],
                "detect_timer_total": r["detect_timer_total"],
                "slides_count": r["slides_count"],
                "timers_focus": r["timers_focus"],
                "gauges": r["gauges"],
            }
            for r in runs
        ],
    }


def parse_max_sides(s: str) -> list[int | None]:
    out: list[int | None] = []
    for part in s.split(","):
        part = part.strip().lower()
        if part in ("none", "null", "native", ""):
            out.append(None)
        else:
            out.append(int(part))
    return out


def parse_fps_list(s: str) -> list[float]:
    return [float(x.strip()) for x in s.split(",") if x.strip()]


def run_sweep(
    video: Path,
    out_root: Path,
    *,
    max_sides: list[int | None],
    sample_fps_list: list[float],
    n_runs: int,
    min_slide_duration: float,
    min_stable_duration: float,
    decoder_backend: str,
    iou_threshold: float,
    warmup: bool,
) -> dict[str, Any]:
    out_root.mkdir(parents=True, exist_ok=True)
    cells_dir = out_root / "cells"
    cells_dir.mkdir(exist_ok=True)

    if warmup:
        warm_dir = out_root / "_warmup"
        print("[sweep] warmup run (discarded)...", flush=True)
        run_cell(
            video,
            warm_dir,
            analysis_max_side=None,
            sample_fps=sample_fps_list[0],
            min_slide_duration=min_slide_duration,
            min_stable_duration=min_stable_duration,
            decoder_backend=decoder_backend,
        )

    # Reference = first native (None) at first sample_fps that includes native;
    # if native not in grid, use first cell as self-ref only for quality N/A.
    ref_side = None if None in max_sides else max_sides[0]
    ref_fps = sample_fps_list[0]
    # Prefer native reference at each sample_fps independently when available
    ref_by_fps: dict[float, list[SlideSegment]] = {}
    ref_png_by_fps: dict[float, list[list[int]]] = {}

    results: list[dict[str, Any]] = []

    for fps in sample_fps_list:
        for side in max_sides:
            key = CellKey(side, fps)
            print(f"[sweep] === {key.label()}  runs={n_runs} ===", flush=True)
            runs: list[dict[str, Any]] = []
            for i in range(n_runs):
                cell_out = cells_dir / f"{key.label()}_run{i+1:02d}"
                print(f"[sweep]   run {i+1}/{n_runs} -> {cell_out.name}", flush=True)
                r = run_cell(
                    video,
                    cell_out,
                    analysis_max_side=side,
                    sample_fps=fps,
                    min_slide_duration=min_slide_duration,
                    min_stable_duration=min_stable_duration,
                    decoder_backend=decoder_backend,
                )
                print(
                    f"[sweep]   wall={r['wall_clock_seconds']:.2f}s "
                    f"extract={r['timers_focus'].get('extract_features', 0):.2f}s "
                    f"p1_decode={r['timers_focus'].get('pass1_decode_or_frame_advance', 0):.2f}s "
                    f"slides={r['slides_count']}",
                    flush=True,
                )
                runs.append(r)

            agg = aggregate_runs(runs)

            # Establish reference for this fps: prefer native
            if side is None or (fps not in ref_by_fps and side == ref_side):
                if side is None:
                    ref_by_fps[fps] = list(agg["segment_objects"])
                    ref_png_by_fps[fps] = list(agg["png_shapes"])

            # Quality vs native reference at same fps (if available)
            if fps in ref_by_fps:
                quality = compute_quality_metrics(
                    ref_by_fps[fps], list(agg["segment_objects"]), iou_threshold=iou_threshold
                )
                # For reference cell itself, quality is perfect match
                if side is None:
                    quality = compute_quality_metrics(
                        ref_by_fps[fps], ref_by_fps[fps], iou_threshold=iou_threshold
                    )
                gate = passes_quality_gates(quality)
            else:
                quality = {"note": "no_native_reference_for_fps"}
                gate = {"pass": None, "gates": {}, "thresholds": {}}

            # Full-res screenshot invariant: PNG shape should match video frame (auto ROI)
            vw, vh = agg.get("video_width"), agg.get("video_height")
            full_res_ok = True
            if agg["png_shapes"] and vw and vh:
                full_res_ok = all(h == vh and w == vw for h, w in agg["png_shapes"])

            cell_record = {
                "analysis_max_side": side,
                "sample_fps": fps,
                "label": key.label(),
                "is_reference": side is None,
                "n_runs": n_runs,
                "wall_clock_seconds_median": agg["wall_clock_seconds"]["median"],
                "wall_clock_seconds": agg["wall_clock_seconds"],
                "detect_timer_total_median": agg["detect_timer_total"]["median"],
                "timers_focus_median": agg["timers_focus_median"],
                "slides_count": agg["slides_count"],
                "score_count": agg["score_count"],
                "segments": agg["segments"],
                "gauges": agg["gauges"],
                "counters": agg["counters"],
                "png_shapes": agg["png_shapes"],
                "full_res_screenshot_ok": full_res_ok,
                "quality_vs_native": quality,
                "quality_gates": gate,
                "per_run": agg["per_run"],
            }
            # Drop non-serializable
            results.append(cell_record)

            # Write per-cell JSON (no segment objects)
            cell_path = out_root / f"cell_{key.label()}.json"
            cell_path.write_text(json.dumps(cell_record, indent=2), encoding="utf-8")

    # Speedup vs native at same fps
    native_wall: dict[float, float] = {}
    native_extract: dict[float, float] = {}
    for c in results:
        if c["analysis_max_side"] is None:
            fps = c["sample_fps"]
            native_wall[fps] = c["wall_clock_seconds_median"]
            native_extract[fps] = c["timers_focus_median"].get("extract_features", 0.0)

    for c in results:
        fps = c["sample_fps"]
        nw = native_wall.get(fps)
        ne = native_extract.get(fps)
        if nw and nw > 0:
            c["speedup_vs_native_wall"] = nw / c["wall_clock_seconds_median"]
            c["seconds_saved_vs_native_wall"] = nw - c["wall_clock_seconds_median"]
            c["wall_reduction_pct"] = (1.0 - c["wall_clock_seconds_median"] / nw) * 100.0
        else:
            c["speedup_vs_native_wall"] = None
            c["seconds_saved_vs_native_wall"] = None
            c["wall_reduction_pct"] = None
        if ne and ne > 0:
            ce = c["timers_focus_median"].get("extract_features", 0.0)
            c["speedup_vs_native_extract_features"] = ne / ce if ce > 0 else None
            c["extract_features_reduction_pct"] = (1.0 - ce / ne) * 100.0 if ce > 0 else None
        else:
            c["speedup_vs_native_extract_features"] = None
            c["extract_features_reduction_pct"] = None

    # Ranking among gate-passers
    passers = [
        c
        for c in results
        if c.get("quality_gates", {}).get("pass") is True and c.get("full_res_screenshot_ok")
    ]
    # Prefer higher wall speedup; tie-break higher max_side then higher fps
    def _rank_key(c: dict[str, Any]) -> tuple:
        sp = c.get("speedup_vs_native_wall") or 0.0
        side = c["analysis_max_side"] if c["analysis_max_side"] is not None else 10**9
        return (sp, side, c["sample_fps"])

    passers_sorted = sorted(passers, key=_rank_key, reverse=True)
    # Exclude pure native from "selected optimization" if speedup ~1
    candidates = [
        c
        for c in passers_sorted
        if c["analysis_max_side"] is not None
        and (c.get("wall_reduction_pct") or 0) >= 5.0  # at least 5% wall reduction
    ]

    if candidates:
        best = candidates[0]
        decision = {
            "selected_analysis_scale": best["analysis_max_side"],
            "selected_sample_fps": best["sample_fps"],
            "selected_label": best["label"],
            "reason": "highest wall speedup among gate-passers with >=5% wall reduction",
            "wall_reduction_pct": best.get("wall_reduction_pct"),
            "extract_features_reduction_pct": best.get("extract_features_reduction_pct"),
            "speedup_vs_native_wall": best.get("speedup_vs_native_wall"),
        }
    elif any(c["analysis_max_side"] is None for c in results):
        # Check if any downscale helped at all without meeting 5% bar
        downs = [c for c in results if c["analysis_max_side"] is not None]
        helped = [c for c in downs if (c.get("wall_reduction_pct") or 0) > 0]
        decision = {
            "selected_analysis_scale": "NONE",
            "reason": (
                "no downscale cell reached >=5% wall reduction with quality gates"
                if not helped
                else "downscale saved some time but <5% wall or failed quality gates"
            ),
            "phase18_reopened": False,
            "positive_but_below_threshold": [
                {
                    "label": c["label"],
                    "wall_reduction_pct": c.get("wall_reduction_pct"),
                    "extract_features_reduction_pct": c.get("extract_features_reduction_pct"),
                    "gates_pass": c.get("quality_gates", {}).get("pass"),
                }
                for c in sorted(downs, key=lambda x: x.get("wall_reduction_pct") or -999, reverse=True)
            ],
        }
    else:
        decision = {
            "selected_analysis_scale": "NONE",
            "reason": "no native reference / incomplete grid",
            "phase18_reopened": False,
        }

    decision["phase18_reopened"] = False
    decision["phase18_selected_optimization"] = "NONE (unchanged)"

    summary = {
        "schema_version": "1.0.0",
        "tool": "sweep_analysis_resolution",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "head_sha": _git_head(),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "video": str(video),
        "video_name": video.name,
        "grid": {
            "analysis_max_side": max_sides,
            "sample_fps": sample_fps_list,
            "n_runs": n_runs,
            "min_slide_duration": min_slide_duration,
            "min_stable_duration": min_stable_duration,
            "decoder_backend": decoder_backend,
            "iou_threshold": iou_threshold,
            "warmup": warmup,
        },
        "cells": results,
        "decision": decision,
        "interpretation_notes": [
            "Decode path still processes native H.264 frames; analysis_max_side mainly cuts extract_features CPU after ROI.",
            "Wall-clock speedup may be modest if decode dominates (~60% in Phase 18 Hermes).",
            "extract_features_reduction_pct is the direct lever; wall_reduction_pct is the user-visible outcome.",
            "full_res_screenshot_ok must remain true for all accepted configs.",
            "Quality is vs native reference at the same sample_fps (soft parity, not score byte-identity).",
        ],
    }

    # Rewrite cells without non-JSON (already clean)
    (out_root / "sweep_summary.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8"
    )
    _write_report_md(out_root / "sweep_report.md", summary)
    (out_root / "golden_mean_decision.json").write_text(
        json.dumps(decision, indent=2), encoding="utf-8"
    )
    return summary


def _write_report_md(path: Path, summary: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# Phase 19 — Analysis Resolution Sweep Report")
    lines.append("")
    lines.append(f"- Created: `{summary['created_at']}`")
    lines.append(f"- HEAD: `{summary['head_sha']}`")
    lines.append(f"- Video: `{summary['video_name']}`")
    lines.append(f"- Grid: max_sides={summary['grid']['analysis_max_side']} "
                 f"sample_fps={summary['grid']['sample_fps']} runs={summary['grid']['n_runs']}")
    lines.append("")
    lines.append("## Results (median wall-clock)")
    lines.append("")
    lines.append(
        "| label | wall_s | vs native | extract_s | extract Δ% | p1_decode_s | slides | missed | false_split | full_res | gates |"
    )
    lines.append(
        "|-------|--------|-----------|-----------|------------|-------------|--------|--------|-------------|---------|-------|"
    )
    for c in summary["cells"]:
        q = c.get("quality_vs_native") or {}
        g = c.get("quality_gates") or {}
        te = c.get("timers_focus_median") or {}
        wr = c.get("wall_reduction_pct")
        er = c.get("extract_features_reduction_pct")
        lines.append(
            f"| {c['label']} "
            f"| {c['wall_clock_seconds_median']:.2f} "
            f"| {('%.1f%%' % wr) if wr is not None else '—'} "
            f"| {te.get('extract_features', 0):.2f} "
            f"| {('%.1f%%' % er) if er is not None else '—'} "
            f"| {te.get('pass1_decode_or_frame_advance', 0):.2f} "
            f"| {c['slides_count']} "
            f"| {q.get('missed_slide_rate', '—')} "
            f"| {q.get('false_split_rate', '—')} "
            f"| {c.get('full_res_screenshot_ok')} "
            f"| {g.get('pass')} |"
        )
    lines.append("")
    lines.append("## Decision")
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(summary["decision"], indent=2))
    lines.append("```")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for n in summary.get("interpretation_notes", []):
        lines.append(f"- {n}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Phase 19 analysis_max_side × sample_fps sweep")
    p.add_argument("--video", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--max-sides", type=str, default="none,960,640,480,320")
    p.add_argument("--sample-fps", type=str, default="2.0")
    p.add_argument("--runs", type=int, default=2)
    p.add_argument("--min-slide-duration", type=float, default=10.0)
    p.add_argument("--min-stable-duration", type=float, default=5.0)
    p.add_argument("--decoder-backend", type=str, default="auto")
    p.add_argument("--iou-threshold", type=float, default=0.3)
    p.add_argument("--warmup", action="store_true", help="Discard one native warmup run first")
    args = p.parse_args(argv)

    if not args.video.is_file():
        print(f"ERROR: video not found: {args.video}", file=sys.stderr)
        return 2

    summary = run_sweep(
        args.video.resolve(),
        args.out.resolve(),
        max_sides=parse_max_sides(args.max_sides),
        sample_fps_list=parse_fps_list(args.sample_fps),
        n_runs=max(1, args.runs),
        min_slide_duration=args.min_slide_duration,
        min_stable_duration=args.min_stable_duration,
        decoder_backend=args.decoder_backend,
        iou_threshold=args.iou_threshold,
        warmup=args.warmup,
    )
    print("[sweep] done", flush=True)
    print(json.dumps(summary["decision"], indent=2))
    print(f"[sweep] report: {args.out / 'sweep_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
