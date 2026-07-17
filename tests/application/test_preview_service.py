# FILE: tests/application/test_preview_service.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Verify PreviewService revision-safe execution, cancellation, and failure behavior.
#   SCOPE: Success, cancellation before mutation, adapter failure, no slide invalidation.
#   DEPENDS: pytest, video2pptx.application, video2pptx.domain
#   LINKS: M-APP-PREVIEW, V-M-APP-PREVIEW
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add preview service tests with fake analyzer
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path

import pytest

from video2pptx.application.base import ServiceContext
from video2pptx.application.cancellation import CancellationToken
from video2pptx.application.dto import ProgressUpdate
from video2pptx.application.errors import StageFailureError
from video2pptx.application.ports.preview_analyzer import PreviewOutput
from video2pptx.application.services.preview_service import PreviewService
from video2pptx.domain import Project, Slide
from video2pptx.infrastructure.persistence.file_project_repository import FileProjectRepository


class FakePreviewAnalyzer:
    def __init__(self, output: PreviewOutput | None = None, error: Exception | None = None):
        self._output = output or PreviewOutput(
            score_timestamps=[0.0, 1.0],
            score_values=[0.1, 0.2],
            video_duration=10.0,
        )
        self._error = error

    def analyze(self, video_path, **kwargs):
        if self._error:
            raise self._error
        return self._output


def _make_project(tmp_path) -> tuple[FileProjectRepository, Path]:
    repo = FileProjectRepository()
    project = Project(name="preview-test", video_path="vid.mp4")
    project.replace_detected_slides([
        Slide.from_dict({"uid": "s1", "start": 0.0, "end": 5.0}),
        Slide.from_dict({"uid": "s2", "start": 5.0, "end": 10.0}),
    ])
    location = tmp_path / "proj"
    repo.create(location, project)
    return repo, location


class TestPreviewService:
    def test_preview_succeeds_and_preserves_slides(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        service = PreviewService(FakePreviewAnalyzer(), ctx)

        result = service.execute(
            location,
            "vid.mp4",
            sample_fps=2.0,
            slide_roi="auto",
            ignore_rois=[],
            threshold=0.15,
            min_stable_duration=1.0,
        )

        assert result.success is True
        assert result.stage == "preview"
        assert result.revision is not None

        loaded = repo.load(location)
        assert loaded.project.score_timestamps == [0.0, 1.0]
        assert loaded.project.score_values == [0.1, 0.2]
        assert loaded.project.slide_count == 2
        assert str(loaded.project.slides[0].slide_id) == "s1"

    def test_cancellation_before_aggregate_mutation(self, tmp_path):
        repo, location = _make_project(tmp_path)
        token = CancellationToken()
        token.trigger()
        ctx = ServiceContext(repository=repo, cancellation=token)
        service = PreviewService(FakePreviewAnalyzer(), ctx)

        with pytest.raises(StageFailureError, match="cancel"):
            service.execute(
                location,
                "vid.mp4",
                sample_fps=2.0,
                slide_roi="auto",
                ignore_rois=[],
                threshold=0.15,
                min_stable_duration=1.0,
            )

        loaded = repo.load(location)
        assert loaded.project.score_timestamps == []
        assert loaded.project.slide_count == 2

    def test_adapter_failure_raises_stage_failure(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        analyzer = FakePreviewAnalyzer(error=RuntimeError("decoder failed"))
        service = PreviewService(analyzer, ctx)

        with pytest.raises(StageFailureError, match="decoder failed"):
            service.execute(
                location,
                "vid.mp4",
                sample_fps=2.0,
                slide_roi="auto",
                ignore_rois=[],
                threshold=0.15,
                min_stable_duration=1.0,
            )

        loaded = repo.load(location)
        assert loaded.project.score_timestamps == []

    def test_progress_observer_receives_updates(self, tmp_path):
        repo, location = _make_project(tmp_path)
        updates: list[ProgressUpdate] = []

        class Collector:
            def on_progress(self, update: ProgressUpdate) -> None:
                updates.append(update)

        ctx = ServiceContext(repository=repo, observer=Collector())
        service = PreviewService(FakePreviewAnalyzer(), ctx)

        service.execute(
            location,
            "vid.mp4",
            sample_fps=2.0,
            slide_roi="auto",
            ignore_rois=[],
            threshold=0.15,
            min_stable_duration=1.0,
        )

        percents = [u.percent for u in updates]
        assert 10 in percents
        assert 100 in percents
