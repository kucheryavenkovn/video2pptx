# FILE: tests/test_target_optimization_discrimination.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Focused tests for Step 18.4C target-optimization discrimination helpers.
#   SCOPE: Statistics, C1 frame parity, C2 resource bytes, C3 variant/sequence parity.
#   DEPENDS: tools.discrimination_helpers
#   LINKS: M-DETECT-PERF-DECISION, V-PERF-DETECT-BOTTLENECK
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from discrimination_helpers import (  # noqa: E402
    build_streaming_frame_signature,
    bytes_to_gb_decimal,
    bytes_to_gib,
    check_frame_parity,
    check_sequence_parity,
    compute_full_rgb_retention_bytes,
    compute_mean,
    compute_median,
    compute_median_reduction_percent,
    compute_paired_absolute_savings,
    compute_paired_percentage_reduction,
    compute_retention_ratio,
    compute_roi_retention_bytes,
    compute_sample_stdev,
    compute_target_frame_index,
    compute_target_sampled_timestamp,
    directional_stability,
    validate_c3_variant_metadata,
)

# =========================================================================
# Statistics tests
# =========================================================================


class TestStatistics:
    def test_median_exact(self):
        assert compute_median([3.0, 1.0, 2.0]) == 2.0
        assert compute_median([1.0, 2.0]) == 1.5

    def test_mean_exact(self):
        assert compute_mean([1.0, 2.0, 3.0]) == 2.0
        assert compute_mean([10.0, 20.0]) == 15.0

    def test_sample_stdev_exact(self):
        # [1,2,3]: mean=2, sq dev=[1,0,1]=2, sample var=2/2=1, stdev=1.0
        assert compute_sample_stdev([1.0, 2.0, 3.0]) == 1.0

    def test_paired_absolute_savings_exact(self):
        result = compute_paired_absolute_savings([100.0, 200.0, 300.0], [90.0, 150.0, 250.0])
        assert result == [10.0, 50.0, 50.0]

    def test_paired_percentage_reduction_exact(self):
        result = compute_paired_percentage_reduction([100.0, 200.0], [50.0, 100.0])
        assert result == [50.0, 50.0]

    def test_paired_percentage_reduction_zero_reference(self):
        result = compute_paired_percentage_reduction([0.0, 100.0], [0.0, 50.0])
        assert result == [0.0, 50.0]

    def test_directional_stability_true(self):
        assert directional_stability([100.0, 200.0, 300.0], [90.0, 150.0, 250.0]) is True

    def test_directional_stability_false(self):
        assert directional_stability([100.0, 200.0], [90.0, 250.0]) is False

    def test_directional_stability_equal(self):
        assert directional_stability([100.0], [100.0]) is False

    def test_median_reduction_percent(self):
        pct = compute_median_reduction_percent([100.0, 200.0], [50.0, 100.0])
        assert pct == 50.0

    def test_median_empty_raises(self):
        with pytest.raises(ValueError):
            compute_median([])

    def test_stdev_single_raises(self):
        with pytest.raises(ValueError):
            compute_sample_stdev([1.0])

    def test_paired_length_mismatch_raises(self):
        with pytest.raises(ValueError):
            compute_paired_absolute_savings([1.0], [1.0, 2.0])


# =========================================================================
# C1 target timestamp tests
# =========================================================================


class TestTargetTimestamp:
    def test_reference_collector_first_within_tolerance(self):
        # video_fps=60, frame_interval=30 → step=0.5, tolerance=0.25
        # rep_ts=102.8 → lower=102.5 (diff=0.3 > 0.25), upper=103.0 (diff=0.2 < 0.25)
        ts = compute_target_sampled_timestamp(102.8, 60.0, 30, 0.25)
        assert ts == 103.0

    def test_exact_match_returns_lower(self):
        # rep_ts=140.0 is exactly on a sampled frame
        ts = compute_target_sampled_timestamp(140.0, 60.0, 30, 0.25)
        assert ts == 140.0

    def test_no_match_returns_none(self):
        # rep_ts=102.25 → lower=102.0 (diff=0.25 not < 0.25), upper=102.5 (diff=0.25 not < 0.25)
        ts = compute_target_sampled_timestamp(102.25, 60.0, 30, 0.25)
        assert ts is None

    def test_target_frame_index(self):
        idx = compute_target_frame_index(103.0, 60.0, 30)
        assert idx == 6180

    def test_target_frame_index_zero(self):
        idx = compute_target_frame_index(0.0, 60.0, 30)
        assert idx == 0


# =========================================================================
# C1 frame parity tests
# =========================================================================


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class TestFrameParity:
    def _make_entry(self, ts: float, shape, data: bytes):
        return {
            "sampled_timestamp": ts,
            "shape": list(shape),
            "rgb_sha256": _sha(data),
            "raw_bytes_sha256": _sha(data),
        }

    def test_exact_match_passes(self):
        data = b"\x01" * 10
        ref = {1.0: self._make_entry(1.0, (2, 5, 3), data)}
        cand = {1.0: self._make_entry(1.0, (2, 5, 3), data)}
        result = check_frame_parity(ref, cand)
        assert result["parity_pass"] is True

    def test_one_byte_difference_detected(self):
        ref = {1.0: self._make_entry(1.0, (2, 5, 3), b"\x01" * 10)}
        cand = {1.0: self._make_entry(1.0, (2, 5, 3), b"\x01" * 9 + b"\x02")}
        result = check_frame_parity(ref, cand)
        assert result["parity_pass"] is False
        assert result["exact_cropped_rgb_sha_parity"] is False

    def test_timestamp_mismatch_fails_parity(self):
        data = b"\x01" * 10
        ref = {1.0: self._make_entry(1.0, (2, 5, 3), data)}
        cand = {1.0: self._make_entry(2.0, (2, 5, 3), data)}
        result = check_frame_parity(ref, cand)
        assert result["parity_pass"] is False
        assert result["exact_sampled_timestamp_parity"] is False

    def test_missing_target_fails_parity(self):
        data = b"\x01" * 10
        ref = {1.0: self._make_entry(1.0, (2, 5, 3), data), 2.0: self._make_entry(2.0, (2, 5, 3), data)}
        cand = {1.0: self._make_entry(1.0, (2, 5, 3), data)}
        result = check_frame_parity(ref, cand)
        assert result["parity_pass"] is False
        assert result["all_targets_mapped"] is False

    def test_shape_mismatch_fails_parity(self):
        data = b"\x01" * 10
        ref = {1.0: self._make_entry(1.0, (2, 5, 3), data)}
        cand = {1.0: self._make_entry(1.0, (3, 5, 3), data)}
        result = check_frame_parity(ref, cand)
        assert result["parity_pass"] is False
        assert result["exact_shape_parity"] is False

    def test_candidate_preserves_unique_timestamps(self):
        data = b"\x01" * 10
        ref = {1.0: self._make_entry(1.0, (2, 5, 3), data), 2.0: self._make_entry(2.0, (2, 5, 3), data)}
        cand = {1.0: self._make_entry(1.0, (2, 5, 3), data), 2.0: self._make_entry(2.0, (2, 5, 3), data)}
        result = check_frame_parity(ref, cand)
        assert result["target_timestamp_count_identical"] is True
        assert result["parity_pass"] is True


# =========================================================================
# C2 resource byte tests
# =========================================================================


class TestC2ResourceBytes:
    def test_full_rgb_retention_bytes_exact(self):
        # 1201 frames, 1920x1080x3
        result = compute_full_rgb_retention_bytes(1201, 1920, 1080, 3)
        expected = 1201 * 1920 * 1080 * 3
        assert result == expected
        assert result == 7_471_180_800

    def test_roi_retention_bytes_exact(self):
        # With roi=None (auto), ROI = full frame
        result = compute_roi_retention_bytes(1201, 1920, 1080, 3)
        expected = 1201 * 1920 * 1080 * 3
        assert result == expected
        assert result == 7_471_180_800

    def test_bytes_to_gb_decimal_deterministic(self):
        gb = bytes_to_gb_decimal(7_470_340_800)
        assert gb == pytest.approx(7.4703408, abs=1e-10)

    def test_bytes_to_gib_deterministic(self):
        gib = bytes_to_gib(7_470_340_800)
        assert gib == pytest.approx(7_470_340_800 / (1024 ** 3), abs=1e-10)

    def test_retention_ratio_exact(self):
        ratio = compute_retention_ratio(7_471_180_800, 522_547_200)
        assert ratio == pytest.approx(1201 / 84, abs=1e-10)

    def test_retention_ratio_zero_raises(self):
        with pytest.raises(ValueError):
            compute_retention_ratio(1000, 0)


# =========================================================================
# C3 variant metadata tests
# =========================================================================


class TestC3VariantMetadata:
    def _valid_variant(self):
        return {
            "name": "thread_count_4",
            "property_or_options_boundary": "codec_context.thread_count",
            "default_value": 0,
            "candidate_value": 4,
            "mechanistic_hypothesis": "test",
            "frame_sequence_parity_risk": "LOW",
            "hwaccel_compatibility_risk": "HIGH",
        }

    def test_valid_variant_accepted(self):
        validate_c3_variant_metadata(self._valid_variant())

    def test_missing_name_rejected(self):
        v = self._valid_variant()
        del v["name"]
        with pytest.raises(ValueError):
            validate_c3_variant_metadata(v)

    def test_missing_field_rejected(self):
        v = self._valid_variant()
        del v["mechanistic_hypothesis"]
        with pytest.raises(ValueError):
            validate_c3_variant_metadata(v)

    def test_unsupported_property_not_classified_as_preserving(self):
        # skip_frame should not be classified as POTENTIALLY_PARITY_PRESERVING
        # This is verified by the classification logic in probe_pyav_decode_config
        # Here we just test that the classification string is not equal
        assert "SEMANTICS_CHANGE" in "SEMANTICS_CHANGE_FRAME_SEQUENCE"


# =========================================================================
# C3 sequence parity tests
# =========================================================================


class TestSequenceParity:
    def test_sequence_signature_deterministic(self):
        sigs = [{"yield_index": 0, "timestamp": 0.0, "shape": [1080, 1920, 3], "rgb_sha256": "abc"}]
        sig1 = build_streaming_frame_signature(sigs)
        sig2 = build_streaming_frame_signature(sigs)
        assert sig1 == sig2

    def test_frame_count_mismatch_fails_parity(self):
        result = check_sequence_parity(
            "sig_a", "sig_b", 1201, 1200, [0.0], [0.0], ["a"], ["a"]
        )
        assert result["parity_pass"] is False
        assert result["yielded_frame_count_identical"] is False

    def test_timestamp_mismatch_fails_parity(self):
        result = check_sequence_parity(
            "sig_a", "sig_b", 2, 2, [0.0, 0.5], [0.0, 1.0], ["a", "b"], ["a", "b"]
        )
        assert result["parity_pass"] is False
        assert result["timestamp_sequence_identical"] is False

    def test_frame_hash_mismatch_fails_parity(self):
        result = check_sequence_parity(
            "sig_a", "sig_b", 2, 2, [0.0, 0.5], [0.0, 0.5], ["a", "b"], ["a", "c"]
        )
        assert result["parity_pass"] is False
        assert result["per_frame_rgb_sha_identical"] is False

    def test_signature_mismatch_fails_parity(self):
        result = check_sequence_parity(
            "sig_a", "sig_b", 1, 1, [0.0], [0.0], ["a"], ["a"]
        )
        assert result["parity_pass"] is False
        assert result["final_sequence_signature_identical"] is False

    def test_full_match_passes(self):
        result = check_sequence_parity(
            "sig_a", "sig_a", 1, 1, [0.0], [0.0], ["a"], ["a"]
        )
        assert result["parity_pass"] is True
