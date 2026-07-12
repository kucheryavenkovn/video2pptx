# FILE: tests/gui/test_project_controller.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit tests for ProjectController — project lifecycle (create/open/save/close)
#            using ApplicationServices with a real temp-directory FileProjectRepository.
#   SCOPE: create, open, save, close, error cases
#   DEPENDS: ProjectController, pytest, PySide6, temp_path fixture
#   LINKS: M-GUI-PROJECT-CTRL
#   ROLE: TEST
#   MAP_MODE: NONE
# END_MODULE_CONTRACT

from __future__ import annotations

import json
from pathlib import Path

import pytest

from video2pptx.bootstrap.application import ApplicationServices
from video2pptx.domain.project import Project
from video2pptx.gui.controllers.project_controller import ProjectController

# -- fixtures ---------------------------------------------------------------


@pytest.fixture
def services() -> ApplicationServices:
    return ApplicationServices()


@pytest.fixture
def controller(services: ApplicationServices) -> ProjectController:
    return ProjectController(services=services)


# -- helpers ----------------------------------------------------------------


def _spy_signal() -> tuple[list, callable]:
    calls: list = []

    def _spy(*args):
        calls.append(args)

    return calls, _spy


# -- create -----------------------------------------------------------------


class TestCreate:
    def test_creates_project_on_disk(self, controller: ProjectController, tmp_path: Path) -> None:
        spy_calls, spy = _spy_signal()
        controller.projectOpened.connect(spy)

        controller.create(tmp_path, "test-project")

        assert controller.is_open
        assert controller.project is not None
        assert controller.project.name == "test-project"
        assert spy_calls == [()]

        proj_file = tmp_path / "test-project" / "project.json"
        assert proj_file.is_file()
        data = json.loads(proj_file.read_text(encoding="utf-8"))
        assert data["schema_version"] == "2.0"
        assert data["name"] == "test-project"

    def test_create_emits_error_on_existing_dir(
        self, controller: ProjectController, tmp_path: Path
    ) -> None:
        (tmp_path / "existing").mkdir(parents=True)
        (tmp_path / "existing" / "placeholder.txt").touch()

        spy_calls, spy = _spy_signal()
        controller.errorOccurred.connect(spy)

        controller.create(tmp_path, "existing")

        assert not controller.is_open
        assert len(spy_calls) == 1
        assert "existing" in str(spy_calls[0][0])

    def test_create_revision_is_set(self, controller: ProjectController, tmp_path: Path) -> None:
        controller.create(tmp_path, "rev-test")
        assert controller.revision is not None
        assert len(controller.revision) > 0


# -- open -------------------------------------------------------------------


class TestOpen:
    def test_opens_created_project(self, controller: ProjectController, tmp_path: Path) -> None:
        controller.create(tmp_path, "open-test")
        project_dir = tmp_path / "open-test"
        first_revision = controller.revision

        controller2 = ProjectController(services=controller._services)
        spy_calls, spy = _spy_signal()
        controller2.projectOpened.connect(spy)

        controller2.open(project_dir)

        assert controller2.is_open
        assert controller2.project is not None
        assert controller2.project.name == "open-test"
        assert spy_calls == [()]

    def test_open_emits_error_on_missing_dir(
        self, controller: ProjectController, tmp_path: Path
    ) -> None:
        spy_calls, spy = _spy_signal()
        controller.errorOccurred.connect(spy)

        controller.open(tmp_path / "does-not-exist")

        assert not controller.is_open
        assert len(spy_calls) == 1

    def test_open_preserves_stored_revision(
        self, controller: ProjectController, tmp_path: Path
    ) -> None:
        controller.create(tmp_path, "rev-test-2")
        project_dir = tmp_path / "rev-test-2"
        first_revision = controller.revision

        controller2 = ProjectController(services=controller._services)
        controller2.open(project_dir)

        assert controller2.revision is not None
        assert controller2.revision == first_revision, (
            "create → load round-trip should preserve the same stored revision"
        )


# -- save -------------------------------------------------------------------


class TestSave:
    def test_save_persists_changes(self, controller: ProjectController, tmp_path: Path) -> None:
        controller.create(tmp_path, "save-test")
        controller.project.name = "UpdatedName"

        spy_calls, spy = _spy_signal()
        controller.stateChanged.connect(spy)

        controller.save()

        data = json.loads(
            (tmp_path / "save-test" / "project.json").read_text(encoding="utf-8")
        )
        assert data["name"] == "UpdatedName"
        assert spy_calls == [()]

    def test_save_emits_error_when_no_project(self, controller: ProjectController) -> None:
        spy_calls, spy = _spy_signal()
        controller.errorOccurred.connect(spy)

        controller.save()

        assert len(spy_calls) == 1

    def test_save_updates_revision(self, controller: ProjectController, tmp_path: Path) -> None:
        controller.create(tmp_path, "save-rev")
        old_rev = controller.revision

        controller.save()

        assert controller.revision != old_rev


# -- close ------------------------------------------------------------------


class TestClose:
    def test_close_resets_state(self, controller: ProjectController, tmp_path: Path) -> None:
        controller.create(tmp_path, "close-test")

        spy_calls, spy = _spy_signal()
        controller.projectClosed.connect(spy)

        controller.close()

        assert not controller.is_open
        assert controller.project is None
        assert controller.revision is None
        assert spy_calls == [()]

    def test_close_then_open_different(
        self, controller: ProjectController, tmp_path: Path
    ) -> None:
        controller.create(tmp_path, "close-first")
        controller.close()

        controller.create(tmp_path, "close-second")
        assert controller.project is not None
        assert controller.project.name == "close-second"


# -- signals ----------------------------------------------------------------


class TestSignals:
    def test_projectOpened_emitted_on_create(
        self, controller: ProjectController, tmp_path: Path
    ) -> None:
        calls, spy = _spy_signal()
        controller.projectOpened.connect(spy)
        controller.create(tmp_path, "sig-test")
        assert len(calls) == 1

    def test_projectOpened_emitted_on_open(
        self, controller: ProjectController, tmp_path: Path
    ) -> None:
        controller.create(tmp_path, "sig-test-open")
        controller.close()

        calls, spy = _spy_signal()
        controller.projectOpened.connect(spy)
        controller.open(tmp_path / "sig-test-open")
        assert len(calls) == 1

    def test_projectClosed_emitted_on_close(
        self, controller: ProjectController, tmp_path: Path
    ) -> None:
        controller.create(tmp_path, "sig-close")

        calls, spy = _spy_signal()
        controller.projectClosed.connect(spy)
        controller.close()
        assert len(calls) == 1

    def test_errorOccurred_on_missing_open(
        self, controller: ProjectController, tmp_path: Path
    ) -> None:
        calls, spy = _spy_signal()
        controller.errorOccurred.connect(spy)
        controller.open(tmp_path / "missing")
        assert len(calls) == 1

    def test_stateChanged_on_save(
        self, controller: ProjectController, tmp_path: Path
    ) -> None:
        controller.create(tmp_path, "sig-save")

        calls, spy = _spy_signal()
        controller.stateChanged.connect(spy)
        controller.save()
        assert len(calls) == 1


class TestDetectionConfigPersistence:
    """F-0075: DetectionConfig schema 2.0 round-trip via canonical save."""

    def test_detection_config_round_trip(self, tmp_path: Path) -> None:
        svc = ApplicationServices()
        location = tmp_path / "det-persist"
        project = Project(
            name="det-roundtrip", output_dir=str(location),
            video_path=str(tmp_path / "video.mp4"),
        )
        Path(project.video_path).write_text("fake")
        project.detection.sample_fps = 3.5
        project.detection.threshold = 0.123
        project.detection.slide_roi = "100,50,1800,1000"
        project.detection.min_slide_duration = 4.5
        project.detection.min_stable_duration = 3.0
        project.detection.decoder_backend = "pyav"
        project.detection.dedupe_enabled = False
        project.detection.ignore_rois = ["10,10,100,100"]
        svc.repository.create(location, project)

        reopened = svc.repository.load(location)
        dc = reopened.project.detection
        assert dc.sample_fps == 3.5
        assert dc.threshold == 0.123
        assert dc.slide_roi == "100,50,1800,1000"
        assert dc.min_slide_duration == 4.5
        assert dc.min_stable_duration == 3.0
        assert dc.decoder_backend == "pyav"
        assert dc.dedupe_enabled is False
        assert dc.ignore_rois == ["10,10,100,100"]

    def test_detection_config_detect_receives_exact(self, tmp_path: Path) -> None:
        svc = ApplicationServices()
        location = tmp_path / "det-detect"
        project = Project(name="det-detect", output_dir=str(location))
        project.video_path = str(tmp_path / "video.mp4")
        Path(project.video_path).write_text("fake")
        project.detection.sample_fps = 0.5
        project.detection.threshold = "auto"
        project.detection.min_slide_duration = 10.0
        project.detection.min_stable_duration = 5.0
        project.detection.dedupe_enabled = False
        svc.repository.create(location, project)

        received = {}

        class FakeDetect:
            def detect(self, video_path, out_dir, **kw):
                received.update(kw)
                from video2pptx.application.ports.slide_detector import DetectionOutput
                return DetectionOutput(slides=[], score_timestamps=[], score_values=[])

        from video2pptx.application.base import ServiceContext
        from video2pptx.application.cancellation import CancellationToken
        ctx = ServiceContext(repository=svc.repository, cancellation=CancellationToken())
        from video2pptx.application.services.detection_service import DetectionService
        service = DetectionService(detector=FakeDetect(), context=ctx)
        service.execute(location, video_path=None)

        assert received["sample_fps"] == 0.5
        assert received["threshold"] == "auto"
        assert received["min_slide_duration"] == 10.0
        assert received["min_stable_duration"] == 5.0
        assert received["dedupe_enabled"] is False
