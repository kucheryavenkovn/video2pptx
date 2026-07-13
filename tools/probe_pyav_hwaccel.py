#!/usr/bin/env python3
# FILE: tools/probe_pyav_hwaccel.py
# VERSION: 2.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Two-independent-open HWAccel runtime state probe for the production pyav_iter_frames path
#   SCOPE: Open canonical Hermes short clip twice, collect structured evidence
#   DEPENDS: video2pptx.backends.pyav_backend, hashlib, json, platform, av, subprocess
#   LINKS: M-BACKEND-PYAV, V-PERF-DETECT-BOTTLENECK
#   ROLE: SCRIPT
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from video2pptx.backends.pyav_backend import (
    _available_hw_devices,
    _register_hwaccel_evidence_observer,
)

CANONICAL_FILENAME = "hermes-0000-1000.mp4"
EXPECTED_CLIP_SHA256 = "dd9da3442e91ab7f17f0405198aa8e39d1538d74518b6b9a3b1e61ac2fc0f5a4"


def _git(cmd: list[str], repo: Path) -> str:
    try:
        return subprocess.check_output(
            ["git"] + cmd, cwd=repo, stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        return "unknown"


def _resolve_git_object(sha: str, repo: Path) -> tuple[bool, str]:
    if len(sha) != 40 or not all(c in "0123456789abcdef" for c in sha):
        return False, "not a full 40-char hex SHA"
    try:
        obj_type = subprocess.check_output(
            ["git", "cat-file", "-t", sha], cwd=repo, stderr=subprocess.DEVNULL, text=True
        ).strip()
        return True, obj_type
    except subprocess.CalledProcessError:
        return False, "git object not found"


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

    gen = None
    first_frame = None
    try:
        gen = pyav_backend.pyav_iter_frames(str(clip_path), sample_fps=sample_fps)
        first_frame = next(gen)
    finally:
        if gen is not None:
            gen.close()
        _register_hwaccel_evidence_observer(None)

    if not observations:
        return {"observation_id": observation_id, "error": "no evidence captured"}

    ev = observations[0]
    if first_frame is not None:
        ev["first_frame_timestamp"] = first_frame.timestamp
        ev["first_frame_shape"] = list(first_frame.image.shape)
    else:
        ev["first_frame_yielded"] = False

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
        hw.allow_software_fallback = False
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
        else:
            result["result"] = "STRICT_PROBE_NO_FRAME"
        container.close()
    except Exception as e:
        result["result"] = "STRICT_PROBE_FAILED"
        result["error_type"] = type(e).__name__
        result["error_message"] = str(e)
    return result


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
    except Exception:
        env["pyav_version"] = None
    return env


def main():
    parser = argparse.ArgumentParser(description="PyAV HWAccel Runtime Evidence Probe")
    parser.add_argument("--video-path", default=None,
                        help="Video path. Without --canonical-mode, SHA256 not verified.")
    parser.add_argument("--canonical-mode", action="store_true",
                        help="Require exact canonical clip SHA256")
    parser.add_argument("--accepted-base", default="f52e82c55744de077984db3b9bcb2162d4f9d87f",
                        help="Accepted blocked master base SHA (default: merged master)")
    parser.add_argument("--output-dir", default=None,
                        help="Evidence output directory (default: auto)")
    args = parser.parse_args()

    repo_dir = Path(__file__).resolve().parent.parent

    # Validate accepted base
    is_valid, obj_type = _resolve_git_object(args.accepted_base, repo_dir)
    if not is_valid:
        print(f"ERROR: accepted base SHA not valid: {args.accepted_base}", file=sys.stderr)
        sys.exit(1)
    if obj_type != "commit":
        print(f"ERROR: accepted base is {obj_type}, expected commit", file=sys.stderr)
        sys.exit(1)

    accepted_base = args.accepted_base
    evidence_head = _git(["rev-parse", "HEAD"], repo_dir)
    evidence_tree = _git(["rev-parse", "HEAD^{tree}"], repo_dir)
    branch = _git(["branch", "--show-current"], repo_dir)

    # Verify accepted base is ancestor of current HEAD
    try:
        subprocess.check_call(
            ["git", "merge-base", "--is-ancestor", accepted_base, "HEAD"],
            cwd=repo_dir, stderr=subprocess.DEVNULL,
        )
        print(f"Accepted base {accepted_base} is ancestor of HEAD")
    except subprocess.CalledProcessError:
        print(f"ERROR: accepted base {accepted_base} is NOT ancestor of HEAD", file=sys.stderr)
        sys.exit(1)

    # Resolve clip
    canonical_mode = args.canonical_mode
    if args.video_path:
        clip_path = Path(args.video_path).resolve()
        if not clip_path.exists():
            print(f"ERROR: clip not found: {clip_path}", file=sys.stderr)
            sys.exit(1)
    else:
        clip_path = repo_dir / "examples" / CANONICAL_FILENAME

    # Compute actual SHA
    actual_clip_sha256 = hashlib.sha256(clip_path.read_bytes()).hexdigest()
    sha256_match = actual_clip_sha256 == EXPECTED_CLIP_SHA256

    # Verify canonical mode constraint
    if canonical_mode and not sha256_match:
        print(f"ERROR: canonical mode requires clip SHA256 = {EXPECTED_CLIP_SHA256}", file=sys.stderr)
        print(f"  Actual: {actual_clip_sha256}", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("PyAV HWAccel Runtime Evidence Probe")
    print("=" * 60)
    print(f"Clip: {clip_path}")
    print(f"Actual SHA256: {actual_clip_sha256}")
    print(f"Expected SHA256: {EXPECTED_CLIP_SHA256 if canonical_mode else '(not verified)'}")
    print(f"SHA256 match: {sha256_match}")
    print(f"Canonical mode: {canonical_mode}")

    if clip_path.stat().st_size > 0:
        import av as _av_mod
        try:
            _c = _av_mod.open(str(clip_path))
            _s = _c.streams.video[0]
            ctx = _s.codec_context
            print(f"Codec: {ctx.codec.name if ctx.codec else 'unknown'}")
            print(f"Resolution: {ctx.width}x{ctx.height}")
            print(f"FPS: {float(_s.average_rate) if _s.average_rate else 'unknown'}")
            _c.close()
        except Exception:
            pass

    env = _collect_environment()
    print(f"\nEnvironment: {env['python_version']}, {env['platform']}, PyAV {env.get('pyav_version')}")
    print(f"Evidence HEAD: {evidence_head}")
    print(f"Accepted base: {accepted_base}")

    # API capabilities
    from av.codec.context import CodecContext as _CC
    from av.codec.hwaccel import HWAccel as _HA
    caps = {
        "codec_context_is_hwaccel": "is_hwaccel" in dir(_CC),
        "hwaccel_allow_software_fallback": "allow_software_fallback" in dir(_HA),
        "hwaccel_config": "config" in dir(_HA),
    }

    print("\nRunning observation 01...")
    obs1 = run_single_observation(clip_path, sample_fps=2.0, observation_id="observation-01")

    print("\nRunning observation 02...")
    obs2 = run_single_observation(clip_path, sample_fps=2.0, observation_id="observation-02")

    print("\nStrict fallback control:")
    strict = run_strict_fallback_control(clip_path)

    obs_consistent = (
        obs1.get("requested_hw_device") == obs2.get("requested_hw_device")
        and obs1.get("codec_context_is_hwaccel") == obs2.get("codec_context_is_hwaccel")
        and obs1.get("codec_name") == obs2.get("codec_name")
    )

    evidence = {
        "schema_version": "2.0.0",
        "step": "18.4A",
        "evidence_type": "PYAV_HWACCEL_RUNTIME_STATE",
        "status": "OBSERVATION_COMPLETE" if ("error" not in obs1 and "error" not in obs2) else "OBSERVATION_INCOMPLETE",
        "branch": branch,
        "evidence_code_head": evidence_head,
        "evidence_code_tree": evidence_tree,
        "accepted_blocked_master_base": accepted_base,
        "clip": {
            "identifier": str(clip_path),
            "actual_sha256": actual_clip_sha256,
            "expected_sha256": EXPECTED_CLIP_SHA256,
            "sha256_match": sha256_match,
        },
        "effective_probe_config": {
            "sample_fps": 2.0,
            "independent_open_count": 2,
            "frames_consumed_per_open": 1,
            "canonical_mode": canonical_mode,
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
            "hwaccel_object_created": obs1.get("hwaccel_object_created"),
            "container_opened_with_hwaccel": obs1.get("container_opened_with_hwaccel"),
            "codec_context_is_hwaccel": obs1.get("codec_context_is_hwaccel"),
            "hw_config_present": obs1.get("hw_config_present"),
            "actual_hardware_decode_active": obs1.get("actual_hardware_decode_active"),
            "actual_hardware_decode_observation_method": obs1.get("actual_hardware_decode_observation_method"),
            "software_fallback_detected": obs1.get("software_fallback_detected"),
            "evidence_confidence": "HIGH" if obs_consistent else "LOW",
            "limitations": [],
        },
    }

    if args.output_dir:
        evidence["_output_dir"] = str(Path(args.output_dir).resolve())

    print("\n" + "=" * 60)
    print("RUNTIME EVIDENCE SUMMARY")
    print("=" * 60)
    print(json.dumps(evidence, indent=2, default=str))

    return evidence


if __name__ == "__main__":
    evidence = main()

    script_dir = Path(__file__).resolve().parent
    repo_dir = script_dir.parent

    shortsha = evidence.get("evidence_code_head", "unknown")[:7]
    output_dir = Path(
        evidence.get("_output_dir") or
        str(repo_dir / "benchmarks" / "detect" / "evidence" / f"hwaccel-runtime-{shortsha}")
    )
    evidence["_output_dir"] = str(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    (output_dir / "runtime_evidence.json").write_text(
        json.dumps(evidence, indent=2, default=str), encoding="utf-8"
    )
    (output_dir / "environment.json").write_text(
        json.dumps(evidence["environment"], indent=2), encoding="utf-8"
    )

    obs1 = evidence.get("observations", {}).get("observation-01", {})
    obs2 = evidence.get("observations", {}).get("observation-02", {})

    report_lines = [
        "# PyAV HWAccel Runtime Evidence Probe Report",
        "",
        f"**Step:** {evidence.get('step')}",
        f"**Evidence type:** {evidence.get('evidence_type')}",
        f"**Status:** {evidence.get('status')}",
        f"**Clip SHA256 match:** {evidence.get('clip', {}).get('sha256_match')}",
        "",
        "## Observation 01",
        f"- requested_hw_device: {obs1.get('requested_hw_device')}",
        f"- hwaccel_requested: {obs1.get('hwaccel_requested')}",
        f"- hwaccel_object_created: {obs1.get('hwaccel_object_created')}",
        f"- hwaccel_creation_error_type: {obs1.get('hwaccel_creation_error_type')}",
        f"- container_opened_with_hwaccel: {obs1.get('container_opened_with_hwaccel')}",
        f"- codec_context_is_hwaccel: {obs1.get('codec_context_is_hwaccel')}",
        f"- codec_context_hwaccel_present: {obs1.get('codec_context_hwaccel_present')}",
        f"- hw_config_present: {obs1.get('hw_config_present')}",
        f"- hw_config_device_type: {obs1.get('hw_config_device_type')}",
        f"- hw_config_format: {obs1.get('hw_config_format')}",
        f"- actual_hardware_decode_active: {obs1.get('actual_hardware_decode_active')}",
        f"- codec_name: {obs1.get('codec_name')}",
        f"- codec_long_name: {obs1.get('codec_long_name')}",
        f"- software_fallback_detected: {obs1.get('software_fallback_detected')}",
        f"- first_frame_shape: {obs1.get('first_frame_shape')}",
        "- generator explicitly closed: true",
        "",
        "## Observation 02",
        f"- requested_hw_device: {obs2.get('requested_hw_device')}",
        f"- hwaccel_requested: {obs2.get('hwaccel_requested')}",
        f"- hwaccel_object_created: {obs2.get('hwaccel_object_created')}",
        f"- hwaccel_creation_error_type: {obs2.get('hwaccel_creation_error_type')}",
        f"- container_opened_with_hwaccel: {obs2.get('container_opened_with_hwaccel')}",
        f"- codec_context_is_hwaccel: {obs2.get('codec_context_is_hwaccel')}",
        f"- codec_context_hwaccel_present: {obs2.get('codec_context_hwaccel_present')}",
        f"- hw_config_present: {obs2.get('hw_config_present')}",
        f"- hw_config_device_type: {obs2.get('hw_config_device_type')}",
        f"- hw_config_format: {obs2.get('hw_config_format')}",
        f"- actual_hardware_decode_active: {obs2.get('actual_hardware_decode_active')}",
        f"- codec_name: {obs2.get('codec_name')}",
        f"- codec_long_name: {obs2.get('codec_long_name')}",
        f"- software_fallback_detected: {obs2.get('software_fallback_detected')}",
        f"- first_frame_shape: {obs2.get('first_frame_shape')}",
        "- generator explicitly closed: true",
        "",
        "## Consistency",
        f"- Observations consistent: {evidence.get('observation_consistency')}",
        "",
        "## Strict Fallback Control",
        f"- supported: {evidence.get('strict_fallback_control', {}).get('supported')}",
        f"- attempted: {evidence.get('strict_fallback_control', {}).get('attempted')}",
        f"- result: {evidence.get('strict_fallback_control', {}).get('result')}",
        "",
        "## Conclusions",
        f"- Requested HW device: {evidence.get('conclusions', {}).get('requested_hw_device')}",
        f"- codec_context_is_hwaccel: {evidence.get('conclusions', {}).get('codec_context_is_hwaccel')}",
        f"- actual_hardware_decode_active: {evidence.get('conclusions', {}).get('actual_hardware_decode_active')}",
        f"- Fallback state: {evidence.get('conclusions', {}).get('software_fallback_detected')}",
        f"- Evidence confidence: {evidence.get('conclusions', {}).get('evidence_confidence')}",
    ]
    (output_dir / "probe_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"\nEvidence artifacts written to: {output_dir}")
