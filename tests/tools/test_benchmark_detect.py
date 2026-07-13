# FILE: tests/tools/test_benchmark_detect.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for benchmark_detect.py derived functions
#   SCOPE: score distribution, bottleneck ranking, invariant evaluation, output signature
#   DEPENDS: pytest, numpy, tools.benchmark_detect
#   LINKS: V-PERF-DETECT-SHORT-BENCHMARK
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   TestScoreDistribution - empty, known values, single value
#   TestRankBottlenecks - stage total equals elapsed, residual is non-negative
#   TestEvaluateInvariants - PASS, FAIL, SKIPPED cases
# END_MODULE_MAP

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# Add tools directory to path so we can import the module
_tools_dir = str(Path(__file__).resolve().parent.parent.parent / "tools")
if _tools_dir not in sys.path:
    sys.path.insert(0, _tools_dir)

from benchmark_detect import (
    compute_score_distribution,
    compute_output_signature,
    evaluate_invariants,
    rank_bottlenecks,
)


class TestScoreDistribution:
    def test_empty_list(self):
        result = compute_score_distribution([])
        assert result["count"] == 0
        assert result["p50"] is None
        assert result["p90"] is None
        assert result["p95"] is None
        assert result["p99"] is None
        assert result["max"] is None

    def test_single_value(self):
        result = compute_score_distribution([5.0])
        assert result["count"] == 1
        assert result["p50"] == 5.0
        assert result["max"] == 5.0

    def test_known_uniform_scores(self):
        scores = list(range(1, 101))
        result = compute_score_distribution(scores)
        assert result["count"] == 100
        assert result["p50"] == 50.5
        assert result["max"] == 100.0

    def test_typed_outputs(self):
        result = compute_score_distribution([0.5, 1.0, 1.5])
        assert isinstance(result["count"], int)
        assert all(isinstance(v, float) for v in [result["p50"], result["max"]]
                   if v is not None)

    def test_not_mutating_input(self):
        original = [0.1, 0.2, 0.3]
        compute_score_distribution(original)
        assert original == [0.1, 0.2, 0.3]


class TestRankBottlenecks:
    def test_stage_total_does_not_exceed_elapsed(self):
        metrics = {
            "timers": {
                "roi": 1.0,
                "extract_features": 2.0,
                "visual_distance": 3.0,
                "threshold": 0.5,
                "debounce": 0.5,
                "pass2_collect": 0.5,
                "pass2_dedupe": 0.2,
                "pass2_screenshots": 0.3,
            }
        }
        elapsed = 10.0
        result = rank_bottlenecks(metrics, elapsed)
        stage_total = sum(r["elapsed_seconds"] for r in result if r["stage"] != "unattributed_residual")
        residual_row = [r for r in result if r["stage"] == "unattributed_residual"]
        assert len(residual_row) == 1
        assert residual_row[0]["elapsed_seconds"] == pytest.approx(elapsed - stage_total)
        assert residual_row[0]["elapsed_seconds"] >= 0

    def test_all_stages_present_in_output(self):
        metrics = {
            "timers": {
                "roi": 0.5, "extract_features": 0.5, "visual_distance": 0.5,
                "threshold": 0.5, "debounce": 0.5, "pass2_collect": 0.5,
                "pass2_dedupe": 0.5, "pass2_screenshots": 0.5,
            }
        }
        elapsed = 5.0
        result = rank_bottlenecks(metrics, elapsed)
        stage_names = {r["stage"] for r in result}
        expected = {"roi", "extract_features", "visual_distance", "threshold",
                     "debounce", "pass2_collect", "pass2_dedupe", "pass2_screenshots",
                     "unattributed_residual"}
        assert stage_names == expected

    def test_sorted_by_elapsed_descending_excluding_residual(self):
        metrics = {
            "timers": {
                "roi": 1.0, "extract_features": 5.0, "visual_distance": 3.0,
                "threshold": 2.0, "debounce": 0.5, "pass2_collect": 0.5,
                "pass2_dedupe": 0.5, "pass2_screenshots": 0.5,
            }
        }
        elapsed = 20.0
        result = rank_bottlenecks(metrics, elapsed)
        stages = [r for r in result if r["stage"] != "unattributed_residual"]
        for i in range(len(stages) - 1):
            assert stages[i]["elapsed_seconds"] >= stages[i + 1]["elapsed_seconds"]

    def test_zero_elapsed(self):
        result = rank_bottlenecks({"timers": {}}, 0.0)
        assert all(r["elapsed_seconds"] == 0.0 for r in result)

    def test_cumulative_percentage_one_hundred(self):
        metrics = {
            "timers": {
                "roi": 2.0, "extract_features": 2.0, "visual_distance": 2.0,
                "threshold": 2.0, "debounce": 2.0, "pass2_collect": 2.0,
                "pass2_dedupe": 2.0, "pass2_screenshots": 2.0,
            }
        }
        elapsed = 20.0  # stage total = 16, residual = 4
        result = rank_bottlenecks(metrics, elapsed)
        total_pct = sum(r["percentage"] for r in result)
        assert total_pct == pytest.approx(100.0)


class TestEvaluateInvariants:
    def test_all_pass(self):
        metrics = {
            "counters": {
                "frames_sampled": 100,
                "pass2_frames_sampled": 20,
                "ndarray_conversions": 120,
                "frames_decoded": 200,
                "representative_frames": 10,
                "representative_frame_bytes": 5000,
                "screenshots_written": 5,
                "features_full": 50,
                "features_quick": 50,
            },
            "gauges": {
                "rss_before_mb": 100.0,
                "rss_peak_mb": 150.0,
                "rss_after_mb": 110.0,
            },
        }
        result = evaluate_invariants(metrics, 5)
        for name, entry in result.items():
            if entry["status"] != "PASS":
                pytest.fail(f"{name}: {entry}")

    def test_features_fail(self):
        metrics = {
            "counters": {
                "frames_sampled": 100,
                "features_full": 40,
                "features_quick": 40,
            },
            "gauges": {},
        }
        result = evaluate_invariants(metrics, 0)
        assert result["features_equal_frames_sampled"]["status"] == "FAIL"

    def test_rss_skipped_when_all_zero(self):
        metrics = {
            "counters": {"representative_frames": 1, "screenshots_written": 1},
            "gauges": {"rss_before_mb": 0, "rss_peak_mb": 0, "rss_after_mb": 0},
        }
        result = evaluate_invariants(metrics, 1)
        assert result["rss_peak_bounds"]["status"] == "SKIPPED"


class TestOutputSignature:
    def test_deterministic(self):
        sig1 = compute_output_signature([0.0, 1.0], [0.1, 0.2], [{"start": 0, "end": 1.0}])
        sig2 = compute_output_signature([0.0, 1.0], [0.1, 0.2], [{"start": 0, "end": 1.0}])
        assert sig1["canonical_sha256"] == sig2["canonical_sha256"]

    def test_different_inputs_different_hash(self):
        sig1 = compute_output_signature([0.0, 1.0], [0.1, 0.2], [{"start": 0, "end": 1.0}])
        sig2 = compute_output_signature([0.0, 2.0], [0.1, 0.2], [{"start": 0, "end": 1.0}])
        assert sig1["canonical_sha256"] != sig2["canonical_sha256"]
