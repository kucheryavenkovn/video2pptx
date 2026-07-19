# FILE: tests/test_analysis_quality.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Phase 20 analysis quality presets, validation, domain apply, persistence
#   SCOPE: preset mapping, custom bounds, new project 480, legacy missing None, invalidation no-op
#   DEPENDS: pytest, M-ANALYSIS-QUALITY, M-DOMAIN-PROJECT, M-PERSIST-DTO
#   LINKS: V-M-ANALYSIS-QUALITY, Phase-20
#   ROLE: TEST
# END_MODULE_CONTRACT

from __future__ import annotations

import json
from pathlib import Path

import pytest

from video2pptx.analysis_quality import (
    ANALYSIS_MAX_SIDE_MAX,
    ANALYSIS_MAX_SIDE_MIN,
    DETAILED_ANALYSIS_MAX_SIDE,
    FAST_ANALYSIS_MAX_SIDE,
    NEW_PROJECT_ANALYSIS_MAX_SIDE,
    PRESET_UI_LABELS,
    AnalysisQualityPreset,
    max_side_from_preset,
    preset_from_max_side,
    validate_custom_max_side,
)
from video2pptx.domain.pipeline_state import StageStatus
from video2pptx.domain.project import DetectionConfig, Project
from video2pptx.infrastructure.persistence.dto import DetectionConfigDocument
from video2pptx.infrastructure.persistence.file_project_repository import FileProjectRepository


class TestPresetMapping:
    def test_from_values(self):
        assert preset_from_max_side(480) is AnalysisQualityPreset.FAST
        assert preset_from_max_side(720) is AnalysisQualityPreset.DETAILED
        assert preset_from_max_side(None) is AnalysisQualityPreset.NATIVE
        assert preset_from_max_side(640) is AnalysisQualityPreset.CUSTOM

    def test_to_values(self):
        assert max_side_from_preset(AnalysisQualityPreset.FAST) == FAST_ANALYSIS_MAX_SIDE
        assert max_side_from_preset(AnalysisQualityPreset.DETAILED) == DETAILED_ANALYSIS_MAX_SIDE
        assert max_side_from_preset(AnalysisQualityPreset.NATIVE) is None
        assert max_side_from_preset(AnalysisQualityPreset.CUSTOM, 512) == 512

    def test_ui_labels_no_480p(self):
        joined = " ".join(PRESET_UI_LABELS.values())
        assert "480p" not in joined
        assert "720p" not in joined
        assert "Быстрый" in PRESET_UI_LABELS[AnalysisQualityPreset.FAST]


class TestCustomValidation:
    def test_bounds(self):
        from video2pptx.analysis_quality import validate_analysis_max_side

        assert validate_analysis_max_side(None) is None
        assert validate_custom_max_side(240) == 240
        assert validate_custom_max_side(480) == 480
        assert validate_custom_max_side(720) == 720
        assert validate_custom_max_side(2160) == 2160

    def test_rejects(self):
        from video2pptx.analysis_quality import validate_analysis_max_side

        for bad in (0, -1, 239, 2161, True, False, "480", 480.5, 100):
            with pytest.raises(ValueError):
                validate_analysis_max_side(bad, allow_none=True)
        with pytest.raises(ValueError):
            validate_custom_max_side(None)

    def test_range_constants(self):
        assert ANALYSIS_MAX_SIDE_MIN == 240
        assert ANALYSIS_MAX_SIDE_MAX == 2160

    def test_project_json_100_rejected(self, tmp_path: Path):
        """Value 100 is not silently clamped — load fails controlled."""
        project = Project.create_new(name="bad100", output_dir=str(tmp_path / "bad100"))
        repo = FileProjectRepository()
        repo.create(tmp_path / "bad100", project)
        path = tmp_path / "bad100" / "project.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["detection"]["analysis_max_side"] = 100
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        with pytest.raises(Exception):
            repo.load(tmp_path / "bad100")


class TestNewVsLegacy:
    def test_create_new_sets_480(self, tmp_path: Path):
        project = Project.create_new(name="n", output_dir=str(tmp_path / "n"))
        assert project.detection.analysis_max_side == NEW_PROJECT_ANALYSIS_MAX_SIDE == 480
        repo = FileProjectRepository()
        loaded = repo.create(tmp_path / "n", project)
        doc = json.loads((tmp_path / "n" / "project.json").read_text(encoding="utf-8"))
        assert doc["detection"]["analysis_max_side"] == 480
        reloaded = repo.load(tmp_path / "n")
        assert reloaded.project.detection.analysis_max_side == 480
        assert loaded.revision

    def test_domain_default_none_not_480(self):
        p = Project(name="x")
        assert p.detection.analysis_max_side is None

    def test_legacy_missing_field_loads_none(self, tmp_path: Path):
        """project.json detection without analysis_max_side → None (native)."""
        # Build a valid document via mapper then strip field from JSON
        project = Project.create_new(name="legacy", output_dir=str(tmp_path / "legacy"))
        project.detection.analysis_max_side = 480
        repo = FileProjectRepository()
        repo.create(tmp_path / "legacy", project)
        path = tmp_path / "legacy" / "project.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        del data["detection"]["analysis_max_side"]
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        reloaded = repo.load(tmp_path / "legacy")
        assert reloaded.project.detection.analysis_max_side is None

    def test_explicit_null_round_trip(self, tmp_path: Path):
        project = Project.create_new(name="nullish", output_dir=str(tmp_path / "nullish"))
        project.detection.analysis_max_side = None
        repo = FileProjectRepository()
        repo.create(tmp_path / "nullish", project)
        data = json.loads((tmp_path / "nullish" / "project.json").read_text(encoding="utf-8"))
        assert "analysis_max_side" in data["detection"]
        assert data["detection"]["analysis_max_side"] is None
        reloaded = repo.load(tmp_path / "nullish")
        assert reloaded.project.detection.analysis_max_side is None

    def test_round_trip_values(self, tmp_path: Path):
        repo = FileProjectRepository()
        for value in (480, 720, 512, None):
            loc = tmp_path / f"rt_{value}"
            p = Project.create_new(name=str(value), output_dir=str(loc))
            p.detection.analysis_max_side = value
            repo.create(loc, p)
            assert repo.load(loc).project.detection.analysis_max_side == value

    def test_corrupted_value_rejected(self):
        with pytest.raises(Exception):
            DetectionConfigDocument.model_validate({"analysis_max_side": True})
        with pytest.raises(Exception):
            DetectionConfigDocument.model_validate({"analysis_max_side": "fast"})
        with pytest.raises(Exception):
            DetectionConfigDocument.model_validate({"analysis_max_side": 0})


class TestApplyDetectionConfig:
    def _succeed(self, pipeline, stage: str) -> None:
        pipeline.start(stage)
        pipeline.succeed(stage)

    def test_change_invalidates_detect_and_downstream(self):
        from video2pptx.domain.pipeline_state import DOWNSTREAM

        p = Project.create_new(name="inv")
        stages = ("detect",) + DOWNSTREAM["detect"]
        for stage in stages:
            self._succeed(p.pipeline, stage)

        new = DetectionConfig(
            sample_fps=p.detection.sample_fps,
            decoder_backend=p.detection.decoder_backend,
            slide_roi=p.detection.slide_roi,
            ignore_rois=list(p.detection.ignore_rois),
            threshold=p.detection.threshold,
            min_slide_duration=p.detection.min_slide_duration,
            min_stable_duration=p.detection.min_stable_duration,
            dedupe_enabled=p.detection.dedupe_enabled,
            analysis_max_side=720,
        )
        assert p.apply_detection_config(new) is True
        assert p.detection.analysis_max_side == 720
        assert p.pipeline.get("detect").status == StageStatus.STALE
        for stage in DOWNSTREAM["detect"]:
            assert p.pipeline.get(stage).status == StageStatus.STALE, stage

    def test_noop_no_invalidation(self):
        p = Project.create_new(name="noop")
        self._succeed(p.pipeline, "detect")
        self._succeed(p.pipeline, "align")
        same = DetectionConfig(
            sample_fps=p.detection.sample_fps,
            decoder_backend=p.detection.decoder_backend,
            slide_roi=p.detection.slide_roi,
            ignore_rois=list(p.detection.ignore_rois),
            threshold=p.detection.threshold,
            min_slide_duration=p.detection.min_slide_duration,
            min_stable_duration=p.detection.min_stable_duration,
            dedupe_enabled=p.detection.dedupe_enabled,
            analysis_max_side=p.detection.analysis_max_side,
        )
        assert p.apply_detection_config(same) is False
        assert p.pipeline.get("detect").status == StageStatus.SUCCEEDED
        assert p.pipeline.get("align").status == StageStatus.SUCCEEDED
