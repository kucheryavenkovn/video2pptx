# FILE: tests/test_detection_counts.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Phase 21 Wave 6 — DetectionCounts and score distribution
#   ROLE: TEST
# END_MODULE_CONTRACT

from __future__ import annotations

from video2pptx.detection_counts import DetectionCounts, score_distribution_summary


def test_score_distribution_summary_empty():
    s = score_distribution_summary([])
    assert s["score_count"] == 0


def test_score_distribution_summary_basic():
    scores = [0.01, 0.02, 0.03, 0.5, 0.9]
    s = score_distribution_summary(scores)
    assert s["score_count"] == 5
    assert s["score_min"] == 0.01
    assert s["score_max"] == 0.9
    assert s["score_median"] == 0.03


def test_detection_counts_to_dict():
    c = DetectionCounts(sampled_frames=10, candidate_changes=5, debounced_changes=3)
    d = c.to_dict()
    assert d["sampled_frames"] == 10
    assert d["candidate_changes"] == 5
    assert d["debounced_changes"] == 3
