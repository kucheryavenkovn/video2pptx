# FILE: tests/application/test_detection_service.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Verify DetectionService replaces slides, invalidates downstream, and saves with revision.
#   SCOPE: Success, cancellation, adapter failure, downstream invalidation, no side effects.
#   DEPENDS: pytest, video2pptx.application, video2pptx.domain
#   LINKS: M-APP-DETECT, V-APP-DETECT
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add detection service tests with fake detector
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path

import pytest

from video2pptx.application.base import ServiceContext
from video2pptx.application.cancellation import CancellationToken
from video2pptx.application.errors import StageFailureError
from video2pptx.application.ports.slide_detector import DetectionOutput
from video2pptx.application.services.detection_service import DetectionService
from video2pptx.domain import Project, Slide, StageStatus
from video2pptx.infrastructure.persistence.file_project_repository import FileProjectRepository


class FakeDetector:
    def __init__(self, output: DetectionOutput | None = None, error: Exception | None = None):
        self._output = output or DetectionOutput(
            slides=[
                Slide.from_dict({"uid": "d1", "start": 0.0, "end": 3.0}),
                Slide.from_dict({"uid": "d2", "start": 3.0, "end": 7.0}),
            ],
            score_timestamps=[1.0],
            score_values=[0.5],
            video_duration=7.0,
        )
        self._error = error

    def detect(self, video_path, out_dir, **kwargs):
        if self._error:
            raise self._error
        return self._output


def _make_project(tmp_path) -> tuple[FileProjectRepository, Path]:
    repo = FileProjectRepository()
    project = Project(name="detect-test", video_path="vid.mp4")
    project.replace_detected_slides([
        Slide.from_dict({"uid": "old1", "start": 0.0, "end": 5.0}),
    ])
    project.pipeline.start("detect")
    project.pipeline.succeed("detect")
    project.pipeline.start("align")
    project.pipeline.succeed("align")
    location = tmp_path / "proj"
    repo.create(location, project)
    return repo, location


class TestDetectionService:
    def test_detect_replaces_slides_and_invalidates_downstream(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        service = DetectionService(FakeDetector(), ctx)

        result = service.execute(
            location,
            "vid.mp4",
            sample_fps=2.0,
            slide_roi="auto",
            ignore_rois=[],
            threshold=0.15,
            min_stable_duration=1.0,
            min_slide_duration=1.0,
        )

        assert result.success is True
        assert result.stage == "detect"
        assert result.revision is not None

        loaded = repo.load(location)
        assert loaded.project.slide_count == 2
        assert loaded.project.get_slide("d1") is not None
        assert loaded.project.get_slide("old1") is None
        assert loaded.project.pipeline.status("align") is StageStatus.STALE

    def test_cancellation_before_mutation_preserves_old_slides(self, tmp_path):
        repo, location = _make_project(tmp_path)
        token = CancellationToken()
        token.trigger()
        ctx = ServiceContext(repository=repo, cancellation=token)
        service = DetectionService(FakeDetector(), ctx)

        with pytest.raises(StageFailureError, match="cancel"):
            service.execute(
                location,
                "vid.mp4",
                sample_fps=2.0,
                slide_roi="auto",
                ignore_rois=[],
                threshold=0.15,
                min_stable_duration=1.0,
                min_slide_duration=1.0,
            )

        loaded = repo.load(location)
        assert loaded.project.slide_count == 1
        assert loaded.project.get_slide("old1") is not None

    def test_adapter_failure_raises_stage_failure(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        detector = FakeDetector(error=RuntimeError("cv2 error"))
        service = DetectionService(detector, ctx)

        with pytest.raises(StageFailureError, match="cv2 error"):
            service.execute(
                location,
                "vid.mp4",
                sample_fps=2.0,
                slide_roi="auto",
                ignore_rois=[],
                threshold=0.15,
                min_stable_duration=1.0,
                min_slide_duration=1.0,
            )

        loaded = repo.load(location)
        assert loaded.project.get_slide("old1") is not None

    def test_no_notes_or_export_side_effects(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        service = DetectionService(FakeDetector(), ctx)

        service.execute(
            location,
            "vid.mp4",
            sample_fps=2.0,
            slide_roi="auto",
            ignore_rois=[],
            threshold=0.15,
            min_stable_duration=1.0,
            min_slide_duration=1.0,
        )

        loaded = repo.load(location)
        assert loaded.project.pipeline.status("notes") is StageStatus.NOT_STARTED
        assert loaded.project.pipeline.status("markdown_export") is StageStatus.NOT_STARTED
        assert loaded.project.pipeline.status("pptx_export") is StageStatus.NOT_STARTED


class TestConfigPropagation:
    """Verify DetectionService reads canonical Project.detection when overrides are None."""

    def test_detection_service_uses_project_config(self, tmp_path: Path) -> None:
        repo = FileProjectRepository()
        location = tmp_path / "cfgtest"
        project = Project(name="cfg-test", output_dir=str(location))
        project.detection.sample_fps = 0.5
        project.detection.threshold = "auto"
        project.detection.min_slide_duration = 10.0
        project.detection.min_stable_duration = 5.0
        project.detection.dedupe_enabled = False
        project.detection.decoder_backend = "opencv"
        project.detection.slide_roi = "0,0,100,100"
        project.detection.ignore_rois = ["10,10,20,20"]
        project.video_path = str(tmp_path / "video.mp4")
        Path(project.video_path).write_text("fake")
        repo.create(location, project)

        received = {}

        class CapturingDetector:
            def detect(self, video_path, out_dir, **kw):
                received.update(kw)
                return DetectionOutput(slides=[], score_timestamps=[], score_values=[], video_duration=0)

        ctx = ServiceContext(repository=repo, cancellation=CancellationToken())
        service = DetectionService(detector=CapturingDetector(), context=ctx)
        service.execute(location, video_path=None)

        assert received["sample_fps"] == 0.5
        assert received["threshold"] == "auto"
        assert received["min_slide_duration"] == 10.0
        assert received["min_stable_duration"] == 5.0
        assert received["dedupe_enabled"] is False
        assert received["decoder_backend"] == "opencv"
        assert received["slide_roi"] == "0,0,100,100"
        assert received["ignore_rois"] == ["10,10,20,20"]

    def test_detection_service_override_wins(self, tmp_path: Path) -> None:
        repo = FileProjectRepository()
        location = tmp_path / "override"
        project = Project(name="override-test", output_dir=str(location))
        project.detection.sample_fps = 0.5
        project.detection.threshold = "auto"
        project.video_path = str(tmp_path / "video.mp4")
        Path(project.video_path).write_text("fake")
        repo.create(location, project)

        received = {}

        class CapturingDetector:
            def detect(self, video_path, out_dir, **kw):
                received.update(kw)
                return DetectionOutput(slides=[], score_timestamps=[], score_values=[], video_duration=0)

        ctx = ServiceContext(repository=repo, cancellation=CancellationToken())
        service = DetectionService(detector=CapturingDetector(), context=ctx)
        service.execute(location, video_path=None, sample_fps=3.5, threshold=0.123)

        assert received["sample_fps"] == 3.5
        assert received["threshold"] == 0.123
