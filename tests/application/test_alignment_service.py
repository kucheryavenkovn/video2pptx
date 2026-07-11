# FILE: tests/application/test_alignment_service.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Verify AlignmentService dry-run, apply, idempotency, and failure behavior.
#   SCOPE: Dry-run, apply, cancellation, adapter failure, no side effects on dry-run.
#   DEPENDS: pytest, video2pptx.application, video2pptx.domain
#   LINKS: M-APP-ALIGN, V-APP-ALIGN
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add alignment service tests with fake aligner
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path

import pytest

from video2pptx.application.base import ServiceContext
from video2pptx.application.cancellation import CancellationToken
from video2pptx.application.errors import StageFailureError
from video2pptx.application.ports.alignment import AlignmentPlan
from video2pptx.application.services.alignment_service import AlignmentService
from video2pptx.domain import Project, Slide, StageStatus
from video2pptx.infrastructure.persistence.file_project_repository import FileProjectRepository


class FakeAligner:
    def __init__(self, plan: AlignmentPlan | None = None, error: Exception | None = None):
        self._plan = plan or AlignmentPlan(
            aligned_intervals=[(0.0, 5.5), (5.5, 10.0)],
            boundaries_total=1,
            boundaries_moved=1,
            avg_shift=0.5,
            max_shift=0.5,
            report={"test": True},
        )
        self._error = error

    def compute_plan(self, intervals, subtitles_path, **kwargs):
        if self._error:
            raise self._error
        return self._plan


def _make_project(tmp_path, subtitle_path="subs.srt") -> tuple[FileProjectRepository, Path]:
    repo = FileProjectRepository()
    project = Project(name="align-test", video_path="vid.mp4", subtitle_path=subtitle_path)
    project.replace_detected_slides([
        Slide.from_dict({"uid": "s1", "start": 0.0, "end": 5.0}),
        Slide.from_dict({"uid": "s2", "start": 5.0, "end": 10.0}),
    ])
    project.pipeline.start("detect")
    project.pipeline.succeed("detect")
    location = tmp_path / "proj"
    repo.create(location, project)
    return repo, location


class TestAlignmentService:
    def test_dry_run_returns_metrics_without_saving(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        service = AlignmentService(FakeAligner(), ctx)

        result = service.execute(location, "subs.srt", dry_run=True)

        assert result.success is True
        assert result.data["dry_run"] is True
        assert result.revision is None

        loaded = repo.load(location)
        assert loaded.project.slides[0].interval.start == 0.0
        assert loaded.project.slides[0].interval.end == 5.0

    def test_apply_updates_intervals_and_saves(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        service = AlignmentService(FakeAligner(), ctx)

        result = service.execute(location, "subs.srt", dry_run=False)

        assert result.success is True
        assert result.revision is not None
        assert result.data["boundaries_moved"] == 1

        loaded = repo.load(location)
        assert loaded.project.slides[0].interval.end == 5.5
        assert loaded.project.pipeline.status("align") is StageStatus.SUCCEEDED

    def test_cancellation_before_compute(self, tmp_path):
        repo, location = _make_project(tmp_path)
        token = CancellationToken()
        token.trigger()
        ctx = ServiceContext(repository=repo, cancellation=token)
        service = AlignmentService(FakeAligner(), ctx)

        with pytest.raises(StageFailureError, match="cancel"):
            service.execute(location, "subs.srt")

        loaded = repo.load(location)
        assert loaded.project.slides[0].interval.end == 5.0

    def test_adapter_failure_raises_stage_failure(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        aligner = FakeAligner(error=RuntimeError("subtitle parse error"))
        service = AlignmentService(aligner, ctx)

        with pytest.raises(StageFailureError, match="subtitle parse"):
            service.execute(location, "subs.srt")

    def test_no_subtitles_returns_failure(self, tmp_path):
        repo, location = _make_project(tmp_path, subtitle_path="")
        ctx = ServiceContext(repository=repo)
        service = AlignmentService(FakeAligner(), ctx)

        result = service.execute(location, "", dry_run=True)

        assert result.success is False
        assert "Subtitles" in result.error
