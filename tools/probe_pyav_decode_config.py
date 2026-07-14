#!/usr/bin/env python3
# FILE: tools/probe_pyav_decode_config.py
# VERSION: 2.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Emit provenance-bound C3 decoder-configuration discrimination evidence.
#   SCOPE: Live API inspection, deterministic selection, consistency guarding, exact sequence parity, and conditional paired timing.
#   DEPENDS: av, numpy, platform process APIs, tools.discrimination_helpers, video2pptx.backends.pyav_backend
#   LINKS: M-DETECT-PERF-DECISION, V-PERF-DETECT-TARGET-OPTIMIZATION-DISCRIMINATION
#   ROLE: SCRIPT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   inspect_codec_context - record live decoder property boundaries
#   decode_pass_probe - execute one production-equivalent sampled decode pass
#   validate_canonical_clip - reject byte identity mismatches
#   select_c3_variants - imported deterministic candidate selector
#   main - validate provenance and directly emit C3 child artifacts
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v2.0.0 - Replaced contradictory C3 artifact flow with deterministic selection, provenance, and repeatability-aware execution
# END_CHANGE_SUMMARY
"""Corrected C3 diagnostic for Step 18.4C-r2."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from discrimination_helpers import (  # noqa: E402
    balanced_recorded_order,
    build_streaming_frame_signature,
    check_c3_selection_consistency,
    check_sequence_parity,
    collect_git_provenance,
    compute_mean,
    compute_median,
    compute_paired_absolute_savings,
    compute_paired_percentage_reduction,
    compute_sample_stdev,
    directional_stability,
    process_rss_bytes,
    select_c3_variants,
    validate_accepted_base,
    validate_c3_variant_metadata,
)

EXPECTED_CLIP_SHA256 = "dd9da3442e91ab7f17f0405198aa8e39d1538d74518b6b9a3b1e61ac2fc0f5a4"
_INSPECT_PROPERTIES = (
    "thread_type",
    "thread_count",
    "low_delay",
    "skip_loop_filter",
    "skip_non_ref",
    "skip_idct",
    "skip_frame",
)


def _json_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    try:
        return int(value)
    except (TypeError, ValueError):
        return str(value)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_canonical_clip(path: Path) -> str:
    """Return the exact canonical SHA or reject a mismatched clip."""
    actual = _sha256(path)
    if actual != EXPECTED_CLIP_SHA256:
        raise ValueError(f"canonical SHA256 mismatch: {actual}")
    return actual


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8")


def _classify_property(name: str, writable: bool) -> str:
    if not writable:
        return "NOT_AVAILABLE"
    if name in {"thread_count", "thread_type"}:
        return "POTENTIALLY_PARITY_PRESERVING"
    if name in {"skip_loop_filter", "skip_non_ref", "skip_idct", "skip_frame"}:
        return "SEMANTICS_CHANGE_FRAME_SEQUENCE"
    return "UNKNOWN"


def _open_context(video_path: Path):
    import av

    from video2pptx.backends.pyav_backend import _create_hwaccel_with_evidence, _pick_hw_device

    hw_device = _pick_hw_device()
    hwaccel = None
    if hw_device is not None:
        hwaccel, _, _ = _create_hwaccel_with_evidence(hw_device)
    container = av.open(str(video_path), hwaccel=hwaccel)
    stream = container.streams.video[0]
    return container, stream, hw_device, hwaccel


def inspect_codec_context(video_path: Path) -> dict[str, Any]:
    """Inspect live codec-context properties without inferring active HW decode."""
    import av

    container, stream, hw_device, hwaccel = _open_context(video_path)
    try:
        context = stream.codec_context
        properties: dict[str, Any] = {}
        for name in _INSPECT_PROPERTIES:
            entry: dict[str, Any] = {"name": name}
            try:
                value = getattr(context, name)
                entry.update(
                    readable=True, default_value=_json_value(value), observed_value_repr=str(value)
                )
            except Exception as exc:
                value = None
                entry.update(readable=False, default_value=None, read_error=type(exc).__name__)
            try:
                setattr(context, name, value)
                writable = True
            except Exception as exc:
                writable = False
                entry["write_error"] = type(exc).__name__
            entry["writable"] = writable
            entry["classification"] = _classify_property(name, writable)
            entry["eligible"] = (
                writable and entry["classification"] == "POTENTIALLY_PARITY_PRESERVING"
            )
            entry["eligibility_reason"] = (
                "WRITABLE_AND_POTENTIALLY_PARITY_PRESERVING"
                if entry["eligible"]
                else "ELIGIBILITY_RULE_NOT_SATISFIED"
            )
            entry["exclusion_reason"] = None if entry["eligible"] else entry["eligibility_reason"]
            entry["direct_runtime_exclusion_evidence"] = None
            properties[name] = entry
        try:
            codec_context_is_hwaccel = bool(context.is_hwaccel)
        except Exception:
            codec_context_is_hwaccel = None
        return {
            "pyav_version": av.__version__,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "hw_device_requested": hw_device,
            "hwaccel_object_created": hwaccel is not None,
            "hwaccel_object_repr": repr(hwaccel),
            "codec_context_is_hwaccel": codec_context_is_hwaccel,
            "actual_hardware_decode_active": "UNKNOWN_NOT_PROVEN",
            "codec_name": context.codec.name if context.codec else None,
            "properties": properties,
        }
    finally:
        container.close()


def decode_pass_probe(
    video_path: Path,
    sample_fps: float = 2.0,
    config_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one fresh complete sampled decode and stream exact frame signatures."""
    container, stream, _, _ = _open_context(video_path)
    context = stream.codec_context
    applied: dict[str, Any] = {}
    if config_overrides:
        for name, value in config_overrides.items():
            setattr(context, name, value)
            applied[name] = value
    video_fps = float(stream.average_rate or 30.0)
    frame_interval = max(1, int(round(video_fps / sample_fps)))
    initial_rss, rss_backend = process_rss_bytes()
    peak_rss = initial_rss or 0
    current_frame_idx = 0
    frames_decoded = 0
    conversions = 0
    transfer_bytes = 0
    signatures: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        for packet in container.demux(stream):
            for frame in packet.decode():
                frames_decoded += 1
                if current_frame_idx % frame_interval == 0:
                    image = frame.to_ndarray(format="rgb24")
                    sha = hashlib.sha256(image.tobytes()).hexdigest()
                    signatures.append(
                        {
                            "yield_index": len(signatures),
                            "timestamp": current_frame_idx / video_fps,
                            "shape": list(image.shape),
                            "rgb_sha256": sha,
                        }
                    )
                    conversions += 1
                    transfer_bytes += image.nbytes
                current_frame_idx += 1
                if frames_decoded % 600 == 0:
                    current_rss, _ = process_rss_bytes()
                    peak_rss = max(peak_rss, current_rss or 0)
    finally:
        container.close()
    elapsed = time.perf_counter() - started
    current_rss, _ = process_rss_bytes()
    peak_rss = max(peak_rss, current_rss or 0)
    return {
        "wall_clock_seconds": elapsed,
        "frames_decoded": frames_decoded,
        "frames_yielded": len(signatures),
        "ndarray_conversions": conversions,
        "rgb_transfer_bytes": transfer_bytes,
        "peak_rss_bytes": peak_rss,
        "rss_measurement_backend": rss_backend,
        "video_fps": video_fps,
        "frame_interval": frame_interval,
        "config_applied": applied,
        "frame_signatures": signatures,
        "yielded_timestamps": [entry["timestamp"] for entry in signatures],
        "shapes": [entry["shape"] for entry in signatures],
        "frame_hashes": [entry["rgb_sha256"] for entry in signatures],
        "sequence_signature": build_streaming_frame_signature(signatures),
    }


def _timing_summary(
    reference_runs: list[dict[str, Any]], candidate_runs: list[dict[str, Any]]
) -> dict[str, Any]:
    reference = [run["wall_clock_seconds"] for run in reference_runs]
    candidate = [run["wall_clock_seconds"] for run in candidate_runs]
    savings = compute_paired_absolute_savings(reference, candidate)
    reductions = compute_paired_percentage_reduction(reference, candidate)
    return {
        "reference_runs": reference_runs,
        "candidate_runs": candidate_runs,
        "reference_seconds": reference,
        "candidate_seconds": candidate,
        "reference_median": compute_median(reference),
        "candidate_median": compute_median(candidate),
        "reference_mean": compute_mean(reference),
        "candidate_mean": compute_mean(candidate),
        "reference_sample_stdev": compute_sample_stdev(reference),
        "candidate_sample_stdev": compute_sample_stdev(candidate),
        "paired_absolute_savings": savings,
        "paired_percentage_reductions": reductions,
        "median_seconds_saved": compute_median(savings),
        "median_reduction_percent": compute_median(reductions),
        "directional_stability": directional_stability(reference, candidate),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Corrected C3 decoder configuration discrimination"
    )
    parser.add_argument("--canonical-mode", action="store_true")
    parser.add_argument("--accepted-base", required=True)
    parser.add_argument("--video", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    repo = Path(__file__).resolve().parent.parent
    video = Path(args.video).resolve()
    output = Path(args.output).resolve()
    if not args.canonical_mode:
        raise ValueError("--canonical-mode is required for corrected evidence")
    if not video.is_file():
        raise ValueError(f"video not found: {video}")
    validate_accepted_base(args.accepted_base, repo)
    provenance = collect_git_provenance(repo, output)
    clip_sha = validate_canonical_clip(video)
    output.mkdir(parents=True, exist_ok=True)

    base = {
        **provenance,
        "accepted_master_base": args.accepted_base,
        "clip_actual_sha256": clip_sha,
        "clip_expected_sha256": EXPECTED_CLIP_SHA256,
        "sha256_match": True,
    }
    inspection = {**base, **inspect_codec_context(video)}
    _write_json(output / "c3_inspection.json", inspection)

    variants = select_c3_variants(inspection, max_variants=3)
    for variant in variants:
        validate_c3_variant_metadata(variant)
    consistency = check_c3_selection_consistency(inspection, variants)
    variants_artifact = {
        **base,
        "selection_function": "select_c3_variants(inspection, max_variants=3)",
        "eligibility_rule": "writable == true AND classification == POTENTIALLY_PARITY_PRESERVING",
        "candidate_selection_consistency": consistency,
        "eligible_boundaries": [
            name for name, value in inspection["properties"].items() if value["eligible"]
        ],
        "approved_variants": variants,
    }
    _write_json(output / "c3_variants.json", variants_artifact)
    if consistency == "FAIL_ELIGIBLE_BOUNDARIES_WITH_ZERO_VARIANTS":
        raise RuntimeError(consistency)

    repeatability = json.loads(
        (output / "reference_repeatability.json").read_text(encoding="utf-8")
    )
    if repeatability["classification"] != "REFERENCE_EXACTLY_REPEATABLE":
        blocked = {
            **base,
            "reference_repeatability_classification": repeatability["classification"],
            "state": "BLOCKED_REFERENCE_NONDETERMINISM",
            "result": "C3_EVALUATION_BLOCKED_BY_REFERENCE_NONDETERMINISM",
            "variants_not_rejected": [variant["name"] for variant in variants],
        }
        _write_json(output / "c3_frame_parity.json", blocked)
        return 0

    parity_results: dict[str, Any] = {**base, "variants": {}}
    run_results: dict[str, Any] = {
        **base,
        "recorded_order": balanced_recorded_order(),
        "variants": {},
    }
    for variant in variants:
        override_name = variant["property_or_options_boundary"].split(".")[-1]
        overrides = {override_name: variant["candidate_value"]}
        reference_probe = decode_pass_probe(video)
        candidate_probe = decode_pass_probe(video, config_overrides=overrides)
        parity = check_sequence_parity(
            reference_probe["sequence_signature"],
            candidate_probe["sequence_signature"],
            reference_probe["frames_yielded"],
            candidate_probe["frames_yielded"],
            reference_probe["yielded_timestamps"],
            candidate_probe["yielded_timestamps"],
            reference_probe["frame_hashes"],
            candidate_probe["frame_hashes"],
        )
        parity["shape_sequence_identical"] = reference_probe["shapes"] == candidate_probe["shapes"]
        parity["parity_pass"] = parity["parity_pass"] and parity["shape_sequence_identical"]
        parity_results["variants"][variant["name"]] = {
            "override": overrides,
            "parity": parity,
            "reference": reference_probe,
            "candidate": candidate_probe,
        }
        if not parity["parity_pass"]:
            run_results["variants"][variant["name"]] = {
                "measured": False,
                "reason": "NOT_VIABLE_PARITY_FAIL",
            }
            continue

        warmups = {
            "reference": decode_pass_probe(video),
            "candidate": decode_pass_probe(video, config_overrides=overrides),
        }
        references: dict[int, dict[str, Any]] = {}
        candidates: dict[int, dict[str, Any]] = {}
        for item in balanced_recorded_order():
            method, number_text = item.split("-")
            number = int(number_text)
            run = decode_pass_probe(
                video, config_overrides=overrides if method == "candidate" else None
            )
            run.pop("frame_signatures")
            run.pop("yielded_timestamps")
            run.pop("shapes")
            run.pop("frame_hashes")
            (references if method == "reference" else candidates)[number] = run
        summary = _timing_summary(
            [references[index] for index in (1, 2, 3)],
            [candidates[index] for index in (1, 2, 3)],
        )
        summary["warmups"] = {key: value["wall_clock_seconds"] for key, value in warmups.items()}
        summary["viable"] = (
            summary["directional_stability"] and summary["median_reduction_percent"] >= 15.0
        )
        summary["state"] = "VIABLE" if summary["viable"] else "NOT_VIABLE_PERFORMANCE_FAIL"
        run_results["variants"][variant["name"]] = summary

    _write_json(output / "c3_frame_parity.json", parity_results)
    _write_json(output / "c3_runs.json", run_results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
