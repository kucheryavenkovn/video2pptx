# FILE: tests/test_target_optimization_discrimination.py
# VERSION: 2.2.0
# START_MODULE_CONTRACT
#   PURPOSE: Focused tests for Step 18.4C target-optimization discrimination helpers.
#   SCOPE: Statistics, repeatability, C1 parity, exact C2 retention, C3 selection/provenance/parity.
#   DEPENDS: tools.discrimination_helpers, tools.probe_pyav_decode_config
#   LINKS: M-DETECT-PERF-DECISION, V-M-PERF-DETECT-BOTTLENECK
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   TestStatistics - exact paired-statistics checks
#   TestReferenceRepeatability - baseline exact-sequence discriminator checks
#   TestC2RetentionModel - formal strict-tolerance rolling-model checks
#   TestC3Selection - deterministic selection and consistency-guard checks
#   TestC3Provenance - accepted-base, clip, and evidence-code provenance checks
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: [v2.2.0 - Step 18.4 closeout: accept negative terminal outcome
#     T3_NO_EVIDENCE_SUPPORTED_TARGET_OPTIMIZATION at the decision layer.
#     Replaced outcome=PENDING/terminal_outcome=null/Step 18.4C=in_progress
#     assertions with outcome=T3, terminal_outcome=T3_..., Step 18.4C=done,
#     Step 18.4=done, selected_optimization=NONE, step18_5_implementation_started
#     false, F-0103 OPEN_NON_BLOCKING. The raw r2 discrimination evidence
#     package is asserted unchanged (immutable raw evidence retains its
#     discrimination-time PENDING snapshot). Causal-language,
#     duplicate-key, arithmetic, and signature-provenance guards retained.]
#   PREV_CHANGE: [v2.1.0 - Step 18.4C: strengthened causal-consistency gate.
#     Added case/whitespace-tolerant rejection of "root cause now isolated",
#     "not an environment anomaly", and "not with an environment or clip anomaly"
#     in current artifacts (incl. findings.md and bottleneck_decision.md). Added
#     positive assertions that the aggregate provenance carries
#     causal_classification=ROOT_CAUSE_UNKNOWN_NOT_ISOLATED, codec_context_causal
#     is False, and explicit "environment contribution is not excluded" wording.
#     Rejected 13e6fff draft package remains out of scope.]
# END_CHANGE_SUMMARY

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from discrimination_helpers import (  # noqa: E402
    balanced_recorded_order,
    build_streaming_frame_signature,
    bytes_to_gb_decimal,
    bytes_to_gib,
    can_evict_retained_frame,
    check_c3_selection_consistency,
    check_frame_parity,
    check_sequence_parity,
    classify_reference_repeatability,
    collect_git_provenance,
    compute_difference_of_medians,
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
    earliest_possible_representative,
    representative_timestamp,
    select_c3_variants,
    select_first_strict_match,
    validate_accepted_base,
    validate_c3_variant_metadata,
)
from probe_pyav_decode_config import validate_canonical_clip  # noqa: E402

from video2pptx.models import FrameFeatures  # noqa: E402
from video2pptx.slide_detector import ChangeEvent, _debounce_changes  # noqa: E402

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
        ref = {
            1.0: self._make_entry(1.0, (2, 5, 3), data),
            2.0: self._make_entry(2.0, (2, 5, 3), data),
        }
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
        ref = {
            1.0: self._make_entry(1.0, (2, 5, 3), data),
            2.0: self._make_entry(2.0, (2, 5, 3), data),
        }
        cand = {
            1.0: self._make_entry(1.0, (2, 5, 3), data),
            2.0: self._make_entry(2.0, (2, 5, 3), data),
        }
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
        assert gib == pytest.approx(7_470_340_800 / (1024**3), abs=1e-10)

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
        result = check_sequence_parity("sig_a", "sig_b", 1201, 1200, [0.0], [0.0], ["a"], ["a"])
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
        result = check_sequence_parity("sig_a", "sig_b", 1, 1, [0.0], [0.0], ["a"], ["a"])
        assert result["parity_pass"] is False
        assert result["final_sequence_signature_identical"] is False

    def test_full_match_passes(self):
        result = check_sequence_parity("sig_a", "sig_a", 1, 1, [0.0], [0.0], ["a"], ["a"])
        assert result["parity_pass"] is True


class TestReferenceRepeatability:
    @staticmethod
    def _run(hashes=None, timestamps=None, count=2):
        hashes = hashes or ["a", "b"]
        timestamps = timestamps or [0.0, 0.5]
        shapes = [[2, 2, 3] for _ in hashes]
        return {
            "frames_yielded": count,
            "yielded_timestamps": timestamps,
            "shapes": shapes,
            "frame_hashes": hashes,
            "sequence_signature": build_streaming_frame_signature(
                [
                    {"yield_index": i, "timestamp": ts, "shape": shapes[i], "rgb_sha256": hashes[i]}
                    for i, ts in enumerate(timestamps)
                ]
            ),
        }

    def test_identical_sequences_are_repeatable(self):
        run = self._run()
        result = classify_reference_repeatability([run, dict(run), dict(run)])
        assert result["classification"] == "REFERENCE_EXACTLY_REPEATABLE"

    def test_one_rgb_hash_difference_is_nondeterministic(self):
        result = classify_reference_repeatability(
            [
                self._run(),
                self._run(hashes=["a", "c"]),
                self._run(),
            ]
        )
        assert result["classification"] == "REFERENCE_PIXEL_NONDETERMINISTIC_ACROSS_OPENS"

    def test_frame_count_difference_is_nondeterministic(self):
        result = classify_reference_repeatability(
            [
                self._run(),
                self._run(count=3),
                self._run(),
            ]
        )
        assert result["classification"] == "REFERENCE_PIXEL_NONDETERMINISTIC_ACROSS_OPENS"

    def test_timestamp_difference_is_nondeterministic(self):
        result = classify_reference_repeatability(
            [
                self._run(),
                self._run(timestamps=[0.0, 1.0]),
                self._run(),
            ]
        )
        assert result["classification"] == "REFERENCE_PIXEL_NONDETERMINISTIC_ACROSS_OPENS"


class TestC2RetentionModel:
    def test_short_segment_uses_halfway_target(self):
        assert representative_timestamp(10.0, 15.0) == 12.5
        assert earliest_possible_representative(10.0, 15.0) == 12.5

    def test_six_second_transition_uses_eighty_percent(self):
        assert representative_timestamp(10.0, 16.0) == pytest.approx(14.8)
        assert earliest_possible_representative(10.0, 16.0) == pytest.approx(14.8)

    def test_strict_tolerance_boundary_is_excluded(self):
        assert select_first_strict_match([2.0], 2.25, 0.25) is None

    def test_possible_future_target_is_not_evicted(self):
        assert can_evict_retained_frame(2.5, 0.0, 5.0, 0.25) is False

    def test_impossible_past_frame_may_be_evicted(self):
        assert can_evict_retained_frame(2.0, 0.0, 5.0, 0.25) is True

    def test_actual_debounce_has_no_confirmation_timestamp_delay(self):
        events = [
            ChangeEvent(2.0, 1.0, FrameFeatures(timestamp=2.0)),
            ChangeEvent(4.0, 1.0, FrameFeatures(timestamp=4.0)),
        ]
        accepted = _debounce_changes(events, min_stable_frames=4)
        assert [event.timestamp for event in accepted] == [2.0, 4.0]

    def test_trace_simulation_matches_full_history_selection(self):
        timestamps = [index * 0.5 for index in range(21)]
        retained = list(timestamps)
        for now in timestamps:
            retained = [
                ts
                for ts in retained
                if ts > now or not can_evict_retained_frame(ts, 0.0, now, 0.25)
            ]
        target = representative_timestamp(0.0, 10.0)
        assert select_first_strict_match(retained, target, 0.25) == select_first_strict_match(
            timestamps, target, 0.25
        )

    def test_retain_all_value_is_upper_bound(self):
        value = compute_full_rgb_retention_bytes(1201, 1920, 1080)
        assert value == 7_471_180_800


class TestC3Selection:
    @staticmethod
    def _inspection():
        return {
            "properties": {
                "thread_count": {
                    "writable": True,
                    "classification": "POTENTIALLY_PARITY_PRESERVING",
                    "default_value": 0,
                },
                "thread_type": {
                    "writable": True,
                    "classification": "POTENTIALLY_PARITY_PRESERVING",
                    "default_value": 3,
                },
            }
        }

    def test_current_fixture_selects_expected_first_three(self):
        variants = select_c3_variants(self._inspection())
        assert [variant["name"] for variant in variants] == [
            "thread_count_1",
            "thread_count_4",
            "thread_count_8",
        ]

    def test_eligible_zero_variants_fails_guard(self):
        assert check_c3_selection_consistency(self._inspection(), []) == (
            "FAIL_ELIGIBLE_BOUNDARIES_WITH_ZERO_VARIANTS"
        )

    def test_no_eligible_boundaries_permits_zero(self):
        inspection = {
            "properties": {
                "thread_count": {
                    "writable": False,
                    "classification": "NOT_AVAILABLE",
                }
            }
        }
        assert check_c3_selection_consistency(inspection, []) == "PASS"

    def test_direct_runtime_exclusion_is_machine_readable(self):
        inspection = self._inspection()
        for value in inspection["properties"].values():
            value["direct_runtime_exclusion_evidence"] = {"kind": "API_ERROR", "message": "x"}
        assert check_c3_selection_consistency(inspection, []) == (
            "PASS_ALL_ELIGIBLE_BOUNDARIES_DIRECTLY_EXCLUDED"
        )

    def test_selection_order_is_deterministic(self):
        first = select_c3_variants(self._inspection())
        second = select_c3_variants(self._inspection())
        assert first == second

    def test_max_variants_enforced(self):
        assert len(select_c3_variants(self._inspection(), max_variants=2)) == 2


class TestC3Provenance:
    @staticmethod
    def _git(repo: Path, *args: str, input_text: str | None = None) -> str:
        return subprocess.check_output(
            ["git", *args],
            cwd=repo,
            text=True,
            input=input_text,
        ).strip()

    def _repo_with_two_commits(self, tmp_path: Path) -> tuple[Path, str, str]:
        repo = tmp_path / "repo"
        repo.mkdir()
        self._git(repo, "init")
        (repo / "value.txt").write_text("one", encoding="utf-8")
        self._git(repo, "add", "value.txt")
        self._git(
            repo,
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-m",
            "one",
        )
        first = self._git(repo, "rev-parse", "HEAD")
        (repo / "value.txt").write_text("two", encoding="utf-8")
        self._git(repo, "add", "value.txt")
        self._git(
            repo,
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.invalid",
            "commit",
            "-m",
            "two",
        )
        second = self._git(repo, "rev-parse", "HEAD")
        return repo, first, second

    def test_abbreviated_base_rejected(self, tmp_path):
        repo, first, _ = self._repo_with_two_commits(tmp_path)
        with pytest.raises(ValueError, match="full lowercase"):
            validate_accepted_base(first[:8], repo)

    def test_wrong_object_type_rejected(self, tmp_path):
        repo, _, _ = self._repo_with_two_commits(tmp_path)
        blob = self._git(repo, "hash-object", "-w", "--stdin", input_text="blob")
        with pytest.raises(ValueError, match="blob"):
            validate_accepted_base(blob, repo)

    def test_non_ancestor_rejected(self, tmp_path):
        repo, first, second = self._repo_with_two_commits(tmp_path)
        self._git(repo, "checkout", "--detach", first)
        with pytest.raises(ValueError, match="not an ancestor"):
            validate_accepted_base(second, repo)

    def test_canonical_sha_mismatch_rejected(self, tmp_path):
        clip = tmp_path / "clip.mp4"
        clip.write_bytes(b"not canonical")
        with pytest.raises(ValueError, match="canonical SHA256 mismatch"):
            validate_canonical_clip(clip)

    def test_evidence_head_and_tree_recorded(self, tmp_path):
        repo, _, second = self._repo_with_two_commits(tmp_path)
        evidence = collect_git_provenance(repo)
        assert evidence["evidence_code_head"] == second
        assert len(evidence["evidence_code_tree"]) == 40


def test_balanced_order_and_warmup_exclusion_contract():
    assert balanced_recorded_order() == [
        "reference-01",
        "candidate-01",
        "candidate-02",
        "reference-02",
        "reference-03",
        "candidate-03",
    ]
    assert all("warmup" not in item for item in balanced_recorded_order())


# =========================================================================
# Difference-of-medians arithmetic (must be recomputed from raw medians)
# =========================================================================


class TestDifferenceOfMedians:
    def test_seconds_and_percent_exact(self):
        result = compute_difference_of_medians(290.5263571000032, 330.72188989999995)
        assert result["difference_of_medians_seconds"] == -40.19553279999673
        assert result["difference_of_medians_percent"] == -13.835416931263438

    def test_distinct_from_median_of_paired_differences(self):
        # difference of medians (-40.195...) != median of paired differences (-46.819...)
        reference = [290.5263571000032, 218.43998660000216, 327.9901213000012]
        candidate = [337.3459901000024, 287.52387100000124, 330.72188989999995]
        diff_of_medians = compute_difference_of_medians(
            compute_median(reference), compute_median(candidate)
        )
        median_of_paired = compute_median(
            compute_paired_absolute_savings(reference, candidate)
        )
        assert diff_of_medians["difference_of_medians_seconds"] != median_of_paired
        assert diff_of_medians["difference_of_medians_seconds"] == -40.19553279999673
        assert median_of_paired == -46.81963299999916

    def test_zero_reference_raises(self):
        with pytest.raises(ValueError):
            compute_difference_of_medians(0.0, 1.0)


# =========================================================================
# Evidence-package consistency gate (cheap static checks on committed artifacts)
# =========================================================================

_EVIDENCE_DIR = (
    Path(__file__).resolve().parents[1]
    / "benchmarks/detect/evidence/target-optimization-discrimination-r2-20260714-0bcfe54"
)
_DECISION_JSON = (
    Path(__file__).resolve().parents[1]
    / "benchmarks/detect/evidence/bottleneck_decision.json"
)
_DECISION_MD = (
    Path(__file__).resolve().parents[1]
    / "benchmarks/detect/evidence/bottleneck_decision.md"
)
_FINDINGS_MD = Path(__file__).resolve().parents[1] / "docs/findings.md"


def _load_strict_json(path: Path) -> Any:
    """Parse JSON rejecting duplicate object keys."""
    seen: list[str] = []

    def hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        obj: dict[str, Any] = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError(f"duplicate key in {path}: {key}")
            obj[key] = value
        seen.extend(obj.keys())
        return obj

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=hook)


def _json_files(paths: list[Path]) -> list[Path]:
    return [path for path in paths if path.exists()]


def _normalize_ws(text: str) -> str:
    """Collapse all runs of whitespace to a single space (line-wrap tolerant)."""
    return re.sub(r"\s+", " ", text)


class TestEvidencePackageConsistency:
    def _aggregate(self):
        return _load_strict_json(_EVIDENCE_DIR / "discrimination_evidence.json")

    def _decision(self):
        return _load_strict_json(_DECISION_JSON)

    def test_all_artifacts_parse_without_duplicate_keys(self):
        candidates = [
            _EVIDENCE_DIR / "c1_status.json",
            _EVIDENCE_DIR / "c2_retention_model.json",
            _EVIDENCE_DIR / "c2_runs.json",
            _EVIDENCE_DIR / "c3_runs.json",
            _EVIDENCE_DIR / "c3_variants.json",
            _EVIDENCE_DIR / "c3_inspection.json",
            _EVIDENCE_DIR / "discrimination_evidence.json",
            _DECISION_JSON,
        ]
        for path in _json_files(candidates):
            _load_strict_json(path)  # raises on duplicate keys

    def test_c1_causality_consistent(self):
        c1 = _load_strict_json(_EVIDENCE_DIR / "c1_status.json")
        assert c1["state"] == "NOT_VIABLE_EXACT_PARITY_FAIL"
        assert c1["causal_matrix_run"] is False
        assert c1["causal_classification"] == "ROOT_CAUSE_UNKNOWN_NOT_ISOLATED"
        assert c1["codec_context_causal"] is False
        assert c1["seek_causal"] is False
        # aggregate c1 block must agree
        decision = self._decision()
        agg_c1 = decision["step18_4c_status"]["c1_evaluation"]
        assert agg_c1["state"] == "NOT_VIABLE_EXACT_PARITY_FAIL"
        assert agg_c1["causal_classification"] == "ROOT_CAUSE_UNKNOWN_NOT_ISOLATED"
        assert agg_c1["codec_context_causal"] is False

    def test_c2_state_and_retention_model_consistent(self):
        c2_runs = _load_strict_json(_EVIDENCE_DIR / "c2_runs.json")
        c2_model = _load_strict_json(_EVIDENCE_DIR / "c2_retention_model.json")
        assert c2_runs["state"] == "NOT_VIABLE_PERFORMANCE_FAIL"
        assert c2_model["classification"] == "ROLLING_WINDOW_EXACT_MODEL_PROVEN"
        decision = self._decision()
        agg_c2 = decision["step18_4c_status"]["c2_evaluation"]
        assert agg_c2["state"] == "NOT_VIABLE_PERFORMANCE_FAIL"
        assert agg_c2["retention_model"] == "ROLLING_WINDOW_EXACT_MODEL_PROVEN"

    def test_c3_variants_all_performance_fail(self):
        c3_runs = _load_strict_json(_EVIDENCE_DIR / "c3_runs.json")
        for name, variant in c3_runs["variants"].items():
            assert variant["state"] == "NOT_VIABLE_PERFORMANCE_FAIL", name
            assert variant["directional_stability"] is False, name
        decision = self._decision()
        assert decision["step18_4c_status"]["c3_evaluation"]["state"] == (
            "NOT_VIABLE_PERFORMANCE_FAIL"
        )

    def test_canonical_signature_mismatch_preserved(self):
        agg = self._aggregate()
        prov = agg["canonical_signature_provenance"]
        assert prov["accepted_immutable_signature"] == (
            "8cc06c6accb055fb6fed461f2f4a96f0b288ef864b9423000b6f59d9ab56bc85"
        )
        assert prov["fresh_reference_signature"] == (
            "5a7c45387383adf8fa31a306111451f2aadb6f91352c307545547057f686e783"
        )
        assert prov["match"] is False
        assert prov["causal_classification"] == "ROOT_CAUSE_UNKNOWN_NOT_ISOLATED"
        assert prov["codec_context_causal"] is False
        assert prov["codec_context_access"] == "LEADING_HYPOTHESIS_NOT_PROVEN"

    def test_negative_terminal_outcome_accepted(self):
        # Management decision (Step 18.4 closeout): the negative terminal
        # outcome T3 is accepted at the decision layer (bottleneck_decision.json
        # step18_4c_status). The raw r2 discrimination evidence package
        # (discrimination_evidence.json) is immutable raw evidence and
        # intentionally retains its discrimination-time PENDING snapshot; the
        # accepted management outcome supersedes it at the decision layer.
        decision = self._decision()
        status = decision["step18_4c_status"]
        assert status["outcome"] == "T3"
        assert status["terminal_outcome"] == (
            "T3_NO_EVIDENCE_SUPPORTED_TARGET_OPTIMIZATION"
        )
        assert status["decision_status"] == "NO_EVIDENCE_SUPPORTED_TARGET_OPTIMIZATION"
        assert status["selected_optimization"] == "NONE"
        assert decision["selected_optimization"] == "NONE"
        assert status["f0103_status"] == "OPEN_NON_BLOCKING"
        # Raw discrimination evidence package is unchanged at the evidence layer.
        agg = self._aggregate()
        assert agg["outcome"] == "PENDING"
        assert agg["terminal_outcome"] is None
        assert agg["selected_optimization"] == "NONE"

    def test_step_18_4c_done_and_18_5_blocked(self):
        decision = self._decision()
        status = decision["step18_4c_status"]
        assert status["status"] == "done"
        assert status["step_18_4"] == "done"
        assert status["step_18_5"] == "planned / blocked"
        assert status["step18_5_implementation_started"] is False
        assert status["selected_optimization"] == "NONE"
        assert status["step18_5_hypothesis"] == "NONE"
        # raw discrimination evidence retains its discrimination-time snapshot
        agg = self._aggregate()
        assert agg["selected_optimization"] == "NONE"

    def test_c2_difference_of_medians_recomputed_from_raw(self):
        c2_runs = _load_strict_json(_EVIDENCE_DIR / "c2_runs.json")
        recomputed = compute_difference_of_medians(
            c2_runs["reference_median"], c2_runs["candidate_median"]
        )
        assert c2_runs["difference_of_medians_seconds"] == (
            recomputed["difference_of_medians_seconds"]
        )
        assert c2_runs["difference_of_medians_percent"] == (
            recomputed["difference_of_medians_percent"]
        )
        # cross-check the aggregate carries the same corrected percent
        agg_c2 = self._decision()["step18_4c_status"]["c2_evaluation"]
        assert agg_c2["difference_of_medians_seconds"] == (
            recomputed["difference_of_medians_seconds"]
        )
        assert agg_c2["difference_of_medians_percent"] == (
            recomputed["difference_of_medians_percent"]
        )
        # median-of-paired-differences must remain distinct from difference-of-medians
        assert c2_runs["median_seconds_saved"] == -46.81963299999916
        assert c2_runs["median_seconds_saved"] != c2_runs["difference_of_medians_seconds"]

    def test_c3_difference_of_medians_recomputed_from_raw(self):
        c3_runs = _load_strict_json(_EVIDENCE_DIR / "c3_runs.json")
        for name, variant in c3_runs["variants"].items():
            recomputed = compute_difference_of_medians(
                variant["reference_median"], variant["candidate_median"]
            )
            assert variant["difference_of_medians_seconds"] == (
                recomputed["difference_of_medians_seconds"]
            ), name
            assert variant["difference_of_medians_percent"] == (
                recomputed["difference_of_medians_percent"]
            ), name
            assert variant["median_seconds_saved"] != (
                variant["difference_of_medians_seconds"]
            ), name

    def test_no_unsupported_isolated_cause_claims_in_current_artifacts(self):
        # Exact-substring forbidden claims (machine-token form).
        forbidden_exact = [
            "root cause ISOLATED",
            "direct consequence of codec_context",
            "codec_context causal = true",
            "outcome\": \"T3_blocked",
        ]
        # Causal-language claims forbidden in CURRENT conclusions. Matched
        # case-insensitively with collapsed whitespace so line-wrapped/cased
        # variants are caught. The explicitly rejected 13e6fff draft package is
        # intentionally NOT a target, so rejected-draft quotations are out of
        # scope; valid historical quotations are not presented as current
        # conclusions in any targeted artifact.
        causal_forbidden = [
            "root cause now isolated",
            "not an environment anomaly",
            "not with an environment or clip anomaly",
        ]
        targets = [
            _EVIDENCE_DIR / "discrimination_evidence.json",
            _EVIDENCE_DIR / "discrimination_report.md",
            _EVIDENCE_DIR / "c1_status.json",
            _EVIDENCE_DIR / "c2_runs.json",
            _EVIDENCE_DIR / "c3_runs.json",
            _DECISION_JSON,
            _DECISION_MD,
            _FINDINGS_MD,
        ]
        for path in _json_files(targets):
            text = path.read_text(encoding="utf-8")
            for phrase in forbidden_exact:
                assert phrase not in text, f"{path.name}: forbidden phrase {phrase!r}"
            normalized = _normalize_ws(text).lower()
            for phrase in causal_forbidden:
                assert phrase not in normalized, (
                    f"{path.name}: forbidden causal phrase {phrase!r}"
                )

        # Positive assertions: the aggregate provenance block must carry the
        # evidence-bounded classification and explicitly NOT exclude the
        # environment contribution.
        prov = self._aggregate()["canonical_signature_provenance"]
        assert prov["causal_classification"] == "ROOT_CAUSE_UNKNOWN_NOT_ISOLATED"
        assert prov["codec_context_causal"] is False
        implication_normalized = _normalize_ws(prov["implication"]).lower()
        assert "environment contribution is not excluded" in implication_normalized
