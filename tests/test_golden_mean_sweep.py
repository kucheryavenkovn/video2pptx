# FILE: tests/test_golden_mean_sweep.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit tests for Phase 19 golden-mean sweep pure helpers and schema
#   SCOPE: IoU, segment match, quality metrics, parse helpers
#   DEPENDS: pytest, tools.sweep_analysis_resolution
#   LINKS: V-M-GOLDEN-MEAN-SWEEP, M-GOLDEN-MEAN-SWEEP
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "src"))

from video2pptx.models import SlideSegment  # noqa: E402

import sweep_analysis_resolution as sweep  # noqa: E402


class TestIntervalIou:
    def test_identical(self):
        assert sweep.interval_iou((0, 10), (0, 10)) == pytest.approx(1.0)

    def test_disjoint(self):
        assert sweep.interval_iou((0, 5), (5, 10)) == pytest.approx(0.0)

    def test_partial(self):
        assert sweep.interval_iou((0, 10), (5, 15)) == pytest.approx(5 / 15)


def _seg(index: int, start: float, end: float) -> SlideSegment:
    return SlideSegment(
        index=index,
        start=start,
        end=end,
        duration=end - start,
        representative_timestamp=(start + end) / 2,
    )


class TestMatchAndQuality:
    def test_perfect_match(self):
        ref = [_seg(1, 0, 10), _seg(2, 10, 20)]
        q = sweep.compute_quality_metrics(ref, ref)
        assert q["missed"] == 0
        assert q["false_splits"] == 0
        assert q["missed_slide_rate"] == 0.0
        assert q["false_split_rate"] == 0.0

    def test_missed_and_false_split(self):
        ref = [_seg(1, 0, 10), _seg(2, 10, 20)]
        cand = [_seg(1, 0, 10), _seg(2, 30, 40)]
        q = sweep.compute_quality_metrics(ref, cand)
        assert q["missed"] == 1
        assert q["false_splits"] == 1
        assert q["missed_slide_rate"] == pytest.approx(0.5)
        assert q["false_split_rate"] == pytest.approx(0.5)


class TestParse:
    def test_max_sides(self):
        assert sweep.parse_max_sides("none,640,320") == [None, 640, 320]

    def test_fps(self):
        assert sweep.parse_fps_list("2.0,1.0,0.5") == [2.0, 1.0, 0.5]


class TestGates:
    def test_pass(self):
        q = {
            "missed_slide_rate": 0.0,
            "false_split_rate": 0.0,
            "timestamp_error_all": {"median": 0.2},
        }
        g = sweep.passes_quality_gates(q)
        assert g["pass"] is True

    def test_fail_missed(self):
        q = {
            "missed_slide_rate": 0.2,
            "false_split_rate": 0.0,
            "timestamp_error_all": {"median": 0.2},
        }
        g = sweep.passes_quality_gates(q)
        assert g["pass"] is False
