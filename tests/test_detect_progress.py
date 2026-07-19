# FILE: tests/test_detect_progress.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Phase 21 Wave 3 — map_stage_progress and detection progress mapping
#   ROLE: TEST
#   LINKS: M-APP-DETECT, Phase-21
# END_MODULE_CONTRACT

from __future__ import annotations

from video2pptx.application.progress_map import DETECT_STAGE_RANGES, map_stage_progress


def test_pass1_progress_mapped_to_5_65():
    lo, hi = DETECT_STAGE_RANGES["pass1"]
    assert map_stage_progress(lo, hi, 0) == 5
    assert map_stage_progress(lo, hi, 100) == 65
    mid = map_stage_progress(lo, hi, 50)
    assert 5 <= mid <= 65
    assert mid == 35


def test_pass2_progress_mapped_to_70_93():
    lo, hi = DETECT_STAGE_RANGES["pass2"]
    assert map_stage_progress(lo, hi, 0) == 70
    assert map_stage_progress(lo, hi, 100) == 93
    mid = map_stage_progress(lo, hi, 50)
    assert 70 <= mid <= 93


def test_map_stage_progress_clamps_local():
    assert map_stage_progress(10, 20, -50) == 10
    assert map_stage_progress(10, 20, 150) == 20


def test_progress_never_returns_100_to_70():
    """Simulated two-pass sequence must be monotonic globally."""
    seq = [
        map_stage_progress(0, 5, 100),
        map_stage_progress(5, 65, 0),
        map_stage_progress(5, 65, 50),
        map_stage_progress(5, 65, 100),
        map_stage_progress(65, 70, 100),
        map_stage_progress(70, 93, 0),
        map_stage_progress(70, 93, 100),
        map_stage_progress(93, 97, 100),
        map_stage_progress(97, 100, 100),
    ]
    for a, b in zip(seq, seq[1:], strict=False):
        assert b >= a, f"non-monotonic {a} → {b} in {seq}"
    assert seq[-1] == 100
