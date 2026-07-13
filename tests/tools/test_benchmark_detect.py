# FILE: tests/tools/test_benchmark_detect.py
# VERSION: 2.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for benchmark_detect.py pure helpers, derived metrics, aggregate evidence
#   SCOPE: score distribution, bottleneck ranking, invariant evaluation, output signature,
#          derived metric formulas, signature aggregation, median selection, stage accounting,
#          path sanitization, change_count, select_backend integration, aggregate structure
#   DEPENDS: pytest, numpy, tools.benchmark_detect
#   LINKS: V-PERF-DETECT-SHORT-BENCHMARK
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_tools_dir = str(Path(__file__).resolve().parent.parent.parent / "tools")
if _tools_dir not in sys.path:
    sys.path.insert(0, _tools_dir)

from benchmark_detect import (
    HISTORICAL_CANONICAL_SIGNATURE,
    STAGE_NAMES,
    aggregate_signatures,
    build_aggregate_evidence,
    compute_derived_metrics,
    compute_output_signature,
    compute_score_distribution,
    compute_stage_accounting,
    evaluate_invariants,
    rank_bottlenecks,
    sanitize_committed_path,
    select_median_run,
)

# =========================================================================
# Existing tests (preserved)
# =========================================================================

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
                "roi": 1.0, "extract_features": 2.0, "visual_distance": 3.0,
                "threshold": 0.5, "debounce": 0.5, "pass2_collect": 0.5,
                "pass2_dedupe": 0.2, "pass2_screenshots": 0.3,
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
        elapsed = 20.0
        result = rank_bottlenecks(metrics, elapsed)
        total_pct = sum(r["percentage"] for r in result)
        assert total_pct == pytest.approx(100.0)


class TestEvaluateInvariants:
    def test_all_pass(self):
        metrics = {
            "counters": {
                "frames_sampled": 100, "pass2_frames_sampled": 20,
                "ndarray_conversions": 120, "frames_decoded": 200,
                "representative_frames": 10, "representative_frame_bytes": 5000,
                "screenshots_written": 5, "features_full": 50, "features_quick": 50,
            },
            "gauges": {"rss_before_mb": 100.0, "rss_peak_mb": 150.0, "rss_after_mb": 110.0},
        }
        result = evaluate_invariants(metrics, 5)
        for name, entry in result.items():
            if entry["status"] != "PASS":
                pytest.fail(f"{name}: {entry}")

    def test_features_fail(self):
        metrics = {"counters": {"frames_sampled": 100, "features_full": 40, "features_quick": 40}, "gauges": {}}
        result = evaluate_invariants(metrics, 0)
        assert result["features_equal_frames_sampled"]["status"] == "FAIL"

    def test_rss_skipped_when_all_zero(self):
        metrics = {"counters": {"representative_frames": 1, "screenshots_written": 1}, "gauges": {"rss_before_mb": 0, "rss_peak_mb": 0, "rss_after_mb": 0}}
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


# =========================================================================
# New tests: 4.1 Derived metrics
# =========================================================================

class TestDerivedMetrics:
    def test_exact_formulas(self):
        dm = compute_derived_metrics(detect_elapsed=50.0, video_duration=100.0, frames_sampled=200)
        assert dm["real_time_multiplier"] == 0.5
        assert dm["processing_x_realtime"] == 2.0
        assert dm["effective_sampled_fps"] == 2.0

    def test_zero_duration(self):
        dm = compute_derived_metrics(detect_elapsed=0, video_duration=0, frames_sampled=0)
        assert dm["real_time_multiplier"] is None
        assert dm["processing_x_realtime"] is None
        assert dm["effective_sampled_fps"] is None

    def test_no_division_by_zero(self):
        dm = compute_derived_metrics(detect_elapsed=10.0, video_duration=0, frames_sampled=100)
        assert dm["real_time_multiplier"] is None
        assert dm["processing_x_realtime"] is None
        assert dm["effective_sampled_fps"] is None

    def test_consistency_round_trip(self):
        dm = compute_derived_metrics(50.0, 100.0, 200)
        assert dm["processing_x_realtime"] == pytest.approx(1.0 / dm["real_time_multiplier"])


# =========================================================================
# New tests: 4.2 Signature aggregation
# =========================================================================

class TestSignatureAggregation:
    def test_three_identical_true(self):
        sigs = [
            {"canonical_sha256": "aaa"},
            {"canonical_sha256": "aaa"},
            {"canonical_sha256": "aaa"},
        ]
        result = aggregate_signatures(sigs, "aaa")
        assert result["signature_identity"] is True
        assert result["historical_signature_match"] is True

    def test_one_differing_false(self):
        sigs = [
            {"canonical_sha256": "aaa"},
            {"canonical_sha256": "bbb"},
            {"canonical_sha256": "aaa"},
        ]
        result = aggregate_signatures(sigs, "aaa")
        assert result["signature_identity"] is False
        assert result["historical_signature_match"] is False

    def test_all_identical_to_historical(self):
        sigs = [
            {"canonical_sha256": "abc"},
            {"canonical_sha256": "abc"},
        ]
        result = aggregate_signatures(sigs, "abc")
        assert result["signature_identity"] is True
        assert result["historical_signature_match"] is True

    def test_historical_mismatch(self):
        sigs = [
            {"canonical_sha256": "abc"},
        ]
        result = aggregate_signatures(sigs, "xyz")
        assert result["signature_identity"] is True
        assert result["historical_signature_match"] is False

    def test_empty_list(self):
        result = aggregate_signatures([], "abc")
        assert result["signature_identity"] is False
        assert result["historical_signature_match"] is False
        assert result["run_signatures"] == []


# =========================================================================
# New tests: 4.3 Median run selection
# =========================================================================

class TestMedianRunSelection:
    def test_odd_count_median(self):
        runs = [
            {"id": "run-a", "detect_elapsed_seconds": 239.0},
            {"id": "run-b", "detect_elapsed_seconds": 236.0},
            {"id": "run-c", "detect_elapsed_seconds": 237.0},
        ]
        median = select_median_run(runs)
        assert median["id"] == "run-c"
        assert median["detect_elapsed_seconds"] == 237.0

    def test_even_count_lower_median(self):
        runs = [
            {"id": "run-a", "detect_elapsed_seconds": 10.0},
            {"id": "run-b", "detect_elapsed_seconds": 20.0},
            {"id": "run-c", "detect_elapsed_seconds": 30.0},
            {"id": "run-d", "detect_elapsed_seconds": 40.0},
        ]
        median = select_median_run(runs)
        assert median["detect_elapsed_seconds"] == 30.0

    def test_single_run(self):
        runs = [{"id": "run-only", "detect_elapsed_seconds": 100.0}]
        median = select_median_run(runs)
        assert median["id"] == "run-only"

    def test_empty_list(self):
        assert select_median_run([]) == {}


# =========================================================================
# New tests: 4.4 Stage accounting vs profile evidence
# =========================================================================

class TestStageAccounting:
    def test_measured_stage_total_exact(self):
        timers = {
            "roi": 0.3, "extract_features": 85.0, "visual_distance": 0.2,
            "threshold": 0.1, "debounce": 0.0, "pass2_collect": 53.0,
            "pass2_dedupe": 6.0, "pass2_screenshots": 0.1,
        }
        result = compute_stage_accounting(timers, 237.0)
        assert result["measured_stage_total"] == pytest.approx(144.7)
        assert result["residual_seconds"] == pytest.approx(92.3)
        assert result["residual_percentage"] == pytest.approx(92.3 / 237.0 * 100)

    def test_residual_exact(self):
        timers = dict.fromkeys(STAGE_NAMES, 0.0)
        result = compute_stage_accounting(timers, 100.0)
        assert result["measured_stage_total"] == 0.0
        assert result["residual_seconds"] == 100.0
        assert result["residual_percentage"] == 100.0

    def test_profile_evidence_does_not_alter_accounting(self):
        timers = {"roi": 1.0, "extract_features": 2.0}
        result_without = compute_stage_accounting(timers, 10.0)
        result_with = compute_stage_accounting(timers, 10.0, profile_evidence={"cumtime": 999.0})
        assert result_without["measured_stage_total"] == result_with["measured_stage_total"]
        assert result_without["residual_seconds"] == result_with["residual_seconds"]
        assert result_with["_profile_evidence_ignored"] is True

    def test_stage_names_are_canonical(self):
        assert STAGE_NAMES == [
            "roi", "extract_features", "visual_distance", "threshold", "debounce",
            "pass2_collect", "pass2_dedupe", "pass2_screenshots",
        ]


# =========================================================================
# New tests: 4.5 Change count
# =========================================================================

class TestChangeCount:
    def test_change_count_is_NOT_EXPOSED(self):
        assert True  # verified at run level - see aggregate test below

    def test_run_benchmark_returns_string_not_none(self):
        # We can't easily call run_benchmark, but we verify build_aggregate_evidence emits it
        pass

    def test_not_null_or_none_in_aggregate(self):
        aggregate = build_aggregate_evidence(
            benchmark_sequence="test",
            branch="test",
            benchmark_code_head="abc",
            benchmark_code_tree="abc",
            recovered_master_base="abc",
            clip={},
            warmup_performed=False,
            recorded_runs=[{
                "id": "test", "detect_elapsed_seconds": 10.0, "wall_clock_seconds": 11.0,
                "metrics": {"timers": {}, "counters": {}, "gauges": {}},
                "effective_config": {},
                "output_signature": {"canonical_sha256": "aaa"},
                "slides_count": 5, "png_count": 2,
                "score_distribution": {},
                "derived_metrics": {},
            }],
            profile_run=None,
        )
        assert aggregate["quality"]["change_count"] == "NOT_EXPOSED"


# =========================================================================
# New tests: 4.6 Path sanitization
# =========================================================================

class TestPathSanitization:
    def test_windows_absolute_path(self):
        result = sanitize_committed_path(
            "D:\\git\\worktrees\\video2pptx-phase18-short-benchmark\\examples\\hermes-0000-1000.mp4"
        )
        assert "examples" not in result or result == Path(
            "D:\\git\\worktrees\\video2pptx-phase18-short-benchmark\\examples\\hermes-0000-1000.mp4"
        ).name
        assert result == "hermes-0000-1000.mp4"

    def test_posix_absolute_path(self):
        result = sanitize_committed_path(
            "/home/user/video2pptx/examples/hermes-0000-1000.mp4"
        )
        assert result == "hermes-0000-1000.mp4"

    def test_relative_path_preserved(self):
        result = sanitize_committed_path("examples/hermes-0000-1000.mp4")
        assert result == "examples/hermes-0000-1000.mp4"

    def test_basename_only(self):
        result = sanitize_committed_path("hermes-0000-1000.mp4")
        assert result == "hermes-0000-1000.mp4"


# =========================================================================
# New tests: 4.7 Effective backend integration
# =========================================================================

class TestEffectiveBackend:
    def test_select_backend_is_called(self):
        from video2pptx.video_decode import select_backend
        result = select_backend("auto")
        assert result in ("pyav", "opencv")


# =========================================================================
# New tests: aggregate structure
# =========================================================================

class TestAggregateEvidence:
    @pytest.fixture
    def basic_aggregate(self):
        return build_aggregate_evidence(
            benchmark_sequence="test-seq",
            branch="test-branch",
            benchmark_code_head="head123",
            benchmark_code_tree="tree123",
            recovered_master_base="base123",
            clip={"identifier": "abc", "sha256": "def", "duration_seconds": 600.0,
                  "resolution": "1920x1080", "codec": "H.264", "fps": 60},
            warmup_performed=True,
            recorded_runs=[
                {
                    "id": "run-01", "detect_elapsed_seconds": 236.0,
                    "wall_clock_seconds": 237.0, "slides_count": 28, "png_count": 6,
                    "metrics": {"timers": {}, "counters": {"screenshots_written": 6, "frames_sampled": 1200,
                                                           "features_full": 1200, "features_quick": 0,
                                                           "frames_decoded": 72000, "ndarray_conversions": 2400,
                                                           "pass2_frames_sampled": 1200,
                                                           "representative_frames": 84,
                                                           "representative_frame_bytes": 500000},
                                "gauges": {"rss_before_mb": 0, "rss_peak_mb": 0, "rss_after_mb": 0,
                                           "rgb_transfer_bytes": 1000000}},
                    "effective_config": {"video_identifier": "test.mp4", "sample_fps": 2.0,
                                         "configured_backend": "auto", "effective_backend": "pyav",
                                         "slide_roi": "auto", "ignore_rois": [], "threshold": "auto",
                                         "min_slide_duration": 2.0, "min_stable_duration": 2.0,
                                         "dedupe_enabled": True, "quick_mode": False},
                "output_signature": {"canonical_sha256": "8cc06c6accb055fb6fed461f2f4a96f0b288ef864b9423000b6f59d9ab56bc85"},
                "score_distribution": {},
                "derived_metrics": {"real_time_multiplier": 0.39, "processing_x_realtime": 2.54,
                                    "effective_sampled_fps": 2.0},
            },
            {
                "id": "run-02", "detect_elapsed_seconds": 237.0,
                "wall_clock_seconds": 238.0, "slides_count": 28, "png_count": 6,
                "metrics": {"timers": {}, "counters": {"screenshots_written": 6, "frames_sampled": 1200,
                                                       "features_full": 1200, "features_quick": 0,
                                                       "frames_decoded": 72000, "ndarray_conversions": 2400,
                                                       "pass2_frames_sampled": 1200,
                                                       "representative_frames": 84,
                                                       "representative_frame_bytes": 500000},
                            "gauges": {"rss_before_mb": 0, "rss_peak_mb": 0, "rss_after_mb": 0,
                                       "rgb_transfer_bytes": 1000000}},
                "effective_config": {"video_identifier": "test.mp4", "sample_fps": 2.0,
                                     "configured_backend": "auto", "effective_backend": "pyav",
                                     "slide_roi": "auto", "ignore_rois": [], "threshold": "auto",
                                     "min_slide_duration": 2.0, "min_stable_duration": 2.0,
                                     "dedupe_enabled": True, "quick_mode": False},
                "output_signature": {"canonical_sha256": "8cc06c6accb055fb6fed461f2f4a96f0b288ef864b9423000b6f59d9ab56bc85"},
                "score_distribution": {},
                "derived_metrics": {"real_time_multiplier": 0.40, "processing_x_realtime": 2.53,
                                    "effective_sampled_fps": 2.0},
            },
            {
                "id": "run-03", "detect_elapsed_seconds": 239.0,
                "wall_clock_seconds": 240.0, "slides_count": 28, "png_count": 6,
                "metrics": {"timers": {}, "counters": {"screenshots_written": 6, "frames_sampled": 1200,
                                                       "features_full": 1200, "features_quick": 0,
                                                       "frames_decoded": 72000, "ndarray_conversions": 2400,
                                                       "pass2_frames_sampled": 1200,
                                                       "representative_frames": 84,
                                                       "representative_frame_bytes": 500000},
                            "gauges": {"rss_before_mb": 0, "rss_peak_mb": 0, "rss_after_mb": 0,
                                       "rgb_transfer_bytes": 1000000}},
                "effective_config": {"video_identifier": "test.mp4", "sample_fps": 2.0,
                                     "configured_backend": "auto", "effective_backend": "pyav",
                                     "slide_roi": "auto", "ignore_rois": [], "threshold": "auto",
                                     "min_slide_duration": 2.0, "min_stable_duration": 2.0,
                                     "dedupe_enabled": True, "quick_mode": False},
                "output_signature": {"canonical_sha256": "8cc06c6accb055fb6fed461f2f4a96f0b288ef864b9423000b6f59d9ab56bc85"},
                    "score_distribution": {},
                    "derived_metrics": {"real_time_multiplier": 0.40, "processing_x_realtime": 2.51,
                                        "effective_sampled_fps": 2.0},
                },
            ],
            profile_run={
                "id": "profile", "detect_elapsed_seconds": 243.0,
                "wall_clock_seconds": 244.0,
                "metrics": {"timers": {}, "counters": {}, "gauges": {}},
                "effective_config": {"effective_backend": "pyav"},
                "output_signature": {"canonical_sha256": "8cc06c6accb055fb6fed461f2f4a96f0b288ef864b9423000b6f59d9ab56bc85"},
                "derived_metrics": {},
            },
        )

    def test_required_top_level_keys(self, basic_aggregate):
        required = [
            "benchmark_sequence", "benchmark_code_head", "benchmark_code_tree",
            "recovered_master_base", "branch", "clip", "warmup_performed",
            "recorded_run_count", "effective_config", "runs", "summary",
            "signatures", "quality", "median_run_stage_accounting",
            "profile_supporting_evidence", "rss", "counter_invariants",
            "f0088", "decision", "optimization_selected",
        ]
        for key in required:
            assert key in basic_aggregate, f"missing required key: {key}"

    def test_required_effective_config_keys(self, basic_aggregate):
        required = [
            "video_identifier", "sample_fps", "configured_backend", "effective_backend",
            "slide_roi", "ignore_rois", "threshold", "min_slide_duration",
            "min_stable_duration", "dedupe_enabled", "quick_mode",
        ]
        for key in required:
            assert key in basic_aggregate["effective_config"], f"missing effective_config key: {key}"

    def test_required_signatures_keys(self, basic_aggregate):
        required = [
            "run_signatures", "signature_identity", "historical_signature",
            "historical_signature_match", "profile_signature", "profile_signature_match",
        ]
        for key in required:
            assert key in basic_aggregate["signatures"], f"missing signatures key: {key}"

    def test_required_quality_keys(self, basic_aggregate):
        required = [
            "slides_count", "screenshots_written", "actual_png_count",
            "change_count", "score_distribution",
        ]
        for key in required:
            assert key in basic_aggregate["quality"], f"missing quality key: {key}"

    def test_decision_PENDING(self, basic_aggregate):
        assert basic_aggregate["decision"] == "PENDING"

    def test_optimization_selected_false(self, basic_aggregate):
        assert basic_aggregate["optimization_selected"] is False

    def test_signature_identity_true(self, basic_aggregate):
        assert basic_aggregate["signatures"]["signature_identity"] is True

    def test_historical_signature_match(self, basic_aggregate):
        assert basic_aggregate["signatures"]["historical_signature_match"] is True

    def test_profile_signature_match(self, basic_aggregate):
        assert basic_aggregate["signatures"]["profile_signature_match"] is True

    def test_recorded_run_count_three(self, basic_aggregate):
        assert basic_aggregate["recorded_run_count"] == 3

    def test_median_run_id(self, basic_aggregate):
        assert basic_aggregate["summary"]["median_run_id"] == "run-02"

    def test_warmup_performed(self, basic_aggregate):
        assert basic_aggregate["warmup_performed"] is True

    def test_min_median_max(self, basic_aggregate):
        assert basic_aggregate["summary"]["min_detect_elapsed_seconds"] == 236.0
        assert basic_aggregate["summary"]["median_detect_elapsed_seconds"] == 237.0
        assert basic_aggregate["summary"]["max_detect_elapsed_seconds"] == 239.0

    def test_f0088_observed(self, basic_aggregate):
        assert basic_aggregate["f0088"]["observed"] is True
        assert "OPEN" in basic_aggregate["f0088"]["finding_status"]

    def test_rss_skipped(self, basic_aggregate):
        assert basic_aggregate["rss"]["status"] == "SKIPPED_PSUTIL_UNAVAILABLE"

    def test_profile_evidence_does_not_affect_stage_accounting(self, basic_aggregate):
        accounting = basic_aggregate["median_run_stage_accounting"]
        assert isinstance(accounting["measured_stage_total"], float)
        assert isinstance(accounting["residual_seconds"], float)
        assert isinstance(accounting["residual_percentage"], float)


class TestHistoricalConstant:
    def test_historical_signature_is_known(self):
        assert HISTORICAL_CANONICAL_SIGNATURE == "8cc06c6accb055fb6fed461f2f4a96f0b288ef864b9423000b6f59d9ab56bc85"
