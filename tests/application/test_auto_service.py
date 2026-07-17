# FILE: tests/application/test_auto_service.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Verify AutoService full/resume/force orchestration and failure halting.
#   SCOPE: Full runs all stages, resume skips SUCCEEDED, force re-runs all, failure halts.
#   DEPENDS: pytest, video2pptx.application, video2pptx.domain
#   LINKS: M-APP-AUTO, V-M-APP-AUTO
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add auto orchestration tests with fake services
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from video2pptx.application.base import ServiceContext
from video2pptx.application.dto import ServiceResult
from video2pptx.application.services.auto_service import AutoService
from video2pptx.domain import Project, Slide
from video2pptx.infrastructure.persistence.file_project_repository import FileProjectRepository


def _mock_service(name: str, *, fail: bool = False) -> MagicMock:
    svc = MagicMock()
    if fail:
        svc.execute.return_value = ServiceResult.fail(name, f"{name} failed")
    else:
        svc.execute.return_value = ServiceResult.ok(name, data={"msg": f"{name} ok"})
    return svc


def _make_project(tmp_path) -> tuple[FileProjectRepository, Path]:
    repo = FileProjectRepository()
    project = Project(name="auto-test", video_path="vid.mp4")
    project.replace_detected_slides([
        Slide.from_dict({"uid": "s1", "start": 0.0, "end": 5.0}),
    ])
    location = tmp_path / "proj"
    repo.create(location, project)
    return repo, location


class TestAutoService:
    def test_full_runs_all_stages(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        svc = AutoService(
            context=ctx,
            preview_service=_mock_service("preview"),
            detection_service=_mock_service("detect"),
            alignment_service=_mock_service("align"),
            notes_service=_mock_service("notes"),
            export_service=_mock_service("export"),
            validation_service=_mock_service("validate"),
        )

        result = svc.execute(location, mode="full")

        assert result.success is True
        assert result.data["success"] is True
        assert result.data["failed_stage"] is None
        stages = list(result.data["results"].keys())
        assert stages == ["preview", "detect", "align", "notes", "export", "validate"]
        for s in stages:
            assert result.data["results"][s]["success"] is True

    def test_resume_skips_succeeded_stages(self, tmp_path):
        repo, location = _make_project(tmp_path)
        # Pre-mark detect as SUCCEEDED
        loaded = repo.load(location)
        loaded.project.pipeline.start("detect")
        loaded.project.pipeline.succeed("detect")
        repo.save(loaded.project, loaded.location, expected_revision=loaded.revision)

        ctx = ServiceContext(repository=repo)
        svc = AutoService(
            context=ctx,
            preview_service=_mock_service("preview"),
            detection_service=_mock_service("detect"),
            alignment_service=_mock_service("align"),
            notes_service=_mock_service("notes"),
            export_service=_mock_service("export"),
            validation_service=_mock_service("validate"),
        )

        result = svc.execute(location, mode="resume")

        assert result.data["success"] is True
        assert result.data["results"]["detect"].get("skipped") is True
        # non-skipped stages ran
        assert result.data["results"]["preview"]["success"] is True

    def test_force_re_runs_all_stages(self, tmp_path):
        repo, location = _make_project(tmp_path)
        # Pre-mark preview as SUCCEEDED
        loaded = repo.load(location)
        loaded.project.pipeline.start("preview")
        loaded.project.pipeline.succeed("preview")
        repo.save(loaded.project, loaded.location, expected_revision=loaded.revision)

        ctx = ServiceContext(repository=repo)
        svc = AutoService(
            context=ctx,
            preview_service=_mock_service("preview"),
            detection_service=_mock_service("detect"),
            alignment_service=_mock_service("align"),
            notes_service=_mock_service("notes"),
            export_service=_mock_service("export"),
            validation_service=_mock_service("validate"),
        )

        result = svc.execute(location, mode="force")

        assert result.data["success"] is True
        # preview was re-run (not skipped)
        assert "skipped" not in result.data["results"]["preview"]
        assert result.data["results"]["preview"]["success"] is True

    def test_stage_failure_halts_pipeline(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        svc = AutoService(
            context=ctx,
            preview_service=_mock_service("preview"),
            detection_service=_mock_service("detect", fail=True),
            alignment_service=_mock_service("align"),
            notes_service=_mock_service("notes"),
            export_service=_mock_service("export"),
            validation_service=_mock_service("validate"),
        )

        result = svc.execute(location, mode="full")

        assert result.data["success"] is False
        assert result.data["failed_stage"] == "detect"
        assert result.data["results"]["preview"]["success"] is True
        assert result.data["results"]["detect"]["success"] is False
        # align and later should be skipped
        assert result.data["results"]["align"].get("skipped") is True
        assert result.data["results"]["notes"].get("skipped") is True
        assert result.data["results"]["export"].get("skipped") is True
        assert result.data["results"]["validate"].get("skipped") is True
