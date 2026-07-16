#!/usr/bin/env python3
# FILE: tools/discrimination_helpers.py
# VERSION: 2.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Pure deterministic helpers for Step 18.4C target-optimization discrimination.
#   SCOPE: Statistics, reference repeatability, exact C2 retention rules,
#          deterministic C3 selection/guards, frame parity, and signatures.
#   DEPENDS: hashlib, json, statistics, subprocess, platform process APIs
#   LINKS: M-DETECT-PERF-DECISION, V-PERF-DETECT-BOTTLENECK
#   ROLE: SCRIPT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   compute_median - median of a list of floats
#   compute_mean - arithmetic mean of a list of floats
#   compute_sample_stdev - sample standard deviation (N-1)
#   compute_paired_absolute_savings - per-pair reference-candidate differences
#   compute_paired_percentage_reduction - per-pair percentage reduction
#   compute_median_reduction_percent - median of paired percentage reductions
#   compute_difference_of_medians - reference_median - candidate_median seconds and percent
#   directional_stability - true iff every candidate run is faster than paired reference
#   compute_target_sampled_timestamp - first sampled ts within tolerance of rep_ts
#   compute_target_frame_index - frame index for a target sampled timestamp
#   check_frame_parity - exact per-target cropped-frame SHA/shape/byte parity
#   compute_full_rgb_retention_bytes - total bytes for full-RGB frame retention
#   compute_roi_retention_bytes - total bytes for ROI-cropped frame retention
#   bytes_to_gb_decimal - bytes to decimal gigabytes
#   bytes_to_gib - bytes to binary gibibytes
#   compute_retention_ratio - retention bytes / representative frame bytes
#   validate_c3_variant_metadata - required-fields validation for a C3 variant
#   build_streaming_frame_signature - deterministic hash over a frame-signature sequence
#   check_sequence_parity - exact yielded-frame-sequence parity
#   classify_reference_repeatability - classify three independent decode sequences
#   earliest_possible_representative - lower target bound for an unresolved segment
#   can_evict_retained_frame - exact strict-tolerance eviction predicate
#   select_c3_variants - deterministic variants from recorded inspection fields
#   check_c3_selection_consistency - hard guard against eligible/zero contradiction
#   validate_accepted_base - validate full commit SHA and HEAD ancestry
#   balanced_recorded_order - required paired timing execution order
#   process_rss_bytes - current process RSS with an explicit platform backend
# END_MODULE_MAP
"""
Pure deterministic helpers for Step 18.4C target-optimization discrimination.
No timing sleeps, no I/O side effects, no randomness.
"""

from __future__ import annotations

import hashlib
import json
import os
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any

_GB = 1_000_000_000
_GIB = 1024**3


# =========================================================================
# Statistics
# =========================================================================


def compute_median(values: list[float]) -> float:
    if not values:
        raise ValueError("compute_median: empty list")
    return float(statistics.median(values))


def compute_mean(values: list[float]) -> float:
    if not values:
        raise ValueError("compute_mean: empty list")
    return float(statistics.mean(values))


def compute_sample_stdev(values: list[float]) -> float:
    if len(values) < 2:
        raise ValueError("compute_sample_stdev: need at least 2 values")
    return float(statistics.stdev(values))


def compute_paired_absolute_savings(reference: list[float], candidate: list[float]) -> list[float]:
    if len(reference) != len(candidate):
        raise ValueError(
            f"paired lengths differ: reference={len(reference)} candidate={len(candidate)}"
        )
    return [float(r - c) for r, c in zip(reference, candidate, strict=True)]


def compute_paired_percentage_reduction(
    reference: list[float], candidate: list[float]
) -> list[float]:
    if len(reference) != len(candidate):
        raise ValueError(
            f"paired lengths differ: reference={len(reference)} candidate={len(candidate)}"
        )
    results: list[float] = []
    for r, c in zip(reference, candidate, strict=True):
        if r == 0:
            results.append(0.0)
        else:
            results.append(float((r - c) / r * 100.0))
    return results


def compute_median_reduction_percent(reference: list[float], candidate: list[float]) -> float:
    return compute_median(compute_paired_percentage_reduction(reference, candidate))


def compute_difference_of_medians(
    reference_median: float, candidate_median: float
) -> dict[str, float]:
    # START_CONTRACT: compute_difference_of_medians
    #   PURPOSE: Compute difference-of-medians seconds and percent from two medians.
    #   INPUTS: { reference_median: float, candidate_median: float }
    #   OUTPUTS: { dict with difference_of_medians_seconds and difference_of_medians_percent }
    #   SIDE_EFFECTS: none
    #   LINKS: M-DETECT-PERF-DECISION
    # END_CONTRACT: compute_difference_of_medians
    """Difference-of-medians statistics.

    difference_of_medians_seconds = reference_median - candidate_median
    difference_of_medians_percent = difference_of_medians_seconds / reference_median * 100

    This is DISTINCT from the median-of-paired-differences
    (compute_paired_absolute_savings + compute_median). Both quantities are
    recorded explicitly in evidence artifacts with their own definition fields so
    the two concepts cannot be conflated.
    """
    if reference_median == 0:
        raise ValueError("reference_median must be non-zero for percent reduction")
    seconds = float(reference_median - candidate_median)
    percent = float(seconds / reference_median * 100.0)
    return {
        "difference_of_medians_seconds": seconds,
        "difference_of_medians_percent": percent,
    }


def directional_stability(reference: list[float], candidate: list[float]) -> bool:
    """True iff every candidate value is strictly less than the paired reference."""
    if len(reference) != len(candidate):
        raise ValueError("directional_stability: length mismatch")
    return all(c < r for r, c in zip(reference, candidate, strict=True))


# =========================================================================
# C1 — target timestamp / frame index computation
# =========================================================================


def compute_target_sampled_timestamp(
    rep_ts: float,
    video_fps: float,
    frame_interval: int,
    sample_tolerance: float,
) -> float | None:
    """Compute the first sampled timestamp within tolerance of rep_ts.

    Sampled timestamps are 0, step, 2*step, ... where step = frame_interval / video_fps.
    The sequential pass finds the FIRST sampled frame (in temporal order) where
    abs(sampled_ts - rep_ts) < sample_tolerance (strict less-than).
    """
    step = frame_interval / video_fps
    if step <= 0:
        return None
    lower_idx = int(rep_ts // step)
    lower_ts = lower_idx * step
    if abs(lower_ts - rep_ts) < sample_tolerance:
        return lower_ts
    upper_ts = (lower_idx + 1) * step
    if abs(upper_ts - rep_ts) < sample_tolerance:
        return upper_ts
    return None


def compute_target_frame_index(
    target_ts: float,
    video_fps: float,
    frame_interval: int,
) -> int:
    """Return the frame index (multiple of frame_interval) for a sampled timestamp."""
    step = frame_interval / video_fps
    if step <= 0:
        raise ValueError("frame_interval / video_fps must be positive")
    sampled_step_idx = round(target_ts / step)
    return int(sampled_step_idx * frame_interval)


# =========================================================================
# C1 — frame parity
# =========================================================================


def check_frame_parity(
    reference: dict[float, dict[str, Any]],
    candidate: dict[float, dict[str, Any]],
) -> dict[str, Any]:
    """Compare reference and candidate representative frames for exact parity.

    Each dict maps representative_timestamp -> {
        "sampled_timestamp": float,
        "shape": list[int],
        "rgb_sha256": str,
        "bytes_equal": bool (or None if not checked),
    }
    """
    ref_ts_set = set(reference.keys())
    cand_ts_set = set(candidate.keys())

    result: dict[str, Any] = {
        "target_count_reference": len(ref_ts_set),
        "target_count_candidate": len(cand_ts_set),
        "target_timestamp_count_identical": ref_ts_set == cand_ts_set,
        "all_targets_mapped": ref_ts_set == cand_ts_set,
        "per_target": {},
        "exact_sampled_timestamp_parity": True,
        "exact_cropped_rgb_sha_parity": True,
        "exact_byte_parity": True,
        "exact_shape_parity": True,
        "parity_pass": True,
    }

    for ts in sorted(ref_ts_set):
        ref_entry = reference[ts]
        cand_entry = candidate.get(ts)
        if cand_entry is None:
            result["per_target"][str(ts)] = {"status": "MISSING_IN_CANDIDATE"}
            result["parity_pass"] = False
            result["exact_cropped_rgb_sha_parity"] = False
            result["exact_byte_parity"] = False
            continue

        ts_match = ref_entry["sampled_timestamp"] == cand_entry["sampled_timestamp"]
        sha_match = ref_entry["rgb_sha256"] == cand_entry["rgb_sha256"]
        shape_match = list(ref_entry["shape"]) == list(cand_entry["shape"])

        if not ts_match:
            result["exact_sampled_timestamp_parity"] = False
        if not sha_match:
            result["exact_cropped_rgb_sha_parity"] = False
        if not shape_match:
            result["exact_shape_parity"] = False

        entry: dict[str, Any] = {
            "reference_sampled_timestamp": ref_entry["sampled_timestamp"],
            "candidate_sampled_timestamp": cand_entry["sampled_timestamp"],
            "exact_sampled_timestamp_match": ts_match,
            "reference_shape": list(ref_entry["shape"]),
            "candidate_shape": list(cand_entry["shape"]),
            "exact_shape_match": shape_match,
            "reference_rgb_sha256": ref_entry["rgb_sha256"],
            "candidate_rgb_sha256": cand_entry["rgb_sha256"],
            "exact_cropped_rgb_sha_match": sha_match,
        }

        ref_bytes = ref_entry.get("raw_bytes_sha256")
        cand_bytes = cand_entry.get("raw_bytes_sha256")
        if ref_bytes is not None and cand_bytes is not None:
            byte_match = ref_bytes == cand_bytes
            entry["exact_byte_match"] = byte_match
            if not byte_match:
                result["exact_byte_parity"] = False
        else:
            entry["exact_byte_match"] = None

        entry["status"] = (
            "PASS"
            if (ts_match and sha_match and shape_match and (entry["exact_byte_match"] is not False))
            else "FAIL"
        )
        if entry["status"] == "FAIL":
            result["parity_pass"] = False

        result["per_target"][str(ts)] = entry

    return result


# =========================================================================
# C2 — resource byte calculations
# =========================================================================


def compute_full_rgb_retention_bytes(
    frames_sampled: int, width: int, height: int, channels: int = 3
) -> int:
    return frames_sampled * width * height * channels


def compute_roi_retention_bytes(
    frames_sampled: int, roi_width: int, roi_height: int, channels: int = 3
) -> int:
    return frames_sampled * roi_width * roi_height * channels


def bytes_to_gb_decimal(b: int) -> float:
    return b / _GB


def bytes_to_gib(b: int) -> float:
    return b / _GIB


def compute_retention_ratio(retention_bytes: int, representative_frame_bytes: int) -> float:
    if representative_frame_bytes == 0:
        raise ValueError("representative_frame_bytes must be positive")
    return retention_bytes / representative_frame_bytes


# =========================================================================
# C3 — variant metadata and sequence parity
# =========================================================================


_C3_REQUIRED_FIELDS = (
    "name",
    "property_or_options_boundary",
    "default_value",
    "candidate_value",
    "mechanistic_hypothesis",
    "frame_sequence_parity_risk",
    "hwaccel_compatibility_risk",
)


def validate_c3_variant_metadata(variant: dict[str, Any]) -> None:
    """Raise ValueError if required variant metadata fields are missing."""
    missing = [f for f in _C3_REQUIRED_FIELDS if f not in variant]
    if missing:
        raise ValueError(f"C3 variant missing required fields: {missing}")


def build_streaming_frame_signature(frame_signatures: list[dict[str, Any]]) -> str:
    """Build a deterministic SHA256 over a sequence of per-frame signature dicts."""
    canonical = json.dumps(frame_signatures, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def check_sequence_parity(
    reference_signature: str,
    candidate_signature: str,
    reference_count: int,
    candidate_count: int,
    reference_timestamps: list[float],
    candidate_timestamps: list[float],
    reference_frame_hashes: list[str],
    candidate_frame_hashes: list[str],
) -> dict[str, Any]:
    """Check exact yielded-frame-sequence parity for a decoder configuration variant."""
    count_match = reference_count == candidate_count
    ts_match = reference_timestamps == candidate_timestamps
    hash_match = reference_frame_hashes == candidate_frame_hashes
    sig_match = reference_signature == candidate_signature
    return {
        "yielded_frame_count_identical": count_match,
        "timestamp_sequence_identical": ts_match,
        "per_frame_rgb_sha_identical": hash_match,
        "final_sequence_signature_identical": sig_match,
        "parity_pass": count_match and ts_match and hash_match and sig_match,
    }


# =========================================================================
# Reference repeatability
# =========================================================================


def classify_reference_repeatability(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify exact sequence repeatability across three independent opens."""
    if len(runs) != 3:
        raise ValueError("exactly three reference runs are required")
    comparisons: dict[str, dict[str, bool]] = {}
    all_equal = True
    for left, right in ((0, 1), (0, 2), (1, 2)):
        a, b = runs[left], runs[right]
        key = f"run{left + 1:02d}_run{right + 1:02d}"
        comparison = {
            "frame_count_identical": a["frames_yielded"] == b["frames_yielded"],
            "timestamp_sequence_identical": a["yielded_timestamps"] == b["yielded_timestamps"],
            "shape_sequence_identical": a["shapes"] == b["shapes"],
            "rgb_sequence_identical": a["frame_hashes"] == b["frame_hashes"],
            "complete_signature_identical": a["sequence_signature"] == b["sequence_signature"],
        }
        comparison["exact_match"] = all(comparison.values())
        comparisons[key] = comparison
        all_equal = all_equal and comparison["exact_match"]
    classification = (
        "REFERENCE_EXACTLY_REPEATABLE"
        if all_equal
        else "REFERENCE_PIXEL_NONDETERMINISTIC_ACROSS_OPENS"
    )
    return {
        "run_count": 3,
        "comparisons": comparisons,
        "classification": classification,
        "exact_byte_cross_open_discriminator_valid": all_equal,
    }


# =========================================================================
# C2 exact rolling retention model
# =========================================================================


def representative_timestamp(start: float, end: float) -> float:
    """Mirror segmenter.choose_representative_timestamp exactly."""
    duration = end - start
    factor = 0.8 if duration >= 6.0 else 0.5
    return min(start + factor * duration, end - 0.01)


def earliest_possible_representative(segment_start: float, current_time: float) -> float:
    """Lower representative target over all legal final ends >= current_time."""
    duration = current_time - segment_start
    if duration < 0:
        raise ValueError("current_time precedes segment_start")
    factor = 0.8 if duration >= 6.0 else 0.5
    return min(segment_start + factor * duration, current_time - 0.01)


def can_evict_retained_frame(
    frame_timestamp: float,
    segment_start: float,
    current_time: float,
    sample_tolerance: float,
) -> bool:
    """Return true when strict tolerance makes future selection impossible."""
    lower_target = earliest_possible_representative(segment_start, current_time)
    return frame_timestamp + sample_tolerance <= lower_target


def select_first_strict_match(
    timestamps: list[float], target: float, tolerance: float
) -> float | None:
    """Select the first timestamp satisfying the production strict tolerance."""
    return next((ts for ts in timestamps if abs(ts - target) < tolerance), None)


# =========================================================================
# C3 deterministic selection and provenance
# =========================================================================


def select_c3_variants(inspection: dict[str, Any], max_variants: int = 3) -> list[dict[str, Any]]:
    """Select variants using only recorded inspection fields and stable ordering."""
    if max_variants < 0:
        raise ValueError("max_variants must be non-negative")
    variants: list[dict[str, Any]] = []
    properties = inspection.get("properties", {})
    for name in ("thread_count", "thread_type"):
        prop = properties.get(name, {})
        if not (
            prop.get("writable") is True
            and prop.get("classification") == "POTENTIALLY_PARITY_PRESERVING"
        ):
            continue
        default_value = prop.get("default_value")
        values = (1, 4, 8) if name == "thread_count" else (1, 2)
        for value in values:
            if value == default_value:
                continue
            variants.append(
                {
                    "name": f"{name}_{value}",
                    "property_or_options_boundary": f"codec_context.{name}",
                    "default_value": default_value,
                    "candidate_value": value,
                    "mechanistic_hypothesis": (
                        f"Changing codec_context.{name} may alter decoder scheduling/throughput; "
                        "the actual effect in the production-equivalent path is unknown and must be measured."
                    ),
                    "frame_sequence_parity_risk": "UNKNOWN_REQUIRES_EXACT_MEASUREMENT",
                    "hwaccel_compatibility_risk": "UNKNOWN_NOT_PROVEN",
                }
            )
    return variants[:max_variants]


def check_c3_selection_consistency(
    inspection: dict[str, Any], variants: list[dict[str, Any]]
) -> str:
    """Enforce machine-readable eligible-boundary/variant consistency."""
    eligible = [
        prop
        for prop in inspection.get("properties", {}).values()
        if prop.get("writable") is True
        and prop.get("classification") == "POTENTIALLY_PARITY_PRESERVING"
    ]
    if not eligible or variants:
        return "PASS"
    if all(prop.get("direct_runtime_exclusion_evidence") for prop in eligible):
        return "PASS_ALL_ELIGIBLE_BOUNDARIES_DIRECTLY_EXCLUDED"
    return "FAIL_ELIGIBLE_BOUNDARIES_WITH_ZERO_VARIANTS"


def validate_accepted_base(accepted_base: str, repo: Path) -> None:
    """Require a full lowercase commit SHA that is an ancestor of HEAD."""
    if len(accepted_base) != 40 or any(c not in "0123456789abcdef" for c in accepted_base):
        raise ValueError("accepted base must be a full lowercase 40-character SHA")
    try:
        object_type = subprocess.check_output(
            ["git", "cat-file", "-t", accepted_base],
            cwd=repo,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except subprocess.CalledProcessError as exc:
        raise ValueError("accepted base Git object does not exist") from exc
    if object_type != "commit":
        raise ValueError(f"accepted base is {object_type}, expected commit")
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", accepted_base, "HEAD"],
        cwd=repo,
        check=False,
    )
    if result.returncode != 0:
        raise ValueError("accepted base is not an ancestor of HEAD")


def collect_git_provenance(repo: Path, allowed_evidence_root: Path | None = None) -> dict[str, str]:
    """Record committed HEAD/tree and reject dirt outside the active evidence root."""
    status_lines = subprocess.check_output(
        ["git", "status", "--short"], cwd=repo, text=True
    ).splitlines()
    if allowed_evidence_root is not None:
        allowed = allowed_evidence_root.resolve().relative_to(repo.resolve()).as_posix().rstrip("/")
        status_lines = [
            line
            for line in status_lines
            if not line[3:].replace("\\", "/").startswith(f"{allowed}/")
            and line[3:].replace("\\", "/") != allowed
        ]
    if status_lines:
        raise ValueError(f"evidence execution found dirt outside evidence root: {status_lines}")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=repo, text=True).strip()
    return {"evidence_code_head": head, "evidence_code_tree": tree}


def balanced_recorded_order() -> list[str]:
    """Return the required balanced three-pair timing order."""
    return [
        "reference-01",
        "candidate-01",
        "candidate-02",
        "reference-02",
        "reference-03",
        "candidate-03",
    ]


def process_rss_bytes() -> tuple[int | None, str]:
    """Return current RSS and the exact measurement backend."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class ProcessMemoryCounters(ctypes.Structure):
            _fields_ = [
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = ProcessMemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
        if ok:
            return int(counters.WorkingSetSize), "WIN32_GetProcessMemoryInfo"
        return None, "WIN32_GetProcessMemoryInfo_FAILED"
    try:
        import resource

        value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        multiplier = 1 if sys.platform == "darwin" else 1024
        return int(value * multiplier), "resource.getrusage_ru_maxrss"
    except Exception:
        return None, f"UNAVAILABLE_pid_{os.getpid()}"
