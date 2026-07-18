# FILE: tests/test_video_decode.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for VideoDecoder unified interface
#   SCOPE: Frame iteration, metadata, backend selection, error handling
#   DEPENDS: pytest, numpy, cv2, video2pptx.video_decode
#   LINKS: V-M-VIDEO-DECODE, M-VIDEO-DECODE
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

import logging
from pathlib import Path

import cv2
import numpy as np
import pytest

from video2pptx.models import VideoInfo
from video2pptx.video_decode import VideoDecoder, select_backend

logger = logging.getLogger(__name__)


def make_test_video(tmp_path: Path, num_frames: int = 60, fps: float = 30.0, width: int = 320, height: int = 240) -> Path:
    path = tmp_path / "test.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
    for i in range(num_frames):
        color = (i * 4 % 255, i * 8 % 255, i * 16 % 255)
        frame = np.full((height, width, 3), color, dtype=np.uint8)
        out.write(frame)
    out.release()
    return path


class TestSelectBackend:
    def test_auto_returns_opencv(self):
        name = select_backend("auto")
        assert name == "opencv"

    def test_explicit_opencv(self):
        name = select_backend("opencv")
        assert name == "opencv"

    def test_fallback_log(self, loguru_sink):
        name = select_backend("pynv")
        assert name == "opencv"
        assert any("FALLBACK_CPU" in msg for msg in loguru_sink)


class TestVideoDecoder:
    def test_get_info(self, tmp_path):
        video_path = make_test_video(tmp_path, num_frames=30, fps=10.0)
        decoder = VideoDecoder(video_path, backend="opencv")
        info = decoder.get_info()
        assert isinstance(info, VideoInfo)
        assert info.width == 320
        assert info.height == 240
        assert info.duration == pytest.approx(3.0, abs=0.5)

    def test_get_info_cached(self, tmp_path):
        video_path = make_test_video(tmp_path)
        decoder = VideoDecoder(video_path, backend="opencv")
        info1 = decoder.get_info()
        info2 = decoder.get_info()
        assert info1 is info2

    def test_iter_frames(self, tmp_path):
        video_path = make_test_video(tmp_path, num_frames=60, fps=30.0)
        decoder = VideoDecoder(video_path, sample_fps=15.0, backend="opencv")
        frames = list(decoder.iter_frames())
        assert len(frames) == 30

    def test_iter_frames_auto_backend(self, tmp_path):
        video_path = make_test_video(tmp_path)
        decoder = VideoDecoder(video_path, sample_fps=5.0)
        frames = list(decoder.iter_frames())
        assert len(frames) > 0

    def test_same_frame_count_as_backend(self, tmp_path):
        video_path = make_test_video(tmp_path, num_frames=30, fps=10.0)

        decoder = VideoDecoder(video_path, sample_fps=10.0, backend="opencv")
        direct_frames = list(decoder.iter_frames())

        decoder2 = VideoDecoder(video_path, sample_fps=10.0, backend="auto")
        auto_frames = list(decoder2.iter_frames())

        assert len(direct_frames) == len(auto_frames)

    def test_missing_video(self):
        with pytest.raises(FileNotFoundError):
            decoder = VideoDecoder("/nonexistent/video.mp4", backend="opencv")
            list(decoder.iter_frames())

    def test_timestamps_increasing(self, tmp_path):
        video_path = make_test_video(tmp_path)
        decoder = VideoDecoder(video_path, sample_fps=10.0, backend="opencv")
        ts = [f.timestamp for f in decoder.iter_frames()]
        assert ts == sorted(ts)
