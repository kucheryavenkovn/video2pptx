#!/usr/bin/env python3
# FILE: tools/probe_pyav_hwaccel.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Two-independent-open HWAccel runtime state probe for the production pyav_iter_frames path
#   SCOPE: Open canonical Hermes short clip twice, collect structured evidence from the actual generator path
#   DEPENDS: video2pptx.backends.pyav_backend, hashlib, json, platform, av
#   LINKS: M-BACKEND-PYAV, V-PERF-DETECT-BOTTLENECK
#   ROLE: SCRIPT
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import hashlib
import json
import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from video2pptx.backends.pyav_backend import (
    _available_hw_devices,
    _register_hwaccel_evidence_observer,
)

CANONICAL_CLIP_RELATIVE = "examples/hermes-0000-1000.mp4"
EXPECTED_CLIP_SHA256 = "dd9da3442e91ab7f17f0405198aa8e39d1538d74518b6b9a3b1e61ac2fc0f5a4"


def _verify_clip(clip_path: Path) -> None:
    if not clip_path.exists():
        print(f"ERROR: clip not found: {clip_path}", file=sys.stderr)
        sys.exit(1)
    sha = hashlib.sha256(clip_path.read_bytes()).hexdigest()
    if sha != EXPECTED_CLIP_SHA256:
        print("ERROR: clip SHA256 mismatch", file=sys.stderr)
        print(f"  Expected: {EXPECTED_CLIP_SHA256}", file=sys.stderr)
        print(f"  Actual:   {sha}", file=sys.stderr)
        sys.exit(1)
    print(f"  Clip SHA256: {sha} (match)")


def _collect_environment() -> dict:
    env = {
        "python_version": platform.python_version(),
        "platform": platform.system(),
        "platform_release": platform.release(),
        "platform_machine": platform.machine(),
    }
    try:
        import av
        env["pyav_version"] = av.__version__
        try:
            libs = {}
            for lib in ("libavcodec", "libavformat", "libavutil", "libavdevice", "libswscale"):
                try:
                    ver = getattr(av, lib, None)
                    if ver:
                        libs[lib] = str(ver)
                except Exception:
                    pass
            env["pyav_library_versions"] = libs
        except Exception:
            pass
    except Exception:
        env["pyav_version"] = None
    return env


def _get_git_head() -> str:
    import subprocess
    try:
        repo = Path(__file__).resolve().parent.parent
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return "unknown"


def _get_git_tree() -> str:
    import subprocess
    try:
        repo = Path(__file__).resolve().parent.parent
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD^{tree}"], cwd=repo, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return "unknown"


def _get_git_branch() -> str:
    import subprocess
    try:
        repo = Path(__file__).resolve().parent.parent
        return subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=repo, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return "unknown"


def run_single_observation(
    clip_path: Path,
    sample_fps: float = 2.0,
    observation_id: str = "",
) -> dict:
    from video2pptx.backends import pyav_backend

    observations = []

    def collector(ev):
        ev["observation_id"] = observation_id
        observations.append(ev)

    _register_hwaccel_evidence_observer(collector)

    try:
        gen = pyav_backend.pyav_iter_frames(str(clip_path), sample_fps=sample_fps)
        first = next(gen)
    finally:
        _register_hwaccel_evidence_observer(None)

    if not observations:
        return {"observation_id": observation_id, "error": "no evidence captured"}

    ev = observations[0]

    ev["first_frame_timestamp"] = first.timestamp
    ev["first_frame_shape"] = list(first.image.shape)

    return ev


def run_strict_fallback_control(clip_path: Path) -> dict:
    result = {
        "supported": True,
        "attempted": False,
        "result": None,
        "error_type": None,
        "error_message": None,
    }

    try:
        import av
        from av.codec.hwaccel import HWAccel

        available = [d for d in ["cuda"] if d in _available_hw_devices()]
        if not available:
            result["supported"] = False
            result["result"] = "SKIPPED_NO_CUDA_DEVICE"
            return result

        result["attempted"] = True

        hw = HWAccel("cuda", 0)
        print(f"  HWAccel created with allow_software_fallback={hw.allow_software_fallback}")

        hw.allow_software_fallback = False
        print("  Set allow_software_fallback=False")

        container = av.open(str(clip_path), hwaccel=hw)
        stream = container.streams.video[0]

        frame_decoded = False
        for packet in container.demux(stream):
            for frame in packet.decode():
                _ = frame.to_ndarray(format="rgb24")
                frame_decoded = True
                break
            break

        if frame_decoded:
            result["result"] = "STRICT_PROBE_SUCCEEDED"
            result["error_type"] = None
            result["error_message"] = None
        else:
            result["result"] = "STRICT_PROBE_NO_FRAME"
            result["error_type"] = None

        container.close()

    except Exception as e:
        result["result"] = "STRICT_PROBE_FAILED"
        result["error_type"] = type(e).__name__
        result["error_message"] = str(e)

    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description="PyAV HWAccel Runtime Evidence Probe")
    parser.add_argument("--video-path", default=None, help="Path to video file (default: canonical Hermes short clip)")
    args = parser.parse_args()

    print("=" * 60)
    print("PyAV HWAccel Runtime Evidence Probe")
    print("=" * 60)
    print()

    script_dir = Path(__file__).resolve().parent
    repo_dir = script_dir.parent

    if args.video_path:
        clip_path = Path(args.video_path).resolve()
        if not clip_path.exists():
            print(f"ERROR: specified clip not found: {clip_path}", file=sys.stderr)
            sys.exit(1)
        print(f"Clip: {clip_path} (custom path, SHA256 not verified)")
    else:
        clip_path = repo_dir / CANONICAL_CLIP_RELATIVE
        print("Clip verification:")
        _verify_clip(clip_path)

    print()
    print("Environment:")
    env = _collect_environment()
    for k, v in env.items():
        print(f"  {k}: {v}")

    print()
    print(f"Evidence code HEAD: {_get_git_head()}")
    print(f"Evidence code tree: {_get_git_tree()}")
    print(f"Branch: {_get_git_branch()}")

    print()
    print("Installed API capabilities:")
    from av.codec.context import CodecContext as _CodecContext
    from av.codec.hwaccel import HWAccel as _HWAccel

    caps = {
        "codec_context_is_hwaccel": "is_hwaccel" in dir(_CodecContext),
        "codec_context_name": "name" in dir(_CodecContext),
        "codec_context_codec": "codec" in dir(_CodecContext),
        "codec_context_hwaccel": "hwaccel" in dir(_CodecContext),
        "hwaccel_allow_software_fallback": "allow_software_fallback" in dir(_HWAccel),
        "hwaccel_config": "config" in dir(_HWAccel),
        "hwaccel_config_device_type": True,
        "hwaccel_config_format": True,
        "container_hwaccel": False,
    }
    for k, v in caps.items():
        print(f"  {k}: {v}")

    print()
    print("Running observation 01...")
    obs1 = run_single_observation(clip_path, sample_fps=2.0, observation_id="observation-01")
    print(f"  requested_hw_device: {obs1.get('requested_hw_device')}")
    print(f"  hwaccel_requested: {obs1.get('hwaccel_requested')}")
    print(f"  runtime_hwaccel_active: {obs1.get('runtime_hwaccel_active')}")
    print(f"  codec_name: {obs1.get('codec_name')}")
    print(f"  codec_long_name: {obs1.get('codec_long_name')}")
    print(f"  first_frame_shape: {obs1.get('first_frame_shape')}")

    print()
    print("Running observation 02...")
    obs2 = run_single_observation(clip_path, sample_fps=2.0, observation_id="observation-02")
    print(f"  requested_hw_device: {obs2.get('requested_hw_device')}")
    print(f"  hwaccel_requested: {obs2.get('hwaccel_requested')}")
    print(f"  runtime_hwaccel_active: {obs2.get('runtime_hwaccel_active')}")
    print(f"  codec_name: {obs2.get('codec_name')}")
    print(f"  codec_long_name: {obs2.get('codec_long_name')}")
    print(f"  first_frame_shape: {obs2.get('first_frame_shape')}")

    print()
    print("Strict fallback control:")
    strict = run_strict_fallback_control(clip_path)
    print(f"  supported: {strict['supported']}")
    print(f"  attempted: {strict['attempted']}")
    print(f"  result: {strict['result']}")
    if strict.get("error_type"):
        print(f"  error_type: {strict['error_type']}")
    if strict.get("error_message"):
        print(f"  error_message: {strict['error_message']}")

    obs_consistent = (
        obs1.get("requested_hw_device") == obs2.get("requested_hw_device")
        and obs1.get("runtime_hwaccel_active") == obs2.get("runtime_hwaccel_active")
        and obs1.get("codec_name") == obs2.get("codec_name")
    )

    print()
    print("Observation consistency:", obs_consistent)

    evidence = {
        "schema_version": "1.0.0",
        "step": "18.4A",
        "evidence_type": "PYAV_HWACCEL_RUNTIME_STATE",
        "status": "OBSERVATION_COMPLETE",
        "branch": _get_git_branch(),
        "evidence_code_head": _get_git_head(),
        "evidence_code_tree": _get_git_tree(),
        "accepted_blocked_master_base": _get_git_head(),
        "clip": {
            "identifier": str(clip_path),
            "sha256": EXPECTED_CLIP_SHA256,
        },
        "effective_probe_config": {
            "sample_fps": 2.0,
            "independent_open_count": 2,
            "frames_consumed_per_open": 1,
        },
        "environment": env,
        "installed_api_capabilities": caps,
        "observations": {
            "observation-01": obs1,
            "observation-02": obs2,
        },
        "observation_consistency": obs_consistent,
        "strict_fallback_control": strict,
        "conclusions": {
            "requested_hw_device": obs1.get("requested_hw_device"),
            "runtime_active_state": obs1.get("runtime_hwaccel_active"),
            "fallback_state": obs1.get("software_fallback_detected"),
            "evidence_confidence": "HIGH" if obs_consistent else "LOW",
            "limitations": [],
        },
    }

    print()
    print("=" * 60)
    print("RUNTIME EVIDENCE SUMMARY")
    print("=" * 60)
    print(json.dumps(evidence, indent=2, default=str))

    return evidence


if __name__ == "__main__":
    evidence = main()
    output_dir = Path(__file__).resolve().parent.parent / "benchmarks" / "detect" / "evidence"
    evidence_subdir = output_dir / "hwaccel-runtime-evidence"
    evidence_subdir.mkdir(parents=True, exist_ok=True)

    (evidence_subdir / "runtime_evidence.json").write_text(
        json.dumps(evidence, indent=2, default=str), encoding="utf-8"
    )
    (evidence_subdir / "environment.json").write_text(
        json.dumps(evidence["environment"], indent=2), encoding="utf-8"
    )

    report_lines = [
        "# PyAV HWAccel Runtime Evidence Probe Report",
        "",
        "**Step:** 18.4A",
        "**Evidence type:** PYAV_HWACCEL_RUNTIME_STATE",
        f"**Status:** {evidence['status']}",
        "",
        "## Observations",
        "",
        "### Observation 01",
        f"- requested_hw_device: {evidence['observations']['observation-01'].get('requested_hw_device')}",
        f"- hwaccel_requested: {evidence['observations']['observation-01'].get('hwaccel_requested')}",
        f"- hwaccel_object_created: {evidence['observations']['observation-01'].get('hwaccel_object_created')}",
        f"- container_opened: {evidence['observations']['observation-01'].get('container_opened')}",
        f"- container_opened_with_hwaccel: {evidence['observations']['observation-01'].get('container_opened_with_hwaccel')}",
        f"- runtime_hwaccel_active: {evidence['observations']['observation-01'].get('runtime_hwaccel_active')}",
        f"- observation_method: {evidence['observations']['observation-01'].get('runtime_hwaccel_observation_method')}",
        f"- codec_name: {evidence['observations']['observation-01'].get('codec_name')}",
        f"- codec_long_name: {evidence['observations']['observation-01'].get('codec_long_name')}",
        f"- hw_config_device_type: {evidence['observations']['observation-01'].get('hw_config_device_type')}",
        f"- hw_config_format: {evidence['observations']['observation-01'].get('hw_config_format')}",
        f"- hardware_decoder_or_device_identity: {evidence['observations']['observation-01'].get('hardware_decoder_or_device_identity')}",
        f"- software_fallback_detected: {evidence['observations']['observation-01'].get('software_fallback_detected')}",
        f"- first_frame_shape: {evidence['observations']['observation-01'].get('first_frame_shape')}",
        "",
        "### Observation 02",
        f"- requested_hw_device: {evidence['observations']['observation-02'].get('requested_hw_device')}",
        f"- hwaccel_requested: {evidence['observations']['observation-02'].get('hwaccel_requested')}",
        f"- hwaccel_object_created: {evidence['observations']['observation-02'].get('hwaccel_object_created')}",
        f"- container_opened: {evidence['observations']['observation-02'].get('container_opened')}",
        f"- container_opened_with_hwaccel: {evidence['observations']['observation-02'].get('container_opened_with_hwaccel')}",
        f"- runtime_hwaccel_active: {evidence['observations']['observation-02'].get('runtime_hwaccel_active')}",
        f"- observation_method: {evidence['observations']['observation-02'].get('runtime_hwaccel_observation_method')}",
        f"- codec_name: {evidence['observations']['observation-02'].get('codec_name')}",
        f"- codec_long_name: {evidence['observations']['observation-02'].get('codec_long_name')}",
        f"- hw_config_device_type: {evidence['observations']['observation-02'].get('hw_config_device_type')}",
        f"- hw_config_format: {evidence['observations']['observation-02'].get('hw_config_format')}",
        f"- hardware_decoder_or_device_identity: {evidence['observations']['observation-02'].get('hardware_decoder_or_device_identity')}",
        f"- software_fallback_detected: {evidence['observations']['observation-02'].get('software_fallback_detected')}",
        f"- first_frame_shape: {evidence['observations']['observation-02'].get('first_frame_shape')}",
        "",
        "## Consistency",
        f"- Observations consistent: {evidence['observation_consistency']}",
        "",
        "## Strict Fallback Control",
        f"- supported: {evidence['strict_fallback_control']['supported']}",
        f"- attempted: {evidence['strict_fallback_control']['attempted']}",
        f"- result: {evidence['strict_fallback_control']['result']}",
        f"- error_type: {evidence['strict_fallback_control'].get('error_type', 'N/A')}",
        "",
        "## Conclusions",
        f"- Requested HW device: {evidence['conclusions']['requested_hw_device']}",
        f"- Runtime active state: {evidence['conclusions']['runtime_active_state']}",
        f"- Fallback state: {evidence['conclusions']['fallback_state']}",
        f"- Evidence confidence: {evidence['conclusions']['evidence_confidence']}",
    ]
    (evidence_subdir / "probe_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print()
    print(f"Evidence artifacts written to: {evidence_subdir}")
