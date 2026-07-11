# FILE: tests/application/test_export_service.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Verify ExportService markdown, PPTX, overwrite guard, dry-run, and cancellation.
#   SCOPE: Markdown staged, PPTX slide/image count, overwrite=false error, dry-run, cancellation.
#   DEPENDS: pytest, video2pptx.application, video2pptx.domain
#   LINKS: M-APP-EXPORT, V-APP-EXPORT
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add export service tests with fake exporter
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path

import pytest

from video2pptx.application.base import ServiceContext
from video2pptx.application.cancellation import CancellationToken
from video2pptx.application.errors import StageFailureError
from video2pptx.application.ports.presentation_exporter import ExportOutput
from video2pptx.application.services.export_service import ExportService
from video2pptx.domain import Project, Slide, StageStatus
from video2pptx.infrastructure.persistence.file_project_repository import FileProjectRepository


class FakeExporter:
    def __init__(self, output: ExportOutput | None = None):
        self._output = output or ExportOutput(
            format="markdown",
            output_path="/fake/output/deck.md",
            slide_count=2,
            image_count=1,
        )

    def export(self, slides_data, output_path, *, format="markdown"):
        return ExportOutput(
            format=format,
            output_path=output_path,
            slide_count=len(slides_data),
            image_count=sum(1 for s in slides_data if s.get("image")),
        )


def _make_project(tmp_path) -> tuple[FileProjectRepository, Path]:
    repo = FileProjectRepository()
    project = Project(name="export-test", video_path="vid.mp4", subtitle_path="subs.srt")
    project.replace_detected_slides([
        Slide.from_dict({"uid": "s1", "start": 0.0, "end": 5.0, "image": "img1.jpg"}),
        Slide.from_dict({"uid": "s2", "start": 5.0, "end": 10.0}),
    ])
    project.pipeline.start("detect")
    project.pipeline.succeed("detect")
    location = tmp_path / "proj"
    repo.create(location, project)
    return repo, location


class TestExportService:
    def test_markdown_staged_and_validated(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        service = ExportService(FakeExporter(), ctx)
        output_path = str(tmp_path / "output" / "deck.md")

        result = service.execute(location, output_path=output_path, format="markdown")

        assert result.success is True
        assert result.data["format"] == "markdown"
        assert result.data["slide_count"] == 2
        assert result.data["image_count"] == 1

        loaded = repo.load(location)
        assert loaded.project.pipeline.status("markdown_export") is StageStatus.SUCCEEDED

    def test_dry_run_does_not_save_pipeline(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        service = ExportService(FakeExporter(), ctx)

        result = service.execute(location, format="markdown", dry_run=True)

        assert result.success is True
        assert result.data["dry_run"] is True

        loaded = repo.load(location)
        assert loaded.project.pipeline.status("markdown_export") is StageStatus.NOT_STARTED

    def test_overwrite_false_with_existing_file(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        service = ExportService(FakeExporter(), ctx)

        output_path = str(location / "deck.md")
        Path(output_path).touch()

        result = service.execute(
            location, output_path=output_path, format="markdown", overwrite=False
        )

        assert result.success is False
        assert "overwrite=False" in result.error

    def test_cancellation_before_export(self, tmp_path):
        repo, location = _make_project(tmp_path)
        token = CancellationToken()
        token.trigger()
        ctx = ServiceContext(repository=repo, cancellation=token)
        service = ExportService(FakeExporter(), ctx)

        with pytest.raises(StageFailureError, match="cancel"):
            service.execute(location, format="markdown")

        loaded = repo.load(location)
        assert loaded.project.pipeline.status("markdown_export") is StageStatus.NOT_STARTED

    def test_pptx_slide_count_matches(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        exporter = FakeExporter(ExportOutput(
            format="pptx",
            output_path=str(tmp_path / "output" / "deck.pptx"),
            slide_count=2,
            image_count=1,
        ))
        service = ExportService(exporter, ctx)

        result = service.execute(location, format="pptx")

        assert result.success is True
        assert result.data["format"] == "pptx"
        assert result.data["slide_count"] == 2
        assert result.data["image_count"] == 1
