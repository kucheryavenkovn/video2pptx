# FILE: tests/test_benchmark_detect.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Verify reporting-only calculations used by the Phase 18 detect benchmark.
#   SCOPE: Complete-series percentiles and explicit invariant statuses.
#   DEPENDS: tools.benchmark_detect, pytest
#   LINKS: M-DETECT-BENCHMARK, V-PERF-DETECT-SHORT-BENCHMARK
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   test_score_distribution_uses_complete_series - exact NumPy percentile evidence
#   test_evaluate_invariants_reports_explicit_statuses - PASS invariant schema
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Cover complete-series percentiles and benchmark invariant status output.
# END_CHANGE_SUMMARY

import numpy as np
from tools.benchmark_detect import compute_score_distribution, evaluate_invariants


def test_score_distribution_uses_complete_series():
    values = [0.0, 1.0, 2.0, 3.0, 100.0]
    result = compute_score_distribution(values)
    assert result["count"] == len(values)
    assert result["p50"] == float(np.percentile(values, 50))
    assert result["p99"] == float(np.percentile(values, 99))
    assert result["max"] == 100.0


def test_evaluate_invariants_reports_explicit_statuses():
    metrics = {
        "counters": {
            "features_full": 2, "features_quick": 0, "frames_sampled": 2,
            "pass2_frames_sampled": 2, "frames_decoded": 20, "ndarray_conversions": 4,
            "representative_frames": 1, "representative_frame_bytes": 12,
            "screenshots_written": 1,
        },
        "gauges": {"rss_before_mb": 10, "rss_peak_mb": 12, "rss_after_mb": 11},
    }
    results = evaluate_invariants(metrics, png_count=1)
    assert {value["status"] for value in results.values()} == {"PASS"}
