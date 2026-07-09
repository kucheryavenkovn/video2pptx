# FILE: src/video2pptx/video_decode.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Unified video decoder — backend selection, frame sampling, metadata
#   SCOPE: VideoDecoder class that wraps backend selection, provides iter_frames and video_info
#   DEPENDS: backends, models, loguru
#   LINKS: M-VIDEO-DECODE
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   VideoDecoder - unified interface: iter_frames(), get_info()
#   select_backend - resolve backend name to actual backend
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path
from typing import Iterator

from loguru import logger

from video2pptx.backends import _resolve_backend
from video2pptx.models import VideoFrame, VideoInfo


def select_backend(backend_name: str = "auto") -> str:
    # START_CONTRACT: select_backend
    #   PURPOSE: Resolve backend name to available backend, returns backend name
    #   INPUTS: { backend_name: str }
    #   OUTPUTS: str — resolved backend name
    #   SIDE_EFFECTS: logs warning on fallback
    #   LINKS: M-VIDEO-DECODE
    # END_CONTRACT: select_backend

    # START_BLOCK_SELECT_BACKEND
    name, _ = _resolve_backend(backend_name)
    logger.info(f"[VideoDecode][select_backend] Backend selected | backend={name} requested={backend_name}")
    if name != backend_name and backend_name != "auto":
        logger.warning(f"[VideoDecode][select_backend][BLOCK_FALLBACK_CPU] "
                       f"Requested backend={backend_name} unavailable, using {name}")
    return name
    # END_BLOCK_SELECT_BACKEND


class VideoDecoder:
    # START_CONTRACT: VideoDecoder
    #   PURPOSE: Unified video decoder — wraps backend, provides frame iteration and metadata
    #   INPUTS: { video_path: str|Path, sample_fps: float, backend: str }
    #   OUTPUTS: VideoDecoder instance
    #   SIDE_EFFECTS: opens video file lazily
    #   LINKS: M-VIDEO-DECODE
    # END_CONTRACT: VideoDecoder

    def __init__(
        self,
        video_path: str | Path,
        sample_fps: float = 2.0,
        backend: str = "auto",
    ):
        # START_BLOCK_INIT
        self.video_path = Path(video_path)
        self.sample_fps = sample_fps
        self.backend_name = select_backend(backend)

        _name, backend_info = _resolve_backend(self.backend_name)
        self._iter_frames_fn = backend_info["iter_frames"]
        self._video_info_fn = backend_info["video_info"]
        self._cached_info: VideoInfo | None = None
        # END_BLOCK_INIT

    def get_info(self) -> VideoInfo:
        # START_CONTRACT: get_info
        #   PURPOSE: Get video metadata (cached after first call)
        #   INPUTS: none
        #   OUTPUTS: VideoInfo
        #   SIDE_EFFECTS: reads video file metadata on first call
        #   LINKS: M-VIDEO-DECODE
        # END_CONTRACT: get_info

        if self._cached_info is None:
            # START_BLOCK_GET_INFO
            self._cached_info = self._video_info_fn(self.video_path)
            logger.info(
                f"[VideoDecode][get_info] Loaded video metadata | "
                f"path={self._cached_info.path} "
                f"duration={self._cached_info.duration:.2f} "
                f"width={self._cached_info.width} "
                f"height={self._cached_info.height} "
                f"fps={self._cached_info.fps:.2f}"
            )
            # END_BLOCK_GET_INFO
        return self._cached_info

    def iter_frames(self, keyframes_only: bool = False) -> Iterator[VideoFrame]:
        # START_CONTRACT: iter_frames
        #   PURPOSE: Iterate video frames at configured sample rate
        #   INPUTS: { keyframes_only: bool }
        #   OUTPUTS: Iterator[VideoFrame]
        #   SIDE_EFFECTS: reads video file sequentially
        #   LINKS: M-VIDEO-DECODE
        # END_CONTRACT: iter_frames

        # START_BLOCK_ITER_FRAMES
        logger.info(
            f"[VideoDecode][iter_frames] Sampling frames | "
            f"backend={self.backend_name} sample_fps={self.sample_fps} keyframes_only={keyframes_only}"
        )
        yield from self._iter_frames_fn(self.video_path, self.sample_fps, keyframes_only)
        # END_BLOCK_ITER_FRAMES
