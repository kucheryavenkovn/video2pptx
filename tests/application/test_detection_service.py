# FILE: tests/application/test_detection_service.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Verify DetectionService replaces slides, invalidates downstream, and saves with revision.
#   SCOPE: Success, cancellation, adapter failure, downstream invalidation, no side effects.
#   DEPENDS: pytest, video2pptx.application, video2pptx.domain
#   LINKS: M-APP-DETECT, V-M-APP-DETECT
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
from video2pptx.application.dto import ProgressUpdate
from video2pptx.application.errors import StageFailureError
from video2pptx.application.ports.slide_detector import DetectionOutput
from video2pptx.application.services.detection_service import DetectionService
from video2pptx.domain import Project, Slide, StageStatus
from video2pptx.infrastructure.persistence.file_project_repository import FileProjectRepository


class RecordingObserver:
    def __init__(self) -> None:
        self.updates: list[ProgressUpdate] = []

    def on_progress(self, update: ProgressUpdate) -> None:
        self.updates.append(update)


class FakeDetector:
    def __init__(
        self,
        output: DetectionOutput | None = None,
        error: Exception | None = None,
        *,
        emit_progress: bool = False,
    ):
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
        self._emit_progress = emit_progress
        self.last_kwargs: dict = {}

    def detect(self, video_path, out_dir, **kwargs):
        self.last_kwargs = dict(kwargs)
        if self._error:
            raise self._error
        cb = kwargs.get("progress_callback")
        if self._emit_progress and cb is not None:
            cb(0, "Pass 1/2: analyzed 10 frames, 1 candidates")
            cb(50, "Pass 1/2: analyzed 50 frames, 3 candidates")
            cb(100, "Pass 1/2: frame analysis complete")
            cb(50, "Pass 2/2: captured 5/10 representative frames")
            cb(100, "Pass 2/2: captured 10/10 representative frames")
            cb(100, "Deduplication: 10 → 2 slides")
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

    def test_detector_progress_reaches_gui_observer(self, tmp_path):
        repo, location = _make_project(tmp_path)
        observer = RecordingObserver()
        ctx = ServiceContext(repository=repo, observer=observer)
        service = DetectionService(FakeDetector(emit_progress=True), ctx)

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
        percents = [u.percent for u in observer.updates]
        assert percents, "expected progress updates"
        # Monotonic non-decreasing after clamps applied by mapping
        for a, b in zip(percents, percents[1:], strict=False):
            assert b >= a, f"non-monotonic progress {percents}"
        # Must leave the old sticky 10% zone and show mapped Pass1 mid values
        assert any(5 <= p <= 65 for p in percents)
        assert any(70 <= p <= 93 for p in percents)
        assert percents[-1] == 100
        # Fake detector must receive a callback
        assert callable(FakeDetector(emit_progress=True).detect)  # sanity
        # Re-run capture: service always passes progress_callback
        det = FakeDetector(emit_progress=False)
        DetectionService(det, ServiceContext(repository=repo, observer=observer)).execute(
            location,
            "vid.mp4",
            sample_fps=2.0,
            slide_roi="auto",
            ignore_rois=[],
            threshold=0.15,
            min_stable_duration=1.0,
            min_slide_duration=1.0,
        )
        assert "progress_callback" in det.last_kwargs
        assert det.last_kwargs["progress_callback"] is not None


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
        project.detection.analysis_max_side = 720
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
        assert received["analysis_max_side"] == 720

    def test_detection_service_override_wins(self, tmp_path: Path) -> None:
        repo = FileProjectRepository()
        location = tmp_path / "override"
        project = Project(name="override-test", output_dir=str(location))
        project.detection.sample_fps = 0.5
        project.detection.threshold = "auto"
        project.detection.analysis_max_side = 480
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
        service.execute(
            location, video_path=None, sample_fps=3.5, threshold=0.123, analysis_max_side=640
        )

        assert received["sample_fps"] == 3.5
        assert received["threshold"] == 0.123
        assert received["analysis_max_side"] == 640

    def test_explicit_native_none_override(self, tmp_path: Path) -> None:
        """analysis_max_side=None is explicit native, not 'use project'."""
        repo = FileProjectRepository()
        location = tmp_path / "native-ov"
        project = Project.create_new(name="native-ov", output_dir=str(location))
        project.detection.analysis_max_side = 480
        project.video_path = str(tmp_path / "video.mp4")
        Path(project.video_path).write_text("fake")
        repo.create(location, project)

        received = {}

        class CapturingDetector:
            def detect(self, video_path, out_dir, **kw):
                received.update(kw)
                return DetectionOutput(
                    slides=[], score_timestamps=[], score_values=[], video_duration=0
                )

        ctx = ServiceContext(repository=repo, cancellation=CancellationToken())
        service = DetectionService(detector=CapturingDetector(), context=ctx)
        service.execute(location, video_path=None, analysis_max_side=None)
        assert received["analysis_max_side"] is None

    def test_product_range_validation_before_pipeline(self, tmp_path: Path) -> None:
        from video2pptx.application.errors import PreconditionError
        from video2pptx.domain.pipeline_state import StageStatus

        repo = FileProjectRepository()
        location = tmp_path / "bad-ams"
        project = Project.create_new(name="bad-ams", output_dir=str(location))
        project.detection.analysis_max_side = 480
        project.video_path = str(tmp_path / "video.mp4")
        Path(project.video_path).write_text("fake")
        repo.create(location, project)

        calls = {"n": 0}

        class NoCallDetector:
            def detect(self, *a, **k):
                calls["n"] += 1
                raise AssertionError("detector must not run")

        class CountingRepo:
            def __init__(self, inner):
                self._inner = inner
                self.saves = 0

            def load(self, location):
                return self._inner.load(location)

            def save(self, *a, **k):
                self.saves += 1
                return self._inner.save(*a, **k)

            def create(self, *a, **k):
                return self._inner.create(*a, **k)

        crepo = CountingRepo(repo)
        ctx = ServiceContext(repository=crepo, cancellation=CancellationToken())
        service = DetectionService(detector=NoCallDetector(), context=ctx)

        for bad in (239, 2161, 100, 0, -1, True, "480", 480.0):
            with pytest.raises(PreconditionError) as ei:
                service.execute(location, video_path=None, analysis_max_side=bad)  # type: ignore[arg-type]
            assert "analysis_max_side" in str(ei.value)
            assert calls["n"] == 0
            assert crepo.saves == 0
            reloaded = repo.load(location)
            assert reloaded.project.pipeline.get("detect").status == StageStatus.NOT_STARTED

    def test_bounds_accepted(self, tmp_path: Path) -> None:
        repo = FileProjectRepository()
        location = tmp_path / "bounds"
        project = Project.create_new(name="bounds", output_dir=str(location))
        project.video_path = str(tmp_path / "video.mp4")
        Path(project.video_path).write_text("fake")
        repo.create(location, project)
        received = {}

        class CapturingDetector:
            def detect(self, video_path, out_dir, **kw):
                received["ams"] = kw.get("analysis_max_side")
                return DetectionOutput(
                    slides=[], score_timestamps=[], score_values=[], video_duration=0
                )

        ctx = ServiceContext(repository=repo, cancellation=CancellationToken())
        service = DetectionService(detector=CapturingDetector(), context=ctx)
        for val in (240, 2160):
            service.execute(location, video_path=None, analysis_max_side=val)
            assert received["ams"] == val
