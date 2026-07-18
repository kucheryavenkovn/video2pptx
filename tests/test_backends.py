# FILE: tests/test_backends.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for video decoder backends
#   SCOPE: Backend selection, OpenCV frame iteration, metadata extraction
#   DEPENDS: pytest, numpy, cv2, video2pptx.backends
#   LINKS: V-M-BACKENDS, M-BACKENDS
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

import logging
from pathlib import Path

import cv2
import numpy as np
import pytest

from video2pptx.backends import _resolve_backend, iter_frames, video_info
from video2pptx.backends import pyav_backend as _pyav_backend
from video2pptx.backends.pyav_backend import (
    _build_hwaccel_evidence,
    _create_hwaccel_with_evidence,
    _register_hwaccel_evidence_observer,
)
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


# START_BLOCK_HWACCEL_EVIDENCE_TESTS
class TestHwaccelEvidence:
    """Tests for PyAV HWAccel runtime evidence observer (corrected semantics)."""

    def test_observer_disabled_by_default(self):
        assert _pyav_backend._hwaccel_evidence_observer is None

    def test_register_and_unregister(self):
        def dummy(evidence):
            pass
        _register_hwaccel_evidence_observer(dummy)
        assert _pyav_backend._hwaccel_evidence_observer is dummy
        _register_hwaccel_evidence_observer(None)
        assert _pyav_backend._hwaccel_evidence_observer is None

    def test_build_evidence_minimal(self):
        ev = _build_hwaccel_evidence(
            video_path="test.mp4",
            sample_fps=2.0,
            available_hw_devices=["cuda"],
            requested_hw_device="cuda",
            hwaccel_requested=True,
            hwaccel_object_created=True,
            hwaccel_creation_error_type=None,
            hwaccel_creation_error_message=None,
            container_opened_with_hwaccel=True,
            container_open_error=None,
            allow_software_fallback=True,
            codec_context_hwaccel_present=True,
            codec_context_is_hwaccel=True,
            hw_config_present=True,
            hw_config_device_type="cuda",
            hw_config_format="cuda",
            actual_hardware_decode_active=True,
            actual_hardware_decode_observation_method="config present + codec supports HW decode",
            software_fallback_detected=False,
            software_fallback_reason="",
            codec_name="h264",
            codec_long_name="H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10",
            deterministic_hardware_identity="requested=cuda",
            first_frame_yielded=True,
            first_frame_timestamp=0.0,
            first_frame_shape=[1080, 1920, 3],
        )
        assert ev["schema_version"] == "1.0.0"
        assert ev["backend"] == "pyav"
        assert ev["requested_hw_device"] == "cuda"
        assert ev["hwaccel_requested"] is True
        assert ev["codec_context_is_hwaccel"] is True
        assert ev["actual_hardware_decode_active"] is True
        assert ev["codec_name"] == "h264"
        assert ev["first_frame_yielded"] is True

    def test_build_evidence_no_hw(self):
        ev = _build_hwaccel_evidence(
            video_path="test.mp4",
            sample_fps=2.0,
            available_hw_devices=[],
            requested_hw_device=None,
            hwaccel_requested=False,
            hwaccel_object_created=False,
            hwaccel_creation_error_type="NOT_APPLICABLE",
            hwaccel_creation_error_message="NOT_APPLICABLE",
            container_opened_with_hwaccel=False,
            container_open_error=None,
            allow_software_fallback="NOT_APPLICABLE",
            codec_context_hwaccel_present=False,
            codec_context_is_hwaccel=False,
            hw_config_present=False,
            hw_config_device_type=None,
            hw_config_format=None,
            actual_hardware_decode_active=False,
            actual_hardware_decode_observation_method="no HWAccel configured",
            software_fallback_detected="UNKNOWN_NOT_PROVEN",
            software_fallback_reason="",
            codec_name=None,
            codec_long_name=None,
            deterministic_hardware_identity="NOT_APPLICABLE",
            first_frame_yielded=True,
            first_frame_timestamp=1.5,
            first_frame_shape=[480, 640, 3],
        )
        assert ev["requested_hw_device"] is None
        assert ev["hwaccel_requested"] is False
        assert ev["container_opened_with_hwaccel"] is False
        assert ev["codec_context_is_hwaccel"] is False
        assert ev["actual_hardware_decode_active"] is False
        assert ev["software_fallback_detected"] == "UNKNOWN_NOT_PROVEN"
        assert ev["hwaccel_creation_error_type"] == "NOT_APPLICABLE"

    def test_build_evidence_unknown_active(self):
        ev = _build_hwaccel_evidence(
            video_path="test.mp4",
            sample_fps=2.0,
            available_hw_devices=["cuda"],
            requested_hw_device="cuda",
            hwaccel_requested=True,
            hwaccel_object_created=True,
            hwaccel_creation_error_type=None,
            hwaccel_creation_error_message=None,
            container_opened_with_hwaccel=True,
            container_open_error=None,
            allow_software_fallback=True,
            codec_context_hwaccel_present=True,
            codec_context_is_hwaccel=True,
            hw_config_present=False,
            hw_config_device_type=None,
            hw_config_format=None,
            actual_hardware_decode_active="UNKNOWN_NOT_PROVEN",
            actual_hardware_decode_observation_method="no installed API directly proves actual HW decode",
            software_fallback_detected="UNKNOWN_NOT_PROVEN",
            software_fallback_reason="",
            codec_name=None,
            codec_long_name=None,
            deterministic_hardware_identity="requested=cuda",
            first_frame_yielded=False,
            first_frame_timestamp=None,
            first_frame_shape=None,
        )
        assert ev["codec_context_is_hwaccel"] is True
        assert ev["actual_hardware_decode_active"] == "UNKNOWN_NOT_PROVEN"
        assert ev["hw_config_present"] is False
        assert ev["first_frame_yielded"] is False

    def test_build_evidence_not_reached(self):
        ev = _build_hwaccel_evidence(
            video_path="test.mp4",
            sample_fps=2.0,
            available_hw_devices=["cuda"],
            requested_hw_device="cuda",
            hwaccel_requested=True,
            hwaccel_object_created=False,
            hwaccel_creation_error_type="RuntimeError",
            hwaccel_creation_error_message="device not available",
            container_opened_with_hwaccel=False,
            container_open_error="File not found",
            allow_software_fallback="NOT_REACHED",
            codec_context_hwaccel_present=False,
            codec_context_is_hwaccel=None,
            hw_config_present=False,
            hw_config_device_type=None,
            hw_config_format=None,
            actual_hardware_decode_active="NOT_REACHED",
            actual_hardware_decode_observation_method="NOT_REACHED",
            software_fallback_detected="NOT_REACHED",
            software_fallback_reason="",
            codec_name=None,
            codec_long_name=None,
            deterministic_hardware_identity="NOT_REACHED",
            first_frame_yielded=False,
            first_frame_timestamp=None,
            first_frame_shape=None,
        )
        assert ev["container_open_error"] == "File not found"
        assert ev["actual_hardware_decode_active"] == "NOT_REACHED"
        assert ev["hwaccel_creation_error_type"] == "RuntimeError"
        assert ev["allow_software_fallback"] == "NOT_REACHED"

    def test__create_hwaccel_with_evidence_valid_device(self):
        hwaccel, err_type, err_msg = _create_hwaccel_with_evidence("cuda", 0)
        assert hwaccel is not None
        assert err_type is None
        assert err_msg is None

    def test_observer_disabled_no_change(self, monkeypatch):
        import sys
        from types import SimpleNamespace

        import numpy as np

        from video2pptx.backends import pyav_backend

        class FakeFrame:
            def __init__(self, key_frame=True):
                self.key_frame = key_frame
            def to_ndarray(self, format):
                return np.full((2, 3, 3), 42, dtype=np.uint8)

        class FakePacket:
            def __init__(self):
                self._called = False
            def decode(self):
                if not self._called:
                    self._called = True
                    return [FakeFrame() for _ in range(3)]
                return []

        codec_ctx = SimpleNamespace(
            is_hwaccel=False,
            codec=SimpleNamespace(name="mpeg4", long_name="MPEG-4 part 2"),
            hwaccel=None,
        )

        class FakeContainer:
            def __init__(self):
                stream = SimpleNamespace(average_rate=10.0)
                self.streams = SimpleNamespace(video=[stream])
                self.streams.video[0].codec_context = codec_ctx
                self.closed = False
                self._demuxed = False
            def demux(self, stream):
                if not self._demuxed:
                    self._demuxed = True
                    return [FakePacket()]
                return []
            def close(self):
                self.closed = True

        container = FakeContainer()
        fake_av = SimpleNamespace(open=lambda path, hwaccel=None: container)
        monkeypatch.setitem(sys.modules, "av", fake_av)
        monkeypatch.setattr(pyav_backend, "_pick_hw_device", lambda: None)
        _register_hwaccel_evidence_observer(None)
        result = list(pyav_backend.pyav_iter_frames("unused.mp4", sample_fps=10.0))
        assert len(result) == 3
        for vf in result:
            assert vf.image.shape == (2, 3, 3)

    def test_observer_receives_evidence_no_hw(self, monkeypatch):
        import sys
        from types import SimpleNamespace

        import numpy as np

        from video2pptx.backends import pyav_backend

        codec_ctx = SimpleNamespace(
            is_hwaccel=False,
            codec=SimpleNamespace(name="mpeg4", long_name="MPEG-4 part 2"),
            hwaccel=None,
        )

        class FakeContainer:
            def __init__(self):
                stream = SimpleNamespace(average_rate=10.0)
                self.streams = SimpleNamespace(video=[stream])
                self.streams.video[0].codec_context = codec_ctx
                self.closed = False
            def demux(self, stream):
                return [SimpleNamespace(decode=lambda: [SimpleNamespace(
                    key_frame=True,
                    to_ndarray=lambda *a, **kw: np.zeros((2, 3, 3), dtype=np.uint8),
                )])]
            def close(self):
                self.closed = True

        container = FakeContainer()
        fake_av = SimpleNamespace(open=lambda path, hwaccel=None: container)
        monkeypatch.setitem(sys.modules, "av", fake_av)
        monkeypatch.setattr(pyav_backend, "_pick_hw_device", lambda: None)

        observed = []
        def collector(ev):
            observed.append(ev)

        _register_hwaccel_evidence_observer(collector)
        try:
            list(pyav_backend.pyav_iter_frames("unused.mp4", sample_fps=10.0))
        finally:
            _register_hwaccel_evidence_observer(None)

        assert len(observed) == 1
        ev = observed[0]
        assert ev["requested_hw_device"] is None
        assert ev["hwaccel_requested"] is False
        assert ev["hwaccel_object_created"] is False
        assert ev["hwaccel_creation_error_type"] == "NOT_APPLICABLE"
        assert ev["container_opened_with_hwaccel"] is False
        assert ev["codec_context_hwaccel_present"] is False
        assert ev["codec_context_is_hwaccel"] is False
        assert ev["hw_config_present"] is False
        assert ev["actual_hardware_decode_active"] == "UNKNOWN_NOT_PROVEN"
        assert ev["codec_name"] == "mpeg4"
        assert ev["first_frame_yielded"] is True
        assert ev["allow_software_fallback"] == "NOT_APPLICABLE"

    def test_observer_with_hwaccel_no_config(self, monkeypatch):
        import sys
        from types import SimpleNamespace

        import numpy as np

        from video2pptx.backends import pyav_backend

        hwaccel_obj = SimpleNamespace(
            allow_software_fallback=True,
            config=None,
            codec=None,
            is_hw_owned=False,
        )
        codec_ctx = SimpleNamespace(
            is_hwaccel=True,
            codec=SimpleNamespace(name="mpeg4", long_name="MPEG-4 part 2"),
            hwaccel=hwaccel_obj,
        )

        class FakeContainer:
            def __init__(self):
                stream = SimpleNamespace(average_rate=10.0)
                self.streams = SimpleNamespace(video=[stream])
                self.streams.video[0].codec_context = codec_ctx
                self.closed = False
                self._demuxed = False
            def demux(self, stream):
                if not self._demuxed:
                    self._demuxed = True
                    return [SimpleNamespace(decode=lambda: [SimpleNamespace(
                        key_frame=True,
                        to_ndarray=lambda *a, **kw: np.zeros((2, 3, 3), dtype=np.uint8),
                    )])]
                return []
            def close(self):
                self.closed = True

        container = FakeContainer()
        fake_av = SimpleNamespace(open=lambda path, hwaccel=None: container)
        monkeypatch.setitem(sys.modules, "av", fake_av)
        monkeypatch.setattr(pyav_backend, "_pick_hw_device", lambda: "cuda")
        monkeypatch.setattr(pyav_backend, "_create_hwaccel_with_evidence", lambda dt, di=0: (
            SimpleNamespace(allow_software_fallback=True, config=None), None, None
        ))

        observed = []
        def collector(ev):
            observed.append(ev)

        _register_hwaccel_evidence_observer(collector)
        try:
            list(pyav_backend.pyav_iter_frames("unused.mp4", sample_fps=10.0))
        finally:
            _register_hwaccel_evidence_observer(None)

        assert len(observed) == 1
        ev = observed[0]
        assert ev["hwaccel_requested"] is True
        assert ev["requested_hw_device"] == "cuda"
        assert ev["hwaccel_object_created"] is True
        assert ev["container_opened_with_hwaccel"] is True
        assert ev["codec_context_is_hwaccel"] is True
        assert ev["codec_context_hwaccel_present"] is True
        assert ev["hw_config_present"] is False
        assert ev["hw_config_device_type"] is None
        assert ev["hw_config_format"] is None
        assert ev["actual_hardware_decode_active"] == "UNKNOWN_NOT_PROVEN"
        assert ev["deterministic_hardware_identity"] == "requested=cuda"

    def test_observer_with_hwaccel_and_config(self, monkeypatch):
        import sys
        from types import SimpleNamespace

        import numpy as np

        from video2pptx.backends import pyav_backend

        hwaccel_obj = SimpleNamespace(
            allow_software_fallback=True,
            config=SimpleNamespace(device_type="cuda", format="cuda"),
            codec=None,
            is_hw_owned=False,
        )
        codec_ctx = SimpleNamespace(
            is_hwaccel=True,
            codec=SimpleNamespace(name="h264", long_name="H.264 / AVC"),
            hwaccel=hwaccel_obj,
        )

        class FakeContainer:
            def __init__(self):
                stream = SimpleNamespace(average_rate=10.0)
                self.streams = SimpleNamespace(video=[stream])
                self.streams.video[0].codec_context = codec_ctx
                self.closed = False
                self._demuxed = False
            def demux(self, stream):
                if not self._demuxed:
                    self._demuxed = True
                    return [SimpleNamespace(decode=lambda: [SimpleNamespace(
                        key_frame=True,
                        to_ndarray=lambda *a, **kw: np.zeros((2, 3, 3), dtype=np.uint8),
                    )])]
                return []
            def close(self):
                self.closed = True

        container = FakeContainer()
        fake_av = SimpleNamespace(open=lambda path, hwaccel=None: container)
        monkeypatch.setitem(sys.modules, "av", fake_av)
        monkeypatch.setattr(pyav_backend, "_pick_hw_device", lambda: "cuda")
        monkeypatch.setattr(pyav_backend, "_create_hwaccel_with_evidence", lambda dt, di=0: (
            SimpleNamespace(allow_software_fallback=True, config=SimpleNamespace(device_type="cuda", format="cuda")),
            None, None,
        ))

        observed = []
        def collector(ev):
            observed.append(ev)

        _register_hwaccel_evidence_observer(collector)
        try:
            list(pyav_backend.pyav_iter_frames("unused.mp4", sample_fps=10.0))
        finally:
            _register_hwaccel_evidence_observer(None)

        assert len(observed) == 1
        ev = observed[0]
        assert ev["hw_config_present"] is True
        assert ev["hw_config_device_type"] == "cuda"
        assert ev["hw_config_format"] == "cuda"
        assert ev["actual_hardware_decode_active"] == "UNKNOWN_NOT_PROVEN"
        assert ev["deterministic_hardware_identity"] == "requested=cuda"

    def test_observer_creation_error(self, monkeypatch):
        import sys
        from types import SimpleNamespace

        import numpy as np

        from video2pptx.backends import pyav_backend

        codec_ctx = SimpleNamespace(
            is_hwaccel=True,
            codec=SimpleNamespace(name="h264", long_name="H.264 / AVC"),
            hwaccel=SimpleNamespace(allow_software_fallback=True, config=None),
        )

        class FakeContainer:
            def __init__(self):
                stream = SimpleNamespace(average_rate=10.0)
                self.streams = SimpleNamespace(video=[stream])
                self.streams.video[0].codec_context = codec_ctx
                self.closed = False
                self._demuxed = False
            def demux(self, stream):
                if not self._demuxed:
                    self._demuxed = True
                    return [SimpleNamespace(decode=lambda: [SimpleNamespace(
                        key_frame=True,
                        to_ndarray=lambda *a, **kw: np.zeros((2, 3, 3), dtype=np.uint8),
                    )])]
                return []
            def close(self):
                self.closed = True

        container = FakeContainer()
        fake_av = SimpleNamespace(open=lambda path, hwaccel=None: container)
        monkeypatch.setitem(sys.modules, "av", fake_av)
        monkeypatch.setattr(pyav_backend, "_pick_hw_device", lambda: "cuda")
        monkeypatch.setattr(pyav_backend, "_create_hwaccel_with_evidence", lambda dt, di=0: (
            None, "RuntimeError", "CUDA device not found"
        ))

        observed = []
        def collector(ev):
            observed.append(ev)

        _register_hwaccel_evidence_observer(collector)
        try:
            list(pyav_backend.pyav_iter_frames("unused.mp4", sample_fps=10.0))
        finally:
            _register_hwaccel_evidence_observer(None)

        assert len(observed) == 1
        ev = observed[0]
        assert ev["hwaccel_object_created"] is False
        assert ev["hwaccel_creation_error_type"] == "RuntimeError"
        assert ev["hwaccel_creation_error_message"] == "CUDA device not found"

    def test_observer_json_serializable(self):
        import json
        ev = _build_hwaccel_evidence(
            video_path="test.mp4",
            sample_fps=2.0,
            available_hw_devices=["cuda", "dxva2"],
            requested_hw_device="cuda",
            hwaccel_requested=True,
            hwaccel_object_created=True,
            hwaccel_creation_error_type=None,
            hwaccel_creation_error_message=None,
            container_opened_with_hwaccel=True,
            container_open_error=None,
            allow_software_fallback=True,
            codec_context_hwaccel_present=True,
            codec_context_is_hwaccel=True,
            hw_config_present=True,
            hw_config_device_type="cuda",
            hw_config_format="cuda",
            actual_hardware_decode_active="UNKNOWN_NOT_PROVEN",
            actual_hardware_decode_observation_method="no direct proof",
            software_fallback_detected="UNKNOWN_NOT_PROVEN",
            software_fallback_reason="",
            codec_name="h264",
            codec_long_name="H.264 / AVC",
            deterministic_hardware_identity="requested=cuda",
            first_frame_yielded=True,
            first_frame_timestamp=0.0,
            first_frame_shape=[1080, 1920, 3],
        )
        loaded = json.loads(json.dumps(ev))
        assert loaded["schema_version"] == "1.0.0"
        assert loaded["hwaccel_requested"] is True
        assert loaded["first_frame_shape"] == [1080, 1920, 3]

    def test_observer_exception_does_not_break_decoder(self, monkeypatch):
        import sys
        from types import SimpleNamespace

        import numpy as np

        from video2pptx.backends import pyav_backend

        codec_ctx = SimpleNamespace(
            is_hwaccel=False,
            codec=SimpleNamespace(name="mpeg4", long_name="MPEG-4 part 2"),
            hwaccel=None,
        )

        class FakeContainer:
            def __init__(self):
                stream = SimpleNamespace(average_rate=10.0)
                self.streams = SimpleNamespace(video=[stream])
                self.streams.video[0].codec_context = codec_ctx
                self.closed = False
            def demux(self, stream):
                return [SimpleNamespace(decode=lambda: [SimpleNamespace(
                    key_frame=True,
                    to_ndarray=lambda *a, **kw: np.zeros((2, 3, 3), dtype=np.uint8),
                )])]
            def close(self):
                self.closed = True

        container = FakeContainer()
        fake_av = SimpleNamespace(open=lambda path, hwaccel=None: container)
        monkeypatch.setitem(sys.modules, "av", fake_av)
        monkeypatch.setattr(pyav_backend, "_pick_hw_device", lambda: None)

        def failing_observer(ev):
            raise RuntimeError("observer failure")

        _register_hwaccel_evidence_observer(failing_observer)
        try:
            result = list(pyav_backend.pyav_iter_frames("unused.mp4", sample_fps=10.0))
        finally:
            _register_hwaccel_evidence_observer(None)

        assert len(result) > 0
        assert container.closed

    def test_observer_cleanup_on_success(self, monkeypatch):
        import sys
        from types import SimpleNamespace

        import numpy as np

        from video2pptx.backends import pyav_backend

        codec_ctx = SimpleNamespace(
            is_hwaccel=False,
            codec=SimpleNamespace(name="mpeg4", long_name="MPEG-4 part 2"),
            hwaccel=None,
        )

        class FakeContainer:
            def __init__(self):
                stream = SimpleNamespace(average_rate=10.0)
                self.streams = SimpleNamespace(video=[stream])
                self.streams.video[0].codec_context = codec_ctx
                self.closed = False
            def demux(self, stream):
                return [SimpleNamespace(decode=lambda: [SimpleNamespace(
                    key_frame=True,
                    to_ndarray=lambda *a, **kw: np.zeros((2, 3, 3), dtype=np.uint8),
                )])]
            def close(self):
                self.closed = True

        container = FakeContainer()
        fake_av = SimpleNamespace(open=lambda path, hwaccel=None: container)
        monkeypatch.setitem(sys.modules, "av", fake_av)
        monkeypatch.setattr(pyav_backend, "_pick_hw_device", lambda: None)

        def collector(ev):
            pass

        _register_hwaccel_evidence_observer(collector)
        list(pyav_backend.pyav_iter_frames("unused.mp4", sample_fps=10.0))
        assert _pyav_backend._hwaccel_evidence_observer is collector
        _register_hwaccel_evidence_observer(None)

    def test_generator_explicit_close(self, monkeypatch):
        import sys
        from types import SimpleNamespace

        import numpy as np

        from video2pptx.backends import pyav_backend

        codec_ctx = SimpleNamespace(
            is_hwaccel=False,
            codec=SimpleNamespace(name="mpeg4", long_name="MPEG-4 part 2"),
            hwaccel=None,
        )

        class FakeContainer:
            def __init__(self):
                stream = SimpleNamespace(average_rate=10.0)
                self.streams = SimpleNamespace(video=[stream])
                self.streams.video[0].codec_context = codec_ctx
                self.closed = False
                self._demuxed = False
            def demux(self, stream):
                if not self._demuxed:
                    self._demuxed = True
                    return [SimpleNamespace(decode=lambda: [SimpleNamespace(
                        key_frame=True,
                        to_ndarray=lambda *a, **kw: np.zeros((2, 3, 3), dtype=np.uint8),
                    )])]
                return []
            def close(self):
                self.closed = True

        container = FakeContainer()
        fake_av = SimpleNamespace(open=lambda path, hwaccel=None: container)
        monkeypatch.setitem(sys.modules, "av", fake_av)
        monkeypatch.setattr(pyav_backend, "_pick_hw_device", lambda: None)

        gen = pyav_backend.pyav_iter_frames("unused.mp4", sample_fps=10.0)
        first = next(gen)
        assert first is not None
        assert not container.closed
        gen.close()
        assert container.closed

    def test_no_python_repr_in_identity(self):
        ev = _build_hwaccel_evidence(
            video_path="test.mp4",
            sample_fps=2.0,
            available_hw_devices=["cuda"],
            requested_hw_device="cuda",
            hwaccel_requested=True,
            hwaccel_object_created=True,
            hwaccel_creation_error_type=None,
            hwaccel_creation_error_message=None,
            container_opened_with_hwaccel=True,
            container_open_error=None,
            allow_software_fallback=True,
            codec_context_hwaccel_present=True,
            codec_context_is_hwaccel=True,
            hw_config_present=True,
            hw_config_device_type="cuda",
            hw_config_format="cuda",
            actual_hardware_decode_active="UNKNOWN_NOT_PROVEN",
            actual_hardware_decode_observation_method="test",
            software_fallback_detected="UNKNOWN_NOT_PROVEN",
            software_fallback_reason="",
            codec_name="h264",
            codec_long_name="H.264 / AVC",
            deterministic_hardware_identity="requested=cuda",
            first_frame_yielded=True,
            first_frame_timestamp=0.0,
            first_frame_shape=[1080, 1920, 3],
        )
        identity = ev["deterministic_hardware_identity"]
        assert "object at" not in identity
        assert "0x" not in identity
# END_BLOCK_HWACCEL_EVIDENCE_TESTS
