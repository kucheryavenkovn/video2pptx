#!/usr/bin/env python3
# FILE: tools/probe_pyav_hwaccel.py
# VERSION: 3.0.0
# START_MODULE_CONTRACT
#   PURPOSE: HWAccel runtime state probe for the production pyav_iter_frames path,
#            plus a corrected strict no-software-fallback supporting control.
#   SCOPE:
#     - full probe: two independent production-path opens + strict control (default)
#     - strict-control-only: run ONLY the corrected strict no-software-fallback control
#       on the exact canonical Hermes H.264 clip (does NOT rerun production observations)
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
    _register_hwaccel_evidence_observer,
)

CANONICAL_FILENAME = "hermes-0000-1000.mp4"
EXPECTED_CLIP_SHA256 = "dd9da3442e91ab7f17f0405198aa8e39d1538d74518b6b9a3b1e61ac2fc0f5a4"

# Immutable reference to the accepted canonical production-path raw evidence.
CANONICAL_RUNTIME_EVIDENCE_COMMIT = "9b4cc54949537b2a36e70a0f98f1cb732d6688b2"
CANONICAL_RUNTIME_EVIDENCE_PATH = (
    "benchmarks/detect/evidence/hwaccel-runtime-hermes-h264-20260714/runtime_evidence.json"
)

# Terminal states for the corrected strict no-software-fallback control.
FIRST_FRAME_DECODED = "FIRST_FRAME_DECODED"
EOF_NO_FRAME = "EOF_NO_FRAME"
PACKET_LIMIT_REACHED_NO_FRAME = "PACKET_LIMIT_REACHED_NO_FRAME"
SETUP_EXCEPTION = "SETUP_EXCEPTION"
CONTAINER_OPEN_EXCEPTION = "CONTAINER_OPEN_EXCEPTION"
DECODE_EXCEPTION = "DECODE_EXCEPTION"
FRAME_CONVERSION_EXCEPTION = "FRAME_CONVERSION_EXCEPTION"


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


def _validate_accepted_base(accepted_base: str, repo: Path) -> None:
    """Validate accepted base is a real 40-hex commit and an ancestor of HEAD.

    Raises ValueError with a precise reason otherwise. Centralised so both the
    full probe and the strict-control-only mode share identical provenance checks.
    """
    is_valid, obj_type = _resolve_git_object(accepted_base, repo)
    if not is_valid:
        raise ValueError(f"accepted base not a valid git object: {obj_type}")
    if obj_type != "commit":
        raise ValueError(f"accepted base is {obj_type}, expected commit")
    try:
        subprocess.check_call(
            ["git", "merge-base", "--is-ancestor", accepted_base, "HEAD"],
            cwd=repo, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        raise ValueError(f"accepted base {accepted_base} is NOT an ancestor of HEAD") from None


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


# START_CONTRACT: run_strict_fallback_control
#   PURPOSE: Corrected strict no-software-fallback supporting control.
#            Demux/decode until ONE deterministic terminal state is reached.
#   INPUTS: { clip_path: Path, requested_hw_device: str, packet_limit: int|None,
#             _av: module|None (test injection), _hwaccel_cls: type|None (test injection) }
#   OUTPUTS: { dict — control result with explicit terminal state, packet/frame counts,
#              codec, errors, and explicit container-close accounting }
#   SIDE_EFFECTS: opens and explicitly closes a PyAV container with HWAccel(cuda, fallback=False)
#   TERMINAL_STATES: FIRST_FRAME_DECODED | EOF_NO_FRAME | PACKET_LIMIT_REACHED_NO_FRAME |
#                    SETUP_EXCEPTION | CONTAINER_OPEN_EXCEPTION | DECODE_EXCEPTION |
#                    FRAME_CONVERSION_EXCEPTION
#   NOTE: Does NOT stop merely because one packet yielded zero frames. Does NOT invoke the
#         production observer or run_single_observation. Supporting evidence only.
#   LINKS: M-BACKEND-PYAV, V-PERF-DETECT-BOTTLENECK
# END_CONTRACT: run_strict_fallback_control
def run_strict_fallback_control(
    clip_path,
    *,
    requested_hw_device: str = "cuda",
    packet_limit: int | None = None,
    _av=None,
    _hwaccel_cls=None,
) -> dict:
    result = {
        "schema_version": "1.0.0",
        "control_name": "STRICT_NO_SOFTWARE_FALLBACK",
        "control_purpose": "supporting discriminator only",
        "primary_evidence": False,
        "requested_hw_device": requested_hw_device,
        "allow_software_fallback": False,
        "result": None,
        "result_stage": None,
        "packets_examined": 0,
        "packets_with_decoded_frames": 0,
        "frames_decoded": 0,
        "frames_converted": 0,
        "first_frame_timestamp": None,
        "first_frame_shape": None,
        "codec_name": None,
        "codec_long_name": None,
        "error_type": None,
        "error_message": None,
        "container_opened": False,
        "container_closed": False,
        "container_close_error_type": None,
        "container_close_error_message": None,
        "observation_notes": "",
    }

    if _av is None:
        import av as _av
    if _hwaccel_cls is None:
        from av.codec.hwaccel import HWAccel as _hwaccel_cls

    # Stage: HWAccel setup / configuration.
    try:
        hw = _hwaccel_cls(requested_hw_device, 0)
        hw.allow_software_fallback = False
    except Exception as e:
        result["result"] = SETUP_EXCEPTION
        result["result_stage"] = "hwaccel_setup"
        result["error_type"] = type(e).__name__
        result["error_message"] = str(e)
        return result

    # Stage: container open.
    container = None
    try:
        container = _av.open(str(clip_path), hwaccel=hw)
        result["container_opened"] = True
    except Exception as e:
        result["result"] = CONTAINER_OPEN_EXCEPTION
        result["result_stage"] = "container_open"
        result["error_type"] = type(e).__name__
        result["error_message"] = str(e)
        return result

    try:
        # Stage: stream selection (setup-stage).
        try:
            stream = container.streams.video[0]
            codec_ctx = stream.codec_context
            result["codec_name"] = codec_ctx.codec.name if codec_ctx.codec else None
            result["codec_long_name"] = (
                codec_ctx.codec.long_name if codec_ctx.codec else None
            )
        except Exception as e:
            result["result"] = SETUP_EXCEPTION
            result["result_stage"] = "stream_selection"
            result["error_type"] = type(e).__name__
            result["error_message"] = str(e)
            return result

        # Stage: bounded demux/decode loop. Continue past packets that yield no frame.
        try:
            for packet in container.demux(stream):
                result["packets_examined"] += 1

                try:
                    decoded = list(packet.decode())
                except Exception as e:
                    result["result"] = DECODE_EXCEPTION
                    result["result_stage"] = "decode"
                    result["error_type"] = type(e).__name__
                    result["error_message"] = str(e)
                    return result

                if decoded:
                    result["packets_with_decoded_frames"] += 1

                for frame in decoded:
                    result["frames_decoded"] += 1
                    try:
                        arr = frame.to_ndarray(format="rgb24")
                    except Exception as e:
                        result["result"] = FRAME_CONVERSION_EXCEPTION
                        result["result_stage"] = "frame_conversion"
                        result["error_type"] = type(e).__name__
                        result["error_message"] = str(e)
                        return result
                    result["frames_converted"] += 1
                    result["first_frame_timestamp"] = getattr(frame, "time", None)
                    try:
                        result["first_frame_shape"] = list(arr.shape)
                    except Exception:
                        result["first_frame_shape"] = None
                    result["result"] = FIRST_FRAME_DECODED
                    result["result_stage"] = "first_frame_decoded"
                    return result

                if packet_limit is not None and result["packets_examined"] >= packet_limit:
                    result["result"] = PACKET_LIMIT_REACHED_NO_FRAME
                    result["result_stage"] = "packet_limit"
                    result["observation_notes"] = (
                        f"packet_limit={packet_limit} reached without a decoded frame"
                    )
                    return result
        except Exception as e:
            # demux iteration itself raised (distinct from packet.decode()).
            result["result"] = DECODE_EXCEPTION
            result["result_stage"] = "demux"
            result["error_type"] = type(e).__name__
            result["error_message"] = str(e)
            return result

        # Demux exhausted with no decoded frame.
        result["result"] = EOF_NO_FRAME
        result["result_stage"] = "eof"
        return result
    finally:
        # Deterministic cleanup: close container whenever it was opened.
        # A close error is recorded separately and MUST NOT overwrite the primary result.
        if container is not None:
            try:
                container.close()
                result["container_closed"] = True
            except Exception as e:
                result["container_closed"] = False
                result["container_close_error_type"] = type(e).__name__
                result["container_close_error_message"] = str(e)


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


def _probe_clip_metadata(clip_path: Path) -> dict:
    """Read codec/resolution via a lightweight software av.open (metadata only)."""
    meta = {"codec_name": None, "codec_long_name": None, "width": None, "height": None}
    try:
        import av
        c = av.open(str(clip_path))
        try:
            s = c.streams.video[0]
            cc = s.codec_context
            meta["codec_name"] = cc.codec.name if cc.codec else None
            meta["codec_long_name"] = cc.codec.long_name if cc.codec else None
            meta["width"] = cc.width
            meta["height"] = cc.height
        finally:
            c.close()
    except Exception:
        pass
    return meta


def _interpret_strict_result(result: str) -> tuple[str, str]:
    """Return (interpretation, runtime_interpretation_confidence) for a strict result."""
    if result == FIRST_FRAME_DECODED:
        return (
            "With HWAccel('cuda', 0) and allow_software_fallback=false, the canonical H.264 "
            "stream produced at least one decoded and RGB-converted frame. This directly supports "
            "that a strict no-software-fallback CUDA-configured decode path is operational in this "
            "PyAV/FFmpeg/runtime environment. Supporting evidence only: does NOT prove every "
            "production benchmark frame used hardware decode, does NOT prove the production "
            "fallback-enabled path never used software fallback, and does NOT measure throughput.",
            "HIGH",
        )
    if result in (DECODE_EXCEPTION, FRAME_CONVERSION_EXCEPTION, CONTAINER_OPEN_EXCEPTION, SETUP_EXCEPTION):
        return (
            f"Strict no-software-fallback control terminated with {result}. The exact exception is "
            "captured. This is direct evidence of the failure mechanism; it is NOT automatically a "
            "confirmed software fallback unless the exception semantics directly establish that.",
            "HIGH",
        )
    if result == EOF_NO_FRAME:
        return (
            "Strict control reached EOF without any decoded frame. This is anomalous for the canonical "
            "H.264 video; it does NOT by itself infer software fallback.",
            "LOW",
        )
    if result == PACKET_LIMIT_REACHED_NO_FRAME:
        return (
            "Strict control hit the defensive packet limit without a decoded frame. This is an "
            "incomplete experiment and cannot select an optimization.",
            "LOW",
        )
    return ("Strict control did not reach a recognised terminal state.", "LOW")


def build_strict_control_evidence(
    clip_path: Path,
    *,
    actual_sha256: str,
    sha256_match: bool,
    canonical_mode: bool,
    evidence_head: str,
    evidence_tree: str,
    accepted_master_base: str,
    branch: str,
    env: dict,
    packet_limit: int | None = None,
) -> dict:
    """Run ONLY the corrected strict no-software-fallback control and assemble its evidence object.

    Validates canonical SHA in canonical mode (raises ValueError on mismatch). Does NOT invoke
    run_single_observation() or the production HWAccel observer.
    """
    if canonical_mode and not sha256_match:
        raise ValueError(
            f"canonical mode requires clip SHA256 = {EXPECTED_CLIP_SHA256} "
            f"(actual: {actual_sha256})"
        )

    meta = _probe_clip_metadata(clip_path)
    control = run_strict_fallback_control(clip_path, packet_limit=packet_limit)

    # Assemble the full step-13-compliant control object (core result + clip + provenance).
    control_object = dict(control)
    control_object.update(
        {
            "clip_identifier": str(clip_path),
            "clip_actual_sha256": actual_sha256,
            "clip_expected_sha256": EXPECTED_CLIP_SHA256,
            "clip_sha256_match": sha256_match,
            "evidence_code_head": evidence_head,
            "evidence_code_tree": evidence_tree,
            "accepted_master_base": accepted_master_base,
        }
    )

    deterministic_terminals = {
        FIRST_FRAME_DECODED, EOF_NO_FRAME, PACKET_LIMIT_REACHED_NO_FRAME,
        SETUP_EXCEPTION, CONTAINER_OPEN_EXCEPTION, DECODE_EXCEPTION,
        FRAME_CONVERSION_EXCEPTION,
    }
    reached_deterministic = control["result"] in deterministic_terminals
    interpretation, runtime_conf = _interpret_strict_result(control["result"])

    limitations = [
        "Supporting control only; not primary evidence.",
        "Probes only the first decoded frame; does not prove full-stream hardware decodability.",
        "Does not measure decode throughput or infer any speedup.",
        "A successful first frame does not prove the production fallback-enabled path never used software fallback.",
    ]

    return {
        "schema_version": "1.0.0",
        "step": "18.4B",
        "evidence_type": "PYAV_STRICT_NO_SOFTWARE_FALLBACK_CONTROL",
        "status": "OBSERVATION_COMPLETE" if reached_deterministic else "OBSERVATION_INCOMPLETE",
        "mode": "strict_only",
        "branch": branch,
        "evidence_code_head": evidence_head,
        "evidence_code_tree": evidence_tree,
        "accepted_master_base": accepted_master_base,
        "canonical_runtime_evidence_commit": CANONICAL_RUNTIME_EVIDENCE_COMMIT,
        "canonical_runtime_evidence_path": CANONICAL_RUNTIME_EVIDENCE_PATH,
        "production_observations_rerun": False,
        "clip": {
            "identifier": str(clip_path),
            "actual_sha256": actual_sha256,
            "expected_sha256": EXPECTED_CLIP_SHA256,
            "sha256_match": sha256_match,
            "codec_name": meta["codec_name"],
            "codec_long_name": meta["codec_long_name"],
            "width": meta["width"],
            "height": meta["height"],
        },
        "control": control_object,
        "interpretation": interpretation,
        "limitations": limitations,
        "strict_control_execution_completeness_confidence": "HIGH" if reached_deterministic else "LOW",
        "strict_control_runtime_interpretation_confidence": runtime_conf,
    }


def main():
    parser = argparse.ArgumentParser(description="PyAV HWAccel Runtime Evidence Probe")
    parser.add_argument("--video-path", default=None,
                        help="Video path. Without --canonical-mode, SHA256 not verified.")
    parser.add_argument("--canonical-mode", action="store_true",
                        help="Require exact canonical clip SHA256")
    parser.add_argument("--accepted-base", default="f52e82c55744de077984db3b9bcb2162d4f9d87f",
                        help="Accepted master base SHA (must be a commit ancestor of HEAD)")
    parser.add_argument("--strict-control-only", action="store_true",
                        help="Run ONLY the corrected strict no-software-fallback control; "
                             "do NOT rerun production-path observations.")
    parser.add_argument("--packet-limit", type=int, default=None,
                        help="Optional defensive packet ceiling for the strict control "
                             "(default: no limit).")
    parser.add_argument("--output-dir", default=None,
                        help="Evidence output directory (default: auto)")
    args = parser.parse_args()

    repo_dir = Path(__file__).resolve().parent.parent

    # Shared provenance validation (raises ValueError on invalid base).
    try:
        _validate_accepted_base(args.accepted_base, repo_dir)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    print(f"Accepted base {args.accepted_base} is a commit ancestor of HEAD")

    accepted_base = args.accepted_base
    evidence_head = _git(["rev-parse", "HEAD"], repo_dir)
    evidence_tree = _git(["rev-parse", "HEAD^{tree}"], repo_dir)
    branch = _git(["branch", "--show-current"], repo_dir)

    # Resolve clip.
    canonical_mode = args.canonical_mode
    if args.video_path:
        clip_path = Path(args.video_path).resolve()
        if not clip_path.exists():
            print(f"ERROR: clip not found: {clip_path}", file=sys.stderr)
            sys.exit(1)
    else:
        clip_path = repo_dir / "examples" / CANONICAL_FILENAME

    actual_clip_sha256 = hashlib.sha256(clip_path.read_bytes()).hexdigest()
    sha256_match = actual_clip_sha256 == EXPECTED_CLIP_SHA256

    if canonical_mode and not sha256_match:
        print(f"ERROR: canonical mode requires clip SHA256 = {EXPECTED_CLIP_SHA256}", file=sys.stderr)
        print(f"  Actual: {actual_clip_sha256}", file=sys.stderr)
        sys.exit(1)

    env = _collect_environment()

    print("=" * 60)
    print("PyAV HWAccel Runtime Evidence Probe")
    print("=" * 60)
    print(f"Mode: {'strict-control-only' if args.strict_control_only else 'full'}")
    print(f"Clip: {clip_path}")
    print(f"Actual SHA256: {actual_clip_sha256}")
    print(f"Expected SHA256: {EXPECTED_CLIP_SHA256 if canonical_mode else '(not verified)'}")
    print(f"SHA256 match: {sha256_match}")
    print(f"Canonical mode: {canonical_mode}")
    print(f"Evidence HEAD: {evidence_head}")
    print(f"Accepted base: {accepted_base}")

    if args.strict_control_only:
        evidence = build_strict_control_evidence(
            clip_path,
            actual_sha256=actual_clip_sha256,
            sha256_match=sha256_match,
            canonical_mode=canonical_mode,
            evidence_head=evidence_head,
            evidence_tree=evidence_tree,
            accepted_master_base=accepted_base,
            branch=branch,
            env=env,
            packet_limit=args.packet_limit,
        )
        evidence["environment"] = env
        if args.output_dir:
            evidence["_output_dir"] = str(Path(args.output_dir).resolve())

        print("\n" + "=" * 60)
        print("STRICT CONTROL EVIDENCE SUMMARY")
        print("=" * 60)
        print(json.dumps({k: v for k, v in evidence.items() if k != "environment"}, indent=2, default=str))
        return evidence

    # ---- full probe (unchanged behavior, corrected strict control) ----
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

    print(f"\nEnvironment: {env['python_version']}, {env['platform']}, PyAV {env.get('pyav_version')}")

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


def _write_full_artifacts(evidence: dict, output_dir: Path) -> None:
    (output_dir / "runtime_evidence.json").write_text(
        json.dumps(evidence, indent=2, default=str), encoding="utf-8"
    )
    (output_dir / "environment.json").write_text(
        json.dumps(evidence["environment"], indent=2), encoding="utf-8"
    )
    obs1 = evidence.get("observations", {}).get("observation-01", {})
    obs2 = evidence.get("observations", {}).get("observation-02", {})
    strict = evidence.get("strict_fallback_control", {})
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
        "## Strict Fallback Control (corrected)",
        f"- result: {strict.get('result')}",
        f"- result_stage: {strict.get('result_stage')}",
        f"- packets_examined: {strict.get('packets_examined')}",
        f"- frames_decoded: {strict.get('frames_decoded')}",
        f"- frames_converted: {strict.get('frames_converted')}",
        f"- container_opened: {strict.get('container_opened')}",
        f"- container_closed: {strict.get('container_closed')}",
        f"- error_type: {strict.get('error_type')}",
        "",
        "## Conclusions",
        f"- Requested HW device: {evidence.get('conclusions', {}).get('requested_hw_device')}",
        f"- codec_context_is_hwaccel: {evidence.get('conclusions', {}).get('codec_context_is_hwaccel')}",
        f"- actual_hardware_decode_active: {evidence.get('conclusions', {}).get('actual_hardware_decode_active')}",
        f"- Fallback state: {evidence.get('conclusions', {}).get('software_fallback_detected')}",
        f"- Evidence confidence: {evidence.get('conclusions', {}).get('evidence_confidence')}",
    ]
    (output_dir / "probe_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")


def _write_strict_artifacts(evidence: dict, output_dir: Path) -> None:
    (output_dir / "strict_control_evidence.json").write_text(
        json.dumps(evidence, indent=2, default=str), encoding="utf-8"
    )
    (output_dir / "environment.json").write_text(
        json.dumps(evidence.get("environment", {}), indent=2), encoding="utf-8"
    )
    control = evidence.get("control", {})
    report_lines = [
        "# PyAV Strict No-Software-Fallback Control Report (Step 18.4B)",
        "",
        f"**Step:** {evidence.get('step')}",
        f"**Evidence type:** {evidence.get('evidence_type')}",
        f"**Status:** {evidence.get('status')}",
        f"**Mode:** {evidence.get('mode')}",
        f"**Clip SHA256 match:** {evidence.get('clip', {}).get('sha256_match')}",
        f"**Canonical runtime evidence commit:** {evidence.get('canonical_runtime_evidence_commit')}",
        "",
        "## Corrected Strict Control",
        f"- control_name: {control.get('control_name')}",
        f"- primary_evidence: {control.get('primary_evidence')}",
        f"- requested_hw_device: {control.get('requested_hw_device')}",
        f"- allow_software_fallback: {control.get('allow_software_fallback')}",
        f"- result: {control.get('result')}",
        f"- result_stage: {control.get('result_stage')}",
        f"- packets_examined: {control.get('packets_examined')}",
        f"- packets_with_decoded_frames: {control.get('packets_with_decoded_frames')}",
        f"- frames_decoded: {control.get('frames_decoded')}",
        f"- frames_converted: {control.get('frames_converted')}",
        f"- first_frame_timestamp: {control.get('first_frame_timestamp')}",
        f"- first_frame_shape: {control.get('first_frame_shape')}",
        f"- codec_name: {control.get('codec_name')}",
        f"- codec_long_name: {control.get('codec_long_name')}",
        f"- container_opened: {control.get('container_opened')}",
        f"- container_closed: {control.get('container_closed')}",
        f"- error_type: {control.get('error_type')}",
        f"- error_message: {control.get('error_message')}",
        f"- evidence_code_head: {control.get('evidence_code_head')}",
        f"- evidence_code_tree: {control.get('evidence_code_tree')}",
        f"- accepted_master_base: {control.get('accepted_master_base')}",
        "",
        "## Interpretation",
        evidence.get("interpretation", ""),
        "",
        "## Confidence dimensions",
        f"- strict_control_execution_completeness_confidence: {evidence.get('strict_control_execution_completeness_confidence')}",
        f"- strict_control_runtime_interpretation_confidence: {evidence.get('strict_control_runtime_interpretation_confidence')}",
        "",
        "## Limitations",
        *[f"- {lim}" for lim in evidence.get("limitations", [])],
    ]
    (output_dir / "strict_control_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")


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

    if evidence.get("mode") == "strict_only":
        _write_strict_artifacts(evidence, output_dir)
    else:
        _write_full_artifacts(evidence, output_dir)

    print(f"\nEvidence artifacts written to: {output_dir}")
