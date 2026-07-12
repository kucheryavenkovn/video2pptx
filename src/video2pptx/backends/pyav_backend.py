# FILE: src/video2pptx/backends/pyav_backend.py
# VERSION: 0.2.0
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
# END_MODULE_MAP

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from loguru import logger

from video2pptx.detection_metrics import get as _get_metrics
from video2pptx.models import VideoFrame, VideoInfo

# START_BLOCK_HW_DEVICES
_HW_PREFERRED = ["cuda", "d3d12va", "d3d11va", "qsv", "dxva2"]
# END_BLOCK_HW_DEVICES


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
    hwaccel = _create_hwaccel(hw_device) if hw_device else None

    container = av.open(str(video_path), hwaccel=hwaccel)
    # END_BLOCK_INIT

    # START_BLOCK_CALC_INTERVAL
    stream = container.streams.video[0]
    video_fps = float(stream.average_rate)
    if video_fps <= 0:
        video_fps = 30.0
    frame_interval = max(1, int(round(video_fps / sample_fps)))
    # END_BLOCK_CALC_INTERVAL

    # START_BLOCK_DECODE_LOOP
    current_frame_idx = 0
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
                    yield VideoFrame(timestamp=timestamp, image=img)
                current_frame_idx += 1
    finally:
        container.close()
    # END_BLOCK_DECODE_LOOP
