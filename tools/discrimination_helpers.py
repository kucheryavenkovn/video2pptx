#!/usr/bin/env python3
# FILE: tools/discrimination_helpers.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Pure deterministic helpers for Step 18.4C target-optimization discrimination.
#   SCOPE: Statistics (median/mean/stdev/paired reductions), frame parity checking,
#          C2 resource byte calculations, C3 variant metadata validation,
#          streaming frame sequence signatures.
#   DEPENDS: hashlib, json, statistics
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
# END_MODULE_MAP
"""
Pure deterministic helpers for Step 18.4C target-optimization discrimination.
No timing sleeps, no I/O side effects, no randomness.
"""

from __future__ import annotations

import hashlib
import json
import statistics
from typing import Any

_GB = 1_000_000_000
_GIB = 1024 ** 3


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


def compute_paired_absolute_savings(
    reference: list[float], candidate: list[float]
) -> list[float]:
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


def compute_median_reduction_percent(
    reference: list[float], candidate: list[float]
) -> float:
    return compute_median(compute_paired_percentage_reduction(reference, candidate))


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

        entry["status"] = "PASS" if (
            ts_match and sha_match and shape_match and
            (entry["exact_byte_match"] is not False)
        ) else "FAIL"
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
