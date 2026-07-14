#!/usr/bin/env python3
# FILE: tools/probe_pyav_decode_config.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: C3 diagnostic — inspect installed PyAV decoder configuration
#            boundaries and probe selected variants for exact frame parity
#            and wall-clock decode cost.
#   SCOPE: API inspection, variant selection, decoder-only parity probe,
#          optional microbenchmark.
#   DEPENDS: av, numpy, hashlib, tools.discrimination_helpers
#   LINKS: M-DETECT-PERF-DECISION, V-PERF-DETECT-BOTTLENECK
#   ROLE: SCRIPT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   inspect_codec_context - list writable/readable codec context properties and classify
#   decode_pass_probe - run one decode pass at sample_fps and collect frame signatures
#   main - CLI entry producing JSON evidence artifacts
# END_MODULE_MAP
"""C3 diagnostic: PYAV_DECODE_CONFIGURATION_TUNING."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from discrimination_helpers import (  # noqa: E402
    build_streaming_frame_signature,
    check_sequence_parity,
    compute_mean,
    compute_median,
    compute_median_reduction_percent,
    compute_paired_absolute_savings,
    compute_paired_percentage_reduction,
    compute_sample_stdev,
    directional_stability,
    validate_c3_variant_metadata,
)

# Properties to inspect on the codec context.
# Each is classified by its likely effect on the sampled frame sequence.
_INSPECT_PROPERTIES = [
    "thread_type",
    "thread_count",
    "low_delay",
    "skip_loop_filter",
    "skip_non_ref",
    "skip_idct",
    "skip_frame",
]

# FFmpeg skip enum values for classification.
_SKIP_VALUES = {
    0: "SKIP_NONE",
    16: "SKIP_DEFAULT",
    8: "SKIP_NONREF",
    32: "SKIP_BITSTREAM",
    64: "SKIP_NONINTRA",
}

# Threading type flags (from FFmpeg avcodec.h).
_THREAD_TYPE_FLAGS = {
    0: "NONE",
    1: "FRAME",
    2: "SLICE",
    3: "FRAME_SLICE",
}


# =========================================================================
# API inspection
# =========================================================================


def inspect_codec_context(video_path: str) -> dict[str, Any]:
    """Inspect writable/readable codec context properties and classify them."""
    import av

    from video2pptx.backends.pyav_backend import (
        _create_hwaccel_with_evidence,
        _pick_hw_device,
    )

    hw_device = _pick_hw_device()
    hwaccel = None
    if hw_device is not None:
        hwaccel, _, _ = _create_hwaccel_with_evidence(hw_device)

    container = av.open(video_path, hwaccel=hwaccel)
    stream = container.streams.video[0]
    codec_ctx = stream.codec_context

    properties: dict[str, Any] = {}
    for prop_name in _INSPECT_PROPERTIES:
        entry: dict[str, Any] = {"name": prop_name}
        try:
            default_val = getattr(codec_ctx, prop_name)
            entry["readable"] = True
            entry["default_value"] = default_val
            entry["default_value_repr"] = (
                _THREAD_TYPE_FLAGS.get(default_val, _SKIP_VALUES.get(default_val, str(default_val)))
            )
        except Exception:
            entry["readable"] = False
            entry["default_value"] = None

        try:
            setattr(codec_ctx, prop_name, entry.get("default_value"))
            entry["writable"] = True
        except Exception:
            entry["writable"] = False

        entry["classification"] = _classify_property(prop_name, entry)
        properties[prop_name] = entry

    container.close()

    return {
        "pyav_version": av.__version__,
        "hw_device": hw_device,
        "hwaccel_enabled": hwaccel is not None,
        "codec_name": codec_ctx.codec.name if codec_ctx.codec else None,
        "properties": properties,
    }


def _classify_property(prop_name: str, entry: dict[str, Any]) -> str:
    """Classify a codec context property by its frame-sequence effect."""
    if not entry.get("writable"):
        return "NOT_AVAILABLE"
    if prop_name in ("skip_loop_filter", "skip_non_ref", "skip_idct", "skip_frame"):
        return "SEMANTICS_CHANGE_FRAME_SEQUENCE"
    if prop_name in ("thread_type", "thread_count"):
        return "POTENTIALLY_PARITY_PRESERVING"
    if prop_name == "low_delay":
        return "UNKNOWN"
    return "UNKNOWN"


# =========================================================================
# Decode probe
# =========================================================================


def decode_pass_probe(
    video_path: str,
    sample_fps: float = 2.0,
    config_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one decode pass at sample_fps and collect per-frame signatures.

    Returns wall-clock, yielded-frame count, per-frame signatures, and a
    deterministic sequence signature.  Does NOT retain full frames.
    """
    import av

    from video2pptx.backends.pyav_backend import (
        _create_hwaccel_with_evidence,
        _pick_hw_device,
    )

    hw_device = _pick_hw_device()
    hwaccel = None
    if hw_device is not None:
        hwaccel, _, _ = _create_hwaccel_with_evidence(hw_device)

    container = av.open(video_path, hwaccel=hwaccel)
    stream = container.streams.video[0]
    codec_ctx = stream.codec_context

    config_applied: dict[str, Any] = {}
    if config_overrides:
        for key, val in config_overrides.items():
            try:
                setattr(codec_ctx, key, val)
                config_applied[key] = val
            except Exception as e:
                container.close()
                return {
                    "error": f"Failed to set {key}={val}: {e}",
                    "config_applied": config_applied,
                }

    video_fps = float(stream.average_rate)
    if video_fps <= 0:
        video_fps = 30.0
    frame_interval = max(1, int(round(video_fps / sample_fps)))

    current_frame_idx = 0
    frames_decoded = 0
    ndarray_conversions = 0
    rgb_transfer_bytes = 0

    frame_signatures: list[dict[str, Any]] = []
    yielded_timestamps: list[float] = []
    frame_hashes: list[str] = []

    start = time.perf_counter()
    try:
        for packet in container.demux(stream):
            for frame in packet.decode():
                frames_decoded += 1

                if current_frame_idx % frame_interval == 0:
                    timestamp = current_frame_idx / video_fps
                    img = frame.to_ndarray(format="rgb24")
                    ndarray_conversions += 1
                    rgb_transfer_bytes += img.nbytes

                    sha = hashlib.sha256(img.tobytes()).hexdigest()
                    frame_hashes.append(sha)
                    yielded_timestamps.append(float(timestamp))
                    frame_signatures.append({
                        "yield_index": len(frame_signatures),
                        "timestamp": float(timestamp),
                        "shape": list(img.shape),
                        "rgb_sha256": sha,
                    })

                current_frame_idx += 1
    finally:
        container.close()

    elapsed = time.perf_counter() - start
    seq_sig = build_streaming_frame_signature(frame_signatures)

    return {
        "wall_clock_seconds": elapsed,
        "frames_decoded": frames_decoded,
        "frames_yielded": len(frame_signatures),
        "ndarray_conversions": ndarray_conversions,
        "rgb_transfer_bytes": rgb_transfer_bytes,
        "video_fps": video_fps,
        "frame_interval": frame_interval,
        "yielded_timestamps": yielded_timestamps,
        "frame_hashes": frame_hashes,
        "sequence_signature": seq_sig,
        "config_applied": config_applied,
    }


# =========================================================================
# Main
# =========================================================================


def main():
    parser = argparse.ArgumentParser(
        description="C3 diagnostic: PyAV decode configuration tuning"
    )
    parser.add_argument("--video", required=True, help="Path to canonical video clip")
    parser.add_argument("--output", required=True, help="Output evidence directory")
    parser.add_argument(
        "--benchmark", action="store_true",
        help="Run microbenchmark for approved variants",
    )
    args = parser.parse_args()

    video_path = str(Path(args.video).resolve())
    if not Path(video_path).is_file():
        print(f"ERROR: video not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)

    print("=== C3: Inspecting codec context properties ===")
    inspection = inspect_codec_context(video_path)
    print(f"  PyAV version: {inspection['pyav_version']}")
    print(f"  HW device: {inspection['hw_device']}")
    print(f"  HWaccel enabled: {inspection['hwaccel_enabled']}")
    print(f"  Codec: {inspection['codec_name']}")
    for name, prop in inspection["properties"].items():
        print(
            f"  {name}: writable={prop['writable']} "
            f"default={prop.get('default_value')} "
            f"classification={prop['classification']}"
        )

    (out / "c3_codec_context_inspection.json").write_text(
        json.dumps(inspection, indent=2, default=str), encoding="utf-8"
    )

    # Select variants: only POTENTIALLY_PARITY_PRESERVING writable properties.
    variants: list[dict[str, Any]] = []
    for name, prop in inspection["properties"].items():
        if (
            prop["writable"]
            and prop["classification"] == "POTENTIALLY_PARITY_PRESERVING"
        ):
            if name == "thread_count":
                default_val = prop.get("default_value", 0)
                for candidate_val in [1, 4, 8]:
                    if candidate_val != default_val:
                        variants.append({
                            "name": f"thread_count_{candidate_val}",
                            "property_or_options_boundary": f"codec_context.{name}",
                            "default_value": default_val,
                            "candidate_value": candidate_val,
                            "mechanistic_hypothesis": (
                                f"Setting {name}={candidate_val} may change decoder "
                                f"threading model, potentially affecting decode throughput."
                            ),
                            "frame_sequence_parity_risk": "LOW — thread count should not alter decoded pixels",
                            "hwaccel_compatibility_risk": (
                                "HIGH — NVDEC hardware decoder handles its own parallelism; "
                                "software thread count may have no effect on HW decode path"
                            ),
                        })
            elif name == "thread_type":
                default_val = prop.get("default_value", 0)
                for candidate_val in [1, 2]:
                    if candidate_val != default_val:
                        variants.append({
                            "name": f"thread_type_{'FRAME' if candidate_val == 1 else 'SLICE'}",
                            "property_or_options_boundary": f"codec_context.{name}",
                            "default_value": default_val,
                            "candidate_value": candidate_val,
                            "mechanistic_hypothesis": (
                                f"Setting {name}={candidate_val} may change decoder "
                                f"threading model."
                            ),
                            "frame_sequence_parity_risk": "LOW",
                            "hwaccel_compatibility_risk": "HIGH — HW decoder may ignore thread type",
                        })

    # Limit to 3 variants.
    variants = variants[:3]

    if not variants:
        print("\nNO_EVIDENCE_SUPPORTED_CONFIGURATION_VARIANT")
        c3_variants_data = {
            "variants": [],
            "result": "NO_EVIDENCE_SUPPORTED_CONFIGURATION_VARIANT",
        }
        (out / "c3_variants.json").write_text(
            json.dumps(c3_variants_data, indent=2, default=str), encoding="utf-8"
        )
        print(f"\nEvidence written to {out}")
        return

    for v in variants:
        validate_c3_variant_metadata(v)

    print(f"\n=== {len(variants)} C3 variant(s) selected ===")
    for v in variants:
        print(f"  {v['name']}: {v['property_or_options_boundary']}={v['candidate_value']}")

    c3_variants_data = {
        "variants": variants,
        "inspection": inspection,
    }
    (out / "c3_variants.json").write_text(
        json.dumps(c3_variants_data, indent=2, default=str), encoding="utf-8"
    )

    # Reference probe.
    print("\nRunning reference decode probe...")
    ref_probe = decode_pass_probe(video_path, sample_fps=2.0)
    print(f"  Reference: {ref_probe['wall_clock_seconds']:.1f}s, "
          f"{ref_probe['frames_yielded']} frames yielded")

    all_results: list[dict[str, Any]] = []

    for variant in variants:
        name = variant["name"]
        overrides = {variant["property_or_options_boundary"].split(".")[-1]: variant["candidate_value"]}

        print(f"\nRunning variant: {name}")
        # Parity probe.
        cand_probe = decode_pass_probe(video_path, sample_fps=2.0, config_overrides=overrides)
        if "error" in cand_probe:
            print(f"  ERROR: {cand_probe['error']}")
            all_results.append({"variant": name, "error": cand_probe["error"], "parity": {"parity_pass": False}})
            continue

        parity = check_sequence_parity(
            ref_probe["sequence_signature"],
            cand_probe["sequence_signature"],
            ref_probe["frames_yielded"],
            cand_probe["frames_yielded"],
            ref_probe["yielded_timestamps"],
            cand_probe["yielded_timestamps"],
            ref_probe["frame_hashes"],
            cand_probe["frame_hashes"],
        )
        print(f"  Parity: {'PASS' if parity['parity_pass'] else 'FAIL'}")

        variant_result: dict[str, Any] = {
            "variant": name,
            "parity": parity,
            "reference_wall_clock": ref_probe["wall_clock_seconds"],
            "candidate_wall_clock": cand_probe["wall_clock_seconds"],
        }

        if parity["parity_pass"] and args.benchmark:
            print(f"  Benchmarking {name}...")
            ref_runs: list[float] = []
            cand_runs: list[float] = []
            for i in range(3):
                decode_pass_probe(video_path, sample_fps=2.0)  # warmup
                r = decode_pass_probe(video_path, sample_fps=2.0)
                ref_runs.append(r["wall_clock_seconds"])

                decode_pass_probe(video_path, sample_fps=2.0, config_overrides=overrides)  # warmup
                c = decode_pass_probe(video_path, sample_fps=2.0, config_overrides=overrides)
                cand_runs.append(c["wall_clock_seconds"])
                print(f"    Run {i+1}: ref={ref_runs[-1]:.1f}s cand={cand_runs[-1]:.1f}s")

            savings = compute_paired_absolute_savings(ref_runs, cand_runs)
            reductions = compute_paired_percentage_reduction(ref_runs, cand_runs)
            variant_result["benchmark"] = {
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
        elif not parity["parity_pass"]:
            variant_result["benchmark_skipped"] = "PARITY_FAILED"

        all_results.append(variant_result)

    c3_results = {
        "reference_probe": {k: v for k, v in ref_probe.items()
                            if k not in ("yielded_timestamps", "frame_hashes")},
        "variant_results": all_results,
    }
    (out / "c3_runs.json").write_text(
        json.dumps(c3_results, indent=2, default=str), encoding="utf-8"
    )

    # Frame parity artifact.
    c3_frame_parity = {
        v["variant"]: v.get("parity", {}) for v in all_results
    }
    (out / "c3_frame_parity.json").write_text(
        json.dumps(c3_frame_parity, indent=2, default=str), encoding="utf-8"
    )

    print(f"\nEvidence written to {out}")


if __name__ == "__main__":
    main()
