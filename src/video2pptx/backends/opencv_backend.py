# FILE: src/video2pptx/backends/opencv_backend.py
# VERSION: 0.1.1
# START_MODULE_CONTRACT
#   PURPOSE: OpenCV-based video decoder (CPU fallback)
#   SCOPE: Decode video and yield frames at requested sample rate via cv2.VideoCapture
#   DEPENDS: opencv-python, numpy, video2pptx.models
#   LINKS: M-BACKEND-OPENCV
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   opencv_iter_frames - OpenCV frame iterator, yields VideoFrame at sample_fps
#   opencv_video_info - extract VideoInfo from cv2.VideoCapture
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v0.1.1 - Count each successful VideoCapture read exactly once
# END_CHANGE_SUMMARY

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

import cv2
from loguru import logger

from video2pptx.detection_metrics import get as _get_metrics
from video2pptx.models import VideoFrame, VideoInfo


def _win_short_path(path: str | Path) -> str:
    """Convert a Unicode path to Windows 8.3 short path for OpenCV compatibility."""
    p = str(path)
    if sys.platform != "win32":
        return p
    try:
        import ctypes

        buf = ctypes.create_unicode_buffer(260)
        n = ctypes.windll.kernel32.GetShortPathNameW(p, buf, 260)
        if n > 0:
            return buf.value
    except Exception:
        pass
    return p


def opencv_video_info(video_path: str | Path) -> VideoInfo:
    # START_CONTRACT: opencv_video_info
    #   PURPOSE: Extract VideoInfo from video file via OpenCV
    #   INPUTS: { video_path: str|Path }
    #   OUTPUTS: { VideoInfo }
    #   SIDE_EFFECTS: opens and releases video file
    #   LINKS: M-BACKEND-OPENCV
    # END_CONTRACT: opencv_video_info

    # START_BLOCK_OPEN_VIDEO
    cap = cv2.VideoCapture(_win_short_path(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")
    # END_BLOCK_OPEN_VIDEO

    # START_BLOCK_EXTRACT_METADATA
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if fps > 0 and total_frames > 0:
        duration = total_frames / fps
    else:
        duration = -1.0
    # END_BLOCK_EXTRACT_METADATA

    cap.release()

    return VideoInfo(
        path=str(video_path),
        duration=duration,
        width=width,
        height=height,
        fps=fps,
    )


def opencv_iter_frames(
    video_path: str | Path,
    sample_fps: float = 2.0,
    keyframes_only: bool = False,
) -> Iterator[VideoFrame]:
    # START_CONTRACT: opencv_iter_frames
    #   PURPOSE: Iterate video frames at given sample rate using OpenCV
    #   INPUTS: { video_path: str|Path, sample_fps: float, keyframes_only: bool }
    #   OUTPUTS: Iterator[VideoFrame] — yields frames with timestamps
    #   SIDE_EFFECTS: opens video file, reads frames sequentially
    #   LINKS: M-BACKEND-OPENCV
    # END_CONTRACT: opencv_iter_frames

    # START_BLOCK_OPEN_VIDEO_ITER
    cap = cv2.VideoCapture(_win_short_path(video_path))
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")
    # END_BLOCK_OPEN_VIDEO_ITER

    # START_BLOCK_CALC_SAMPLE_INTERVAL
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    if video_fps <= 0:
        video_fps = 30.0

    if keyframes_only:
        logger.info(
            "[OpenCV][iter_frames] keyframes_only requested — falling back to normal sampling (OpenCV has no keyframe API)"
        )

    frame_interval = max(1, int(round(video_fps / sample_fps)))
    current_frame_idx = 0
    # END_BLOCK_CALC_SAMPLE_INTERVAL

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            m = _get_metrics()
            if m is not None:
                m.counter_frames_decoded.increment()

            if current_frame_idx % frame_interval == 0:
                timestamp = current_frame_idx / video_fps
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                if m is not None:
                    m.counter_ndarray_conversions.increment()
                    m.gauge_rgb_transfer_bytes.value += frame_rgb.nbytes
                yield VideoFrame(timestamp=timestamp, image=frame_rgb)

            current_frame_idx += 1
    finally:
        cap.release()
