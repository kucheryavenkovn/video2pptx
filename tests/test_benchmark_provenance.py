# FILE: tests/test_benchmark_provenance.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for provenance SHA validation and effective config mapping
#   SCOPE: _validate_provenance_sha, effective_config source regression
#   DEPENDS: pytest, benchmark_detect module
#   LINKS: M-DETECT-BENCHMARK
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


def _load_benchmark_module():
    mod_path = Path(__file__).resolve().parent.parent / "tools" / "benchmark_detect.py"
    spec = importlib.util.spec_from_file_location("benchmark_detect", mod_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["benchmark_detect"] = mod
    spec.loader.exec_module(mod)
    return mod


BENCHMARK = _load_benchmark_module()

# Valid test SHAs (all-zero patterns; cat-file will fail in git context)
_VALID_COMMIT = "0000000000000000000000000000000000000001"
_VALID_TREE = "0000000000000000000000000000000000000002"
_ABBREV_SHA = "abc123"
_LOWER_INVALID = "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"  # not hex
_SHORT_SHA = "abcdef01"


class TestValidateProvenanceSha:
    def test_accepts_valid_commit_format(self):
        result = BENCHMARK._validate_provenance_sha(
            "acb424f904bc4b3459f6ad2ceb9f8c701cedb69b",
            expected_type=None,
            repo_dir=None,
        )
        assert result == "acb424f904bc4b3459f6ad2ceb9f8c701cedb69b"

    def test_accepts_valid_tree_format(self):
        result = BENCHMARK._validate_provenance_sha(
            "6a7a596b802fa77465288136d4ea309a50557f2a",
            expected_type=None,
            repo_dir=None,
        )
        assert result == "6a7a596b802fa77465288136d4ea309a50557f2a"

    def test_rejects_abbreviated_sha(self):
        with pytest.raises(ValueError, match="full lowercase 40-character"):
            BENCHMARK._validate_provenance_sha("acb424f", expected_type=None)

    def test_rejects_short_sha(self):
        with pytest.raises(ValueError, match="full lowercase 40-character"):
            BENCHMARK._validate_provenance_sha("abc1234", expected_type=None)

    def test_rejects_non_hex(self):
        with pytest.raises(ValueError, match="full lowercase 40-character"):
            BENCHMARK._validate_provenance_sha("z" * 40, expected_type=None)

    def test_rejects_uppercase(self):
        with pytest.raises(ValueError, match="full lowercase 40-character"):
            BENCHMARK._validate_provenance_sha("A" + "a" * 39, expected_type=None)

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="full lowercase 40-character"):
            BENCHMARK._validate_provenance_sha("", expected_type=None)

    def test_git_object_type_mismatch_raises(self):
        # Use known valid tree SHA where commit is expected (or vice versa)
        # 6a7a596b802fa77465288136d4ea309a50557f2a is a tree SHA in this repo
        try:
            BENCHMARK._validate_provenance_sha(
                "6a7a596b802fa77465288136d4ea309a50557f2a",
                expected_type="commit",
                repo_dir=Path(__file__).resolve().parent.parent,
            )
            pytest.fail("expected ValueError for type mismatch")
        except ValueError as e:
            assert "Expected git object type 'commit'" in str(e)

    def test_commit_sha_passed_as_tree_rejected(self):
        # acb424f904bc4b3459f6ad2ceb9f8c701cedb69b is a commit SHA
        try:
            BENCHMARK._validate_provenance_sha(
                "acb424f904bc4b3459f6ad2ceb9f8c701cedb69b",
                expected_type="tree",
                repo_dir=Path(__file__).resolve().parent.parent,
            )
            pytest.fail("expected ValueError for type mismatch")
        except ValueError as e:
            assert "Expected git object type 'tree'" in str(e)

    def test_tree_sha_passed_as_commit_rejected(self):
        # 6a7a596b802fa77465288136d4ea309a50557f2a is a tree SHA
        try:
            BENCHMARK._validate_provenance_sha(
                "6a7a596b802fa77465288136d4ea309a50557f2a",
                expected_type="commit",
                repo_dir=Path(__file__).resolve().parent.parent,
            )
            pytest.fail("expected ValueError for type mismatch")
        except ValueError as e:
            assert "Expected git object type 'commit'" in str(e)

    def test_valid_exact_commit_accepted(self):
        # This is a commit SHA in the current repo
        result = BENCHMARK._validate_provenance_sha(
            "acb424f904bc4b3459f6ad2ceb9f8c701cedb69b",
            expected_type="commit",
            repo_dir=Path(__file__).resolve().parent.parent,
        )
        assert result == "acb424f904bc4b3459f6ad2ceb9f8c701cedb69b"

    def test_valid_exact_tree_accepted(self):
        result = BENCHMARK._validate_provenance_sha(
            "6a7a596b802fa77465288136d4ea309a50557f2a",
            expected_type="tree",
            repo_dir=Path(__file__).resolve().parent.parent,
        )
        assert result == "6a7a596b802fa77465288136d4ea309a50557f2a"


class TestEffectiveConfigRegression:
    def test_aggregate_effective_config_from_median_run(self):
        """Verify aggregate_evidence.json effective_config comes from median_run effective_config."""
        agg_path = (
            Path(__file__).resolve().parent.parent
            / "benchmarks" / "detect" / "evidence" / "aggregate_evidence.json"
        )
        if not agg_path.exists():
            pytest.skip("aggregate_evidence.json not found")
        agg = json.loads(agg_path.read_text("utf-8"))
        cfg = agg.get("effective_config", {})
        expected_keys = {
            "video_identifier", "sample_fps", "configured_backend",
            "slide_roi", "ignore_rois", "threshold",
            "min_slide_duration", "min_stable_duration",
            "dedupe_enabled", "quick_mode", "effective_backend",
        }
        assert expected_keys.issubset(cfg.keys()), (
            f"effective_config missing expected keys. "
            f"Got: {set(cfg.keys())}. Expected subset: {expected_keys}"
        )
        # Verify it is the detection config payload, not benchmark-summary fields
        assert "benchmark_id" not in cfg, (
            "effective_config must not contain benchmark-summary fields like benchmark_id"
        )
        assert "wall_clock_seconds" not in cfg, (
            "effective_config must not contain benchmark-summary fields like wall_clock_seconds"
        )
        assert "detect_elapsed_seconds" not in cfg, (
            "effective_config must not contain benchmark-summary fields like detect_elapsed_seconds"
        )

    def test_effective_config_not_contaminated_by_summary_fields(self):
        """build_aggregate_evidence must use median_run.effective_config, not benchmark_summary fields."""
        mod = BENCHMARK
        clip = {
            "identifier": "test.mp4", "sha256": "00" * 20,
            "duration_seconds": 10.0, "resolution": "1920x1080",
            "codec": "H.264", "fps": 60.0,
        }
        effective_config = {
            "video_identifier": "test.mp4",
            "sample_fps": 2.0,
            "configured_backend": "auto",
            "slide_roi": "auto",
            "ignore_rois": [],
            "threshold": "auto",
            "min_slide_duration": 2.0,
            "min_stable_duration": 2.0,
            "dedupe_enabled": True,
            "quick_mode": False,
            "effective_backend": "pyav",
        }
        runs = [
            {
                "id": "run-01",
                "detect_elapsed_seconds": 10.0,
                "wall_clock_seconds": 10.5,
                "effective_config": effective_config,
                "output_signature": {"canonical_sha256": "00" * 20},
                "metrics": {"timers": {}, "counters": {}, "gauges": {}},
                "derived_metrics": {"real_time_multiplier": 1.0, "processing_x_realtime": 1.0, "effective_sampled_fps": 2.0},
                "slides_count": 5,
                "png_count": 2,
                "score_distribution": {"count": 10},
            }
        ]
        result = mod.build_aggregate_evidence(
            benchmark_sequence="test-seq",
            branch="test",
            benchmark_code_head="acb424f904bc4b3459f6ad2ceb9f8c701cedb69b",
            evidence_builder_head="acb424f904bc4b3459f6ad2ceb9f8c701cedb69b",
            benchmark_code_tree="6a7a596b802fa77465288136d4ea309a50557f2a",
            recovered_master_base="836a456eee0312646747d755dfe838052eaa6752",
            clip=clip,
            warmup_performed=True,
            recorded_runs=runs,
            profile_run=None,
        )
        cfg = result["effective_config"]
        assert cfg == effective_config, (
            f"effective_config mismatch. Expected: {effective_config}, got: {cfg}"
        )
        # Verify contamination is rejected
        assert "benchmark_id" not in cfg
        assert "wall_clock_seconds" not in cfg
        assert "detect_elapsed_seconds" not in cfg
