# FILE: tests/test_duration_semantics.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Phase 21 Wave 5 — min_stable_duration time-based debounce semantics
#   ROLE: TEST
#   LINKS: M-SLIDE-DETECTOR, M-CONFIG, Phase-21
# END_MODULE_CONTRACT

from __future__ import annotations

import pytest
from pydantic import ValidationError

from video2pptx.config import DetectionConfig as AppDetectionConfig
from video2pptx.infrastructure.persistence.dto import DetectionConfigDocument
from video2pptx.models import FrameFeatures
from video2pptx.slide_detector import ChangeEvent, debounce_changes


def _ev(ts: float) -> ChangeEvent:
    return ChangeEvent(timestamp=ts, score=1.0, features=FrameFeatures(timestamp=ts))


def test_zero_stable_duration_disables_debounce():
    changes = [_ev(0.0), _ev(0.1), _ev(0.2), _ev(5.0)]
    out = debounce_changes(changes, 0.0)
    assert len(out) == len(changes)
    assert [c.timestamp for c in out] == [0.0, 0.1, 0.2, 5.0]


def test_stable_duration_uses_seconds():
    changes = [_ev(0.0), _ev(0.5), _ev(1.0), _ev(3.0)]
    out = debounce_changes(changes, 1.0)
    assert [c.timestamp for c in out] == [0.0, 1.0, 3.0]


def test_debounce_independent_of_sample_fps():
    """Same timestamps + min_stable must yield same result regardless of FPS context.

    (sample_fps is intentionally not an argument of debounce_changes.)
    """
    timestamps = [0.0, 0.4, 0.8, 1.5, 3.0, 3.2, 6.0]
    changes = [_ev(t) for t in timestamps]
    expected = None
    for _fps in (1, 2, 5, 10):
        out = [c.timestamp for c in debounce_changes(changes, 1.0)]
        if expected is None:
            expected = out
        else:
            assert out == expected
    assert expected == [0.0, 1.5, 3.0, 6.0]


def test_negative_stable_duration_rejected_appconfig():
    with pytest.raises(ValidationError):
        AppDetectionConfig(min_stable_duration=-0.1)


def test_dto_allows_zero_stable_duration():
    doc = DetectionConfigDocument(min_stable_duration=0.0)
    assert doc.min_stable_duration == 0.0


def test_dto_rejects_negative_stable_duration():
    with pytest.raises(ValidationError):
        DetectionConfigDocument(min_stable_duration=-1.0)


def test_min_slide_duration_boundary():
    ok = AppDetectionConfig(min_slide_duration=0.5)
    assert ok.min_slide_duration == 0.5
    with pytest.raises(ValidationError):
        AppDetectionConfig(min_slide_duration=0.49)
    with pytest.raises(ValidationError):
        DetectionConfigDocument(min_slide_duration=0.0)


def test_gui_allows_zero_stable_duration():
    """GUI spin range contract: 0.0 is valid (checked without constructing Qt if possible)."""
    # Import module path that defines spin range via source contract test
    import inspect

    from video2pptx.gui import settings_project as sp

    src = inspect.getsource(sp.ProjectSettingsDialog._setup_ui)
    assert "setRange(0.0, 30.0)" in src or "setRange(0, 30" in src
