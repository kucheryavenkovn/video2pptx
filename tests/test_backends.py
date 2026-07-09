# FILE: tests/test_backends.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for video decoder backends
#   SCOPE: Backend selection, OpenCV frame iteration, metadata extraction
#   DEPENDS: pytest, numpy, cv2, video2pptx.backends
#   LINKS: V-M-BACKENDS
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

import logging
from pathlib import Path

import cv2
import numpy as np
import pytest

from video2pptx.backends import _resolve_backend, iter_frames, video_info
from video2pptx.models import VideoFrame, VideoInfo

logger = logging.getLogger(__name__)


# START_BLOCK_HELPERS
def make_test_video(tmp_path: Path, num_frames: int = 60, fps: float = 30.0, width: int = 320, height: int = 240) -> Path:
    """Create a synthetic test video with colored frames."""
    path = tmp_path / "test_video.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(path), fourcc, fps, (width, height))

    for i in range(num_frames):
        color = (i * 4 % 255, i * 8 % 255, i * 16 % 255)
        frame = np.full((height, width, 3), color, dtype=np.uint8)
        out.write(frame)
    out.release()
    return path
# END_BLOCK_HELPERS


class TestResolveBackend:
    def test_auto_returns_opencv(self):
        name, info = _resolve_backend("auto")
        assert name == "opencv"
        assert info["available"] is True

    def test_opencv_explicit(self):
        name, info = _resolve_backend("opencv")
        assert name == "opencv"

    def test_unknown_falls_back(self):
        name, info = _resolve_backend("nonexistent")
        assert name == "opencv"

    def test_auto_fallback_log(self, loguru_sink):
        _resolve_backend("pynv")
        assert any("not available" in msg for msg in loguru_sink)

    def test_unsupported_falls_back(self, loguru_sink):
        _resolve_backend("pyav")
        assert any("not available" in msg for msg in loguru_sink)


class TestVideoInfo:
    def test_opencv_video_info(self, tmp_path):
        video_path = make_test_video(tmp_path, num_frames=30, fps=10.0)
        info = video_info(video_path, backend="opencv")
        assert isinstance(info, VideoInfo)
        assert info.duration == pytest.approx(3.0, abs=0.5)
        assert info.width == 320
        assert info.height == 240
        assert info.fps == pytest.approx(10.0, abs=1.0)

    def test_missing_video(self):
        with pytest.raises(FileNotFoundError):
            video_info("/nonexistent/video.mp4", backend="opencv")

    def test_auto_backend_video_info(self, tmp_path):
        video_path = make_test_video(tmp_path)
        info = video_info(video_path)
        assert info.width > 0


class TestIterFrames:
    def test_iter_frames_count(self, tmp_path):
        video_path = make_test_video(tmp_path, num_frames=60, fps=30.0)
        frames = list(iter_frames(video_path, sample_fps=10.0, backend="opencv"))
        assert len(frames) > 0
        # 60 frames at 30fps sampled at 10fps → ~20 frames (every 3rd frame)
        assert len(frames) == 20

    def test_iter_frames_type(self, tmp_path):
        video_path = make_test_video(tmp_path)
        frames = list(iter_frames(video_path, sample_fps=30.0, backend="opencv"))
        for vf in frames:
            assert isinstance(vf, VideoFrame)
            assert isinstance(vf.timestamp, float)
            assert isinstance(vf.image, np.ndarray)

    def test_iter_frames_timestamps_increasing(self, tmp_path):
        video_path = make_test_video(tmp_path, num_frames=60, fps=30.0)
        frames = list(iter_frames(video_path, sample_fps=10.0, backend="opencv"))
        timestamps = [vf.timestamp for vf in frames]
        assert timestamps == sorted(timestamps)
        assert timestamps[0] >= 0.0

    def test_iter_frames_rgb(self, tmp_path):
        video_path = make_test_video(tmp_path)
        frames = list(iter_frames(video_path, sample_fps=30.0, backend="opencv"))
        for vf in frames[:3]:
            # RGB, not BGR
            assert vf.image.shape[2] == 3

    def test_iter_frames_auto_backend(self, tmp_path):
        video_path = make_test_video(tmp_path)
        frames = list(iter_frames(video_path, sample_fps=5.0))
        assert len(frames) > 0
