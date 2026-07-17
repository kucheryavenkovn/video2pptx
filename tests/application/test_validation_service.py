# FILE: tests/application/test_validation_service.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Verify ValidationService storage, aggregate, media, artifacts, export checks.
#   SCOPE: Valid canonical project valid=true; missing slides.json; missing media; revision mismatch.
#   DEPENDS: pytest, video2pptx.application, video2pptx.domain
#   LINKS: M-APP-VALIDATE, V-M-APP-VALIDATE
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add validation service tests
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path

from video2pptx.application.base import ServiceContext
from video2pptx.application.services.validation_service import ValidationService
from video2pptx.domain import Project, Slide
from video2pptx.infrastructure.persistence.file_project_repository import FileProjectRepository


def _make_project(tmp_path) -> tuple[FileProjectRepository, Path]:
    repo = FileProjectRepository()
    project = Project(name="validate-test", video_path="vid.mp4", subtitle_path="subs.srt")
    project.replace_detected_slides([
        Slide.from_dict({"uid": "s1", "start": 0.0, "end": 5.0, "image": ""}),
    ])
    project.pipeline.start("detect")
    project.pipeline.succeed("detect")
    project.pipeline.start("markdown_export")
    project.pipeline.succeed("markdown_export")
    location = tmp_path / "proj"
    repo.create(location, project)
    # Create stub exports that validation expects
    (location / "deck.md").write_text("# Stub deck", encoding="utf-8")
    return repo, location


class TestValidationService:
    def test_valid_project_returns_valid(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        service = ValidationService(ctx)

        result = service.execute(location)

        assert result.success is True
        assert result.data["valid"] is True

    def test_missing_artifact_reported(self, tmp_path):
        repo, location = _make_project(tmp_path)
        # Remove slides.json
        (location / "slides.json").unlink()
        ctx = ServiceContext(repository=repo)
        service = ValidationService(ctx)

        result = service.execute(location)

        assert result.data["valid"] is False
        artifact_errs = [e for e in result.data["errors"] if "slides.json" in e]
        assert len(artifact_errs) > 0

    def test_disabled_checks_skip(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        service = ValidationService(ctx)

        result = service.execute(
            location,
            check_storage=False,
            check_aggregate=False,
            check_media=False,
            check_artifacts=False,
            check_exports=False,
        )

        assert result.data["valid"] is True
