# FILE: src/video2pptx/backends/__init__.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Barrel for video decoder backends, backend auto-selection
#   SCOPE: Re-exports available backends, provides auto-selection logic
#   DEPENDS: opencv_backend, loguru
#   LINKS: M-BACKENDS
#   ROLE: BARREL
#   MAP_MODE: SUMMARY
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   iter_frames - auto-select backend and iterate frames at sample_fps
#   video_info - auto-select backend and return VideoInfo
#   BACKENDS - dict of available backend name → info
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterator

from loguru import logger

from video2pptx.backends.opencv_backend import opencv_iter_frames, opencv_video_info
from video2pptx.models import VideoFrame, VideoInfo

# START_BLOCK_BACKEND_REGISTRY
BACKENDS: dict[str, dict[str, Any]] = {
    "opencv": {
        "available": True,
        "iter_frames": opencv_iter_frames,
        "video_info": opencv_video_info,
    },
    "pyav": {
        "available": False,
        "iter_frames": None,
        "video_info": None,
    },
    "decord": {
        "available": False,
        "iter_frames": None,
        "video_info": None,
    },
    "pynv": {
        "available": False,
        "iter_frames": None,
        "video_info": None,
    },
}
# END_BLOCK_BACKEND_REGISTRY

# START_BLOCK_AUTO_ORDER
_AUTO_ORDER = ["pynv", "decord", "pyav", "opencv"]
# END_BLOCK_AUTO_ORDER

# START_BLOCK_DETECT_PYAV
try:
    import av  # noqa: F401
    from video2pptx.backends.pyav_backend import pyav_iter_frames, pyav_video_info
    BACKENDS["pyav"] = {
        "available": True,
        "iter_frames": pyav_iter_frames,
        "video_info": pyav_video_info,
    }
    logger.debug("[Backends] PyAV backend detected and registered")
except ImportError:
    logger.debug("[Backends] PyAV not installed, using OpenCV fallback")
# END_BLOCK_DETECT_PYAV


def _resolve_backend(name: str) -> tuple[str, dict[str, Any]]:
    # START_CONTRACT: _resolve_backend
    #   PURPOSE: Resolve backend name to actual available backend
    #   INPUTS: { name: str - "auto", "opencv", "pyav", "decord", "pynv" }
    #   OUTPUTS: (backend_name: str, backend_info: dict)
    #   SIDE_EFFECTS: logs warnings on fallback
    #   LINKS: M-BACKENDS
    # END_CONTRACT: _resolve_backend

    # START_BLOCK_RESOLVE
    if name == "auto":
        for candidate in _AUTO_ORDER:
            info = BACKENDS.get(candidate)
            if info and info["available"]:
                logger.debug(f"[Backends][_resolve_backend] Selected backend={candidate}")
                return candidate, info
        logger.warning("[Backends][_resolve_backend][BLOCK_FALLBACK_CPU] No GPU backend available, using OpenCV")
        return "opencv", BACKENDS["opencv"]

    if name not in BACKENDS:
        logger.warning(f"[Backends][_resolve_backend] Unknown backend={name}, falling back to OpenCV")
        return "opencv", BACKENDS["opencv"]

    info = BACKENDS[name]
    if not info["available"]:
        logger.warning(f"[Backends][_resolve_backend] Backend={name} not available, falling back")
        return _resolve_backend("auto")

    return name, info
    # END_BLOCK_RESOLVE


def detect_best_backend() -> str:
    # START_CONTRACT: detect_best_backend
    #   PURPOSE: Return the name of the best available decoder backend by priority
    #   INPUTS: none — reads BACKENDS registry
    #   OUTPUTS: str — e.g. "pynv", "decord", "pyav", "opencv"
    #   SIDE_EFFECTS: none
    #   LINKS: M-BACKENDS
    # END_CONTRACT: detect_best_backend

    for candidate in _AUTO_ORDER:
        info = BACKENDS.get(candidate)
        if info and info["available"]:
            logger.debug(f"[Backends][detect_best_backend] Best={candidate}")
            return candidate
    logger.debug("[Backends][detect_best_backend] No GPU backend, falling back to opencv")
    return "opencv"


def iter_frames(video_path: str | Path, sample_fps: float = 2.0, backend: str = "auto", keyframes_only: bool = False) -> Iterator[VideoFrame]:
    # START_CONTRACT: iter_frames
    #   PURPOSE: Auto-select backend and iterate video frames at sample_fps
    #   INPUTS: { video_path, sample_fps, backend, keyframes_only }
    #   OUTPUTS: Iterator[VideoFrame]
    #   SIDE_EFFECTS: opens video, reads frames
    #   LINKS: M-BACKENDS
    # END_CONTRACT: iter_frames

    name, info = _resolve_backend(backend)
    logger.info(f"[Backends][iter_frames] backend={name} path={video_path} sample_fps={sample_fps} keyframes_only={keyframes_only}")
    yield from info["iter_frames"](video_path, sample_fps, keyframes_only)


def video_info(video_path: str | Path, backend: str = "auto") -> VideoInfo:
    # START_CONTRACT: video_info
    #   PURPOSE: Auto-select backend and return VideoInfo
    #   INPUTS: { video_path, backend }
    #   OUTPUTS: VideoInfo
    #   SIDE_EFFECTS: opens video briefly to read metadata
    #   LINKS: M-BACKENDS
    # END_CONTRACT: video_info

    name, info = _resolve_backend(backend)
    logger.info(f"[Backends][video_info] backend={name} path={video_path}")
    return info["video_info"](video_path)
