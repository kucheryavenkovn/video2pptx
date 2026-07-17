# FILE: tests/test_strict_fallback_control.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Deterministic focused tests for the corrected strict no-software-fallback
#            HWAccel supporting control (Step 18.4B).
#   SCOPE: terminal states A-L, no-observer M, canonical SHA N, provenance O, JSON P.
#   DEPENDS: tools.probe_pyav_hwaccel, numpy
#   LINKS: V-M-PERF-DETECT-BOTTLENECK
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

_TOOLS = str(Path(__file__).resolve().parent.parent / "tools")
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)

import probe_pyav_hwaccel as probe  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _FakeFrame:
    def __init__(self, *, convert_raises=None, time=0.0, shape=(1080, 1920, 3)):
        self._convert_raises = convert_raises
        self.time = time
        self._shape = shape

    def to_ndarray(self, format=None):  # noqa: A002 (matches PyAV signature)
        if self._convert_raises is not None:
            raise self._convert_raises
        return np.zeros(self._shape, dtype=np.uint8)


class _FakePacket:
    def __init__(self, frames, *, decode_raises=None):
        self._frames = list(frames)
        self._decode_raises = decode_raises

    def decode(self):
        if self._decode_raises is not None:
            raise self._decode_raises
        return list(self._frames)


class _FakeContainer:
    def __init__(self, packets, *, codec_name="h264", codec_long_name="H.264 / AVC",
                 close_raises=None, bad_streams=False):
        self._packets = list(packets)
        self._close_raises = close_raises
        self.closed = False
        if bad_streams:
            self.streams = SimpleNamespace(video=[])  # video[0] -> IndexError
        else:
            cc = SimpleNamespace(codec=SimpleNamespace(name=codec_name, long_name=codec_long_name))
            self.streams = SimpleNamespace(video=[SimpleNamespace(codec_context=cc)])

    def demux(self, stream):
        return list(self._packets)

    def close(self):
        if self._close_raises is not None:
            raise self._close_raises
        self.closed = True


def _fake_av(container=None, *, open_raises=None):
    def _open(path, hwaccel=None):
        if open_raises is not None:
            raise open_raises
        return container
    return SimpleNamespace(open=_open)


def _hwaccel_cls(*, ctor_raises=None, allow_set_raises=None):
    class _HW:
        def __init__(self, device, device_id=0):
            if ctor_raises is not None:
                raise ctor_raises
            self._allow_set_raises = allow_set_raises

        @property
        def allow_software_fallback(self):
            return self._allow

        @allow_software_fallback.setter
        def allow_software_fallback(self, value):
            if self._allow_set_raises is not None:
                raise self._allow_set_raises
            self._allow = value

    return _HW


def _run(container=None, *, av=None, hwaccel_cls=None, packet_limit=None,
         requested_hw_device="cuda"):
    """Run the corrected strict control against fakes."""
    return probe.run_strict_fallback_control(
        Path("unused.mp4"),
        requested_hw_device=requested_hw_device,
        packet_limit=packet_limit,
        _av=av if av is not None else _fake_av(container),
        _hwaccel_cls=hwaccel_cls if hwaccel_cls is not None else _hwaccel_cls(),
    )


# ---------------------------------------------------------------------------
# A-C: loop behavior / terminal state FIRST_FRAME_DECODED
# ---------------------------------------------------------------------------

def test_A_empty_first_packet_then_frame():
    container = _FakeContainer([_FakePacket([]), _FakePacket([_FakeFrame()])])
    r = _run(container)
    assert r["result"] == "FIRST_FRAME_DECODED"
    assert r["packets_examined"] == 2
    assert r["packets_with_decoded_frames"] == 1
    assert r["frames_decoded"] == 1
    assert r["frames_converted"] == 1
    assert r["first_frame_shape"] == [1080, 1920, 3]


def test_B_multiple_empty_packets_before_frame():
    container = _FakeContainer([
        _FakePacket([]), _FakePacket([]), _FakePacket([]),
        _FakePacket([_FakeFrame()]),
    ])
    r = _run(container)
    assert r["result"] == "FIRST_FRAME_DECODED"
    assert r["packets_examined"] == 4
    assert r["packets_with_decoded_frames"] == 1


def test_C_first_packet_yields_frame():
    container = _FakeContainer([_FakePacket([_FakeFrame()]), _FakePacket([_FakeFrame()])])
    r = _run(container)
    assert r["result"] == "FIRST_FRAME_DECODED"
    assert r["packets_examined"] == 1
    assert r["frames_converted"] == 1


# ---------------------------------------------------------------------------
# D: EOF_NO_FRAME
# ---------------------------------------------------------------------------

def test_D_eof_no_frame():
    container = _FakeContainer([_FakePacket([]), _FakePacket([])])
    r = _run(container)
    assert r["result"] == "EOF_NO_FRAME"
    assert r["packets_examined"] == 2
    assert r["frames_decoded"] == 0


# ---------------------------------------------------------------------------
# E-F: decode / conversion exceptions
# ---------------------------------------------------------------------------

def test_E_decode_exception():
    err = RuntimeError("decode boom")
    container = _FakeContainer([_FakePacket([], decode_raises=err)])
    r = _run(container)
    assert r["result"] == "DECODE_EXCEPTION"
    assert r["result_stage"] == "decode"
    assert r["error_type"] == "RuntimeError"
    assert r["error_message"] == "decode boom"


def test_F_frame_conversion_exception():
    err = ValueError("conversion boom")
    container = _FakeContainer([_FakePacket([_FakeFrame(convert_raises=err)])])
    r = _run(container)
    assert r["result"] == "FRAME_CONVERSION_EXCEPTION"
    assert r["result_stage"] == "frame_conversion"
    assert r["error_type"] == "ValueError"
    assert r["frames_decoded"] == 1
    assert r["frames_converted"] == 0


# ---------------------------------------------------------------------------
# G-H: container open / setup exceptions
# ---------------------------------------------------------------------------

def test_G_container_open_exception():
    err = OSError("open boom")
    r = _run(av=_fake_av(None, open_raises=err))
    assert r["result"] == "CONTAINER_OPEN_EXCEPTION"
    assert r["result_stage"] == "container_open"
    assert r["error_type"] == "OSError"
    assert r["container_opened"] is False
    assert r["container_closed"] is False


def test_H_setup_exception_hwaccel_ctor():
    err = RuntimeError("no cuda device")
    r = _run(hwaccel_cls=_hwaccel_cls(ctor_raises=err))
    assert r["result"] == "SETUP_EXCEPTION"
    assert r["result_stage"] == "hwaccel_setup"
    assert r["error_type"] == "RuntimeError"
    assert r["container_opened"] is False


def test_H2_setup_exception_stream_selection():
    container = _FakeContainer([], bad_streams=True)
    r = _run(container)
    assert r["result"] == "SETUP_EXCEPTION"
    assert r["result_stage"] == "stream_selection"
    assert r["container_opened"] is True


# ---------------------------------------------------------------------------
# I-L: deterministic container cleanup
# ---------------------------------------------------------------------------

def test_I_container_closed_on_success():
    container = _FakeContainer([_FakePacket([_FakeFrame()])])
    r = _run(container)
    assert r["result"] == "FIRST_FRAME_DECODED"
    assert r["container_opened"] is True
    assert r["container_closed"] is True
    assert container.closed is True


def test_J_container_closed_on_decode_exception():
    container = _FakeContainer([_FakePacket([], decode_raises=RuntimeError("x"))])
    r = _run(container)
    assert r["result"] == "DECODE_EXCEPTION"
    assert r["container_closed"] is True
    assert container.closed is True


def test_K_container_closed_on_conversion_exception():
    container = _FakeContainer([_FakePacket([_FakeFrame(convert_raises=ValueError("x"))])])
    r = _run(container)
    assert r["result"] == "FRAME_CONVERSION_EXCEPTION"
    assert r["container_closed"] is True


def test_L_close_exception_recorded_primary_preserved():
    close_err = RuntimeError("close boom")
    container = _FakeContainer([_FakePacket([_FakeFrame()])], close_raises=close_err)
    r = _run(container)
    # primary result preserved
    assert r["result"] == "FIRST_FRAME_DECODED"
    # close failure recorded separately, not overwriting primary result
    assert r["container_closed"] is False
    assert r["container_close_error_type"] == "RuntimeError"
    assert r["container_close_error_message"] == "close boom"


def test_packet_limit_reached_distinct():
    container = _FakeContainer([_FakePacket([]), _FakePacket([]), _FakePacket([_FakeFrame()])])
    r = _run(container, packet_limit=2)
    assert r["result"] == "PACKET_LIMIT_REACHED_NO_FRAME"
    assert r["packets_examined"] == 2
    assert "packet_limit=2" in r["observation_notes"]


# ---------------------------------------------------------------------------
# M: no production observer / run_single_observation invocation
# ---------------------------------------------------------------------------

def test_M_no_production_observer_invocation(monkeypatch):
    calls = {"observer": 0, "single": 0}

    def _spy_observer(_=None):
        calls["observer"] += 1
        return None

    def _spy_single(*a, **kw):
        calls["single"] += 1
        return {}

    monkeypatch.setattr(probe, "_register_hwaccel_evidence_observer", _spy_observer)
    monkeypatch.setattr(probe, "run_single_observation", _spy_single)

    container = _FakeContainer([_FakePacket([_FakeFrame()])])
    r = _run(container)

    assert r["result"] == "FIRST_FRAME_DECODED"
    assert calls == {"observer": 0, "single": 0}


# ---------------------------------------------------------------------------
# N: canonical SHA rejection
# ---------------------------------------------------------------------------

def test_N_canonical_sha_mismatch_rejected():
    with pytest.raises(ValueError, match="canonical mode requires clip SHA256"):
        probe.build_strict_control_evidence(
            Path("any.mp4"),
            actual_sha256="00" * 32,
            sha256_match=False,
            canonical_mode=True,
            evidence_head="a" * 40,
            evidence_tree="b" * 40,
            accepted_master_base="c" * 40,
            branch="test",
            env={},
        )


# ---------------------------------------------------------------------------
# O: provenance rejection
# ---------------------------------------------------------------------------

def test_O_abbreviated_base_rejected():
    with pytest.raises(ValueError, match="not a valid git object"):
        probe._validate_accepted_base("da35cf34", REPO)


def test_O_wrong_object_type_rejected():
    tree_sha = probe._git(["rev-parse", "HEAD^{tree}"], REPO)
    with pytest.raises(ValueError, match="expected commit"):
        probe._validate_accepted_base(tree_sha, REPO)


def test_O_nonexistent_object_rejected():
    with pytest.raises(ValueError, match="not a valid git object"):
        probe._validate_accepted_base("f" * 40, REPO)


def test_O_non_ancestor_commit_rejected():
    # Create a throwaway orphan commit (real commit, valid 40-hex) not reachable from HEAD.
    tree_sha = probe._git(["rev-parse", "HEAD^{tree}"], REPO)
    import subprocess
    orphan = subprocess.check_output(
        ["git", "commit-tree", "-m", "strict-control-test-orphan", tree_sha],
        cwd=REPO, text=True,
    ).strip()
    assert len(orphan) == 40
    with pytest.raises(ValueError, match="NOT an ancestor"):
        probe._validate_accepted_base(orphan, REPO)


def test_O_valid_base_accepted():
    head = probe._git(["rev-parse", "HEAD"], REPO)
    # HEAD is an ancestor of itself; must not raise.
    probe._validate_accepted_base(head, REPO)


# ---------------------------------------------------------------------------
# P: JSON serializable deterministic result (no object repr / memory address)
# ---------------------------------------------------------------------------

def test_P_result_json_serializable_no_memory_repr():
    container = _FakeContainer([_FakePacket([]), _FakePacket([_FakeFrame()])])
    r = _run(container)
    # Build a full step-13-compliant control object with provenance fields.
    full = dict(r)
    full.update({
        "clip_identifier": "x.mp4",
        "clip_actual_sha256": "dd" * 32,
        "clip_expected_sha256": "dd" * 32,
        "clip_sha256_match": True,
        "evidence_code_head": "a" * 40,
        "evidence_code_tree": "b" * 40,
        "accepted_master_base": "c" * 40,
    })
    dumped = json.dumps(full, default=str)
    assert "0x" not in dumped  # no Python object repr with memory address
    assert full["result"] == "FIRST_FRAME_DECODED"
    # all values are JSON-native (default=str guarantees serializable)
    again = json.loads(dumped)
    assert again["packets_examined"] == 2
