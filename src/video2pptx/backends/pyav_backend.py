# FILE: src/video2pptx/backends/pyav_backend.py
# VERSION: 0.3.0
# START_MODULE_CONTRACT
#   PURPOSE: PyAV/FFmpeg-based video decoder with CUDA NVDEC hardware acceleration
#   SCOPE: Decode video using PyAV with optional CUDA/D3D11VA/QSV hwaccel, yield frames at sample rate
#   DEPENDS: av, numpy, video2pptx.models
#   LINKS: M-BACKEND-PYAV
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   pyav_video_info - extract VideoInfo from video file via PyAV (software decode)
#   pyav_iter_frames - iterate frames using PyAV with hardware-accelerated decode
#   _hwaccel_evidence_observer - private optional observer for HWAccel runtime state
#   _register_hwaccel_evidence_observer - set observer (disabled by default)
# END_MODULE_MAP

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path

from loguru import logger

from video2pptx.detection_metrics import get as _get_metrics
from video2pptx.models import VideoFrame, VideoInfo

# START_BLOCK_HW_DEVICES
_HW_PREFERRED = ["cuda", "d3d12va", "d3d11va", "qsv", "dxva2"]
# END_BLOCK_HW_DEVICES

# START_BLOCK_EVIDENCE_OBSERVER
_hwaccel_evidence_observer: Callable[[dict], None] | None = None


def _register_hwaccel_evidence_observer(observer: Callable[[dict], None] | None) -> None:
    global _hwaccel_evidence_observer
    _hwaccel_evidence_observer = observer
# END_BLOCK_EVIDENCE_OBSERVER


def _build_hwaccel_evidence(
    *,
    video_path: str | Path,
    sample_fps: float,
    available_hw_devices: list[str],
    requested_hw_device: str | None,
    hwaccel_requested: bool,
    hwaccel_object_created: bool,
    hwaccel_creation_error: str | None,
    container_opened: bool,
    container_opened_with_hwaccel: bool,
    container_open_error: str | None,
    allow_software_fallback: bool | str,
    runtime_hwaccel_active: bool | str,
    runtime_hwaccel_observation_method: str,
    software_fallback_detected: bool | str,
    software_fallback_reason: str,
    codec_name: str | None,
    codec_long_name: str | None,
    hw_config_device_type: str | None,
    hw_config_format: str | None,
    hardware_decoder_or_device_identity: str | None,
    first_frame_yielded: bool,
    first_frame_timestamp: float | None,
    first_frame_shape: list[int] | None,
    observation_notes: str = "",
) -> dict:
    return {
        "schema_version": "1.0.0",
        "observation_id": "",
        "backend": "pyav",
        "pyav_version": "",
        "python_version": "",
        "platform": "",
        "video_identifier": str(video_path),
        "video_sha256": "",
        "sample_fps": sample_fps,
        "available_hw_devices": available_hw_devices,
        "requested_hw_device": requested_hw_device,
        "hwaccel_requested": hwaccel_requested,
        "hwaccel_object_created": hwaccel_object_created,
        "hwaccel_creation_error": hwaccel_creation_error,
        "container_opened": container_opened,
        "container_opened_with_hwaccel": container_opened_with_hwaccel,
        "container_open_error": container_open_error,
        "allow_software_fallback": allow_software_fallback,
        "runtime_hwaccel_active": runtime_hwaccel_active,
        "runtime_hwaccel_observation_method": runtime_hwaccel_observation_method,
        "software_fallback_detected": software_fallback_detected,
        "software_fallback_reason": software_fallback_reason,
        "codec_name": codec_name,
        "codec_long_name": codec_long_name,
        "hw_config_device_type": hw_config_device_type,
        "hw_config_format": hw_config_format,
        "hardware_decoder_or_device_identity": hardware_decoder_or_device_identity,
        "first_frame_yielded": first_frame_yielded,
        "first_frame_timestamp": first_frame_timestamp,
        "first_frame_shape": first_frame_shape,
        "observation_notes": observation_notes,
    }
# END_BLOCK_EVIDENCE_OBSERVER


# START_CONTRACT: _available_hw_devices
#   PURPOSE: List hardware acceleration devices available via PyAV
#   INPUTS: none
#   OUTPUTS: list[str] — device type names (e.g. ["cuda", "dxva2"])
#   SIDE_EFFECTS: none
#   LINKS: M-BACKEND-PYAV
# END_CONTRACT: _available_hw_devices
def _available_hw_devices() -> list[str]:
    from av.codec.hwaccel import hwdevices_available
    return [d for d in _HW_PREFERRED if d in hwdevices_available()]


# START_CONTRACT: _pick_hw_device
#   PURPOSE: Pick the best available hardware acceleration device
#   INPUTS: none
#   OUTPUTS: str | None — device type name or None if no HW available
#   SIDE_EFFECTS: logs selection
#   LINKS: M-BACKEND-PYAV
# END_CONTRACT: _pick_hw_device
def _pick_hw_device() -> str | None:
    available = _available_hw_devices()
    if not available:
        return None
    chosen = available[0]
    logger.info(f"[PyAV][_pick_hw_device] Selected HW device={chosen}")
    return chosen


# START_CONTRACT: _create_hwaccel
#   PURPOSE: Create a HWAccel object for the given device type
#   INPUTS: { device_type: str, device_id: int }
#   OUTPUTS: HWAccel object or None on failure
#   SIDE_EFFECTS: logs on failure
#   LINKS: M-BACKEND-PYAV
# END_CONTRACT: _create_hwaccel
def _create_hwaccel(device_type: str, device_id: int = 0):
    from av.codec.hwaccel import HWAccel
    try:
        return HWAccel(device_type, device_id)
    except Exception as e:
        logger.warning(f"[PyAV][_create_hwaccel] Failed device={device_type}: {e}")
        return None


# START_CONTRACT: pyav_video_info
#   PURPOSE: Extract VideoInfo from video file via PyAV (software decode, no HW needed)
#   INPUTS: { video_path: str|Path }
#   OUTPUTS: VideoInfo
#   SIDE_EFFECTS: opens and closes video file
#   LINKS: M-BACKEND-PYAV
# END_CONTRACT: pyav_video_info
def pyav_video_info(video_path: str | Path) -> VideoInfo:
    # START_BLOCK_OPEN_METADATA
    import av
    container = av.open(str(video_path))
    try:
        stream = container.streams.video[0]
        duration = float(stream.duration * stream.time_base) if stream.duration else 0.0
        if duration <= 0.0:
            duration = float(container.duration / av.time_base) if container.duration else -1.0

        codec = stream.codec_context
        return VideoInfo(
            path=str(video_path),
            duration=duration,
            width=codec.width,
            height=codec.height,
            fps=float(stream.average_rate),
        )
    finally:
        container.close()
    # END_BLOCK_OPEN_METADATA


# START_CONTRACT: pyav_iter_frames
#   PURPOSE: Iterate video frames at sample_fps using PyAV with hardware-accelerated decode
#   INPUTS: { video_path: str|Path, sample_fps: float, keyframes_only: bool }
#   OUTPUTS: Iterator[VideoFrame] — RGB uint8 arrays with timestamps
#   SIDE_EFFECTS: opens video file, decodes frames sequentially
#   LINKS: M-BACKEND-PYAV
# END_CONTRACT: pyav_iter_frames
def pyav_iter_frames(
    video_path: str | Path,
    sample_fps: float = 2.0,
    keyframes_only: bool = False,
) -> Iterator[VideoFrame]:
    # START_BLOCK_INIT
    import av

    hw_device = _pick_hw_device()
    hwaccel_requested = hw_device is not None
    hwaccel = _create_hwaccel(hw_device) if hw_device else None
    hwaccel_object_created = hwaccel is not None

    open_error = None
    container = None
    try:
        container = av.open(str(video_path), hwaccel=hwaccel)
    except Exception as e:
        open_error = str(e)
        raise
    # END_BLOCK_INIT

    # START_BLOCK_CALC_INTERVAL
    stream = container.streams.video[0]
    codec_ctx = stream.codec_context
    video_fps = float(stream.average_rate)
    if video_fps <= 0:
        video_fps = 30.0
    frame_interval = max(1, int(round(video_fps / sample_fps)))
    # END_BLOCK_CALC_INTERVAL

    # START_BLOCK_DECODE_LOOP
    current_frame_idx = 0
    first_frame_observed = False
    try:
        for packet in container.demux(stream):
            for frame in packet.decode():
                m = _get_metrics()
                if m is not None:
                    m.counter_frames_decoded.increment()

                if keyframes_only and not frame.key_frame:
                    current_frame_idx += 1
                    continue

                if keyframes_only or current_frame_idx % frame_interval == 0:
                    timestamp = current_frame_idx / video_fps
                    img = frame.to_ndarray(format="rgb24")
                    if m is not None:
                        m.counter_ndarray_conversions.increment()
                        m.gauge_rgb_transfer_bytes.value += img.nbytes

                    # START_BLOCK_EVIDENCE_CAPTURE
                    if not first_frame_observed and _hwaccel_evidence_observer is not None:
                        first_frame_observed = True
                        hwaccel_obj = codec_ctx.hwaccel
                        asf = (
                            hwaccel_obj.allow_software_fallback
                            if hwaccel_obj is not None else
                            "NOT_APPLICABLE"
                        )
                        cfg = hwaccel_obj.config if hwaccel_obj is not None else None

                        from av.codec.hwaccel import hwdevices_available as _hwdevices_available
                        evidence = _build_hwaccel_evidence(
                            video_path=video_path,
                            sample_fps=sample_fps,
                            available_hw_devices=[d for d in _HW_PREFERRED if d in _hwdevices_available()],
                            requested_hw_device=hw_device,
                            hwaccel_requested=hwaccel_requested,
                            hwaccel_object_created=hwaccel_object_created,
                            hwaccel_creation_error=None,
                            container_opened=container is not None,
                            container_opened_with_hwaccel=container is not None and hwaccel is not None,
                            container_open_error=open_error,
                            allow_software_fallback=asf,
                            runtime_hwaccel_active=codec_ctx.is_hwaccel,
                            runtime_hwaccel_observation_method="stream.codec_context.is_hwaccel",
                            software_fallback_detected="UNKNOWN_NOT_EXPOSED",
                            software_fallback_reason="",
                            codec_name=codec_ctx.codec.name if codec_ctx.codec else None,
                            codec_long_name=codec_ctx.codec.long_name if codec_ctx.codec else None,
                            hw_config_device_type=getattr(cfg, "device_type", None) if cfg else None,
                            hw_config_format=getattr(cfg, "format", None) if cfg else None,
                            hardware_decoder_or_device_identity=str(hwaccel_obj) if hwaccel_obj else None,
                            first_frame_yielded=True,
                            first_frame_timestamp=timestamp,
                            first_frame_shape=list(img.shape),
                        )
                        try:
                            _hwaccel_evidence_observer(evidence)
                        except Exception:
                            pass
                    # END_BLOCK_EVIDENCE_CAPTURE

                    yield VideoFrame(timestamp=timestamp, image=img)
                current_frame_idx += 1
    finally:
        container.close()
    # END_BLOCK_DECODE_LOOP
