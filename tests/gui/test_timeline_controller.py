# FILE: tests/gui/test_timeline_controller.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit and integration tests for TimelineController — slide CRUD with
#            reload-mutate-save cycle, revision checking, and error propagation.
#   SCOPE: add/delete/move/resize slides, clear image, signals, error cases
#   DEPENDS: TimelineController, pytest, PySide6, pytest-mock, tmp_path
#   LINKS: M-GUI-TIMELINE-CTRL
#   ROLE: TEST
#   MAP_MODE: NONE
# END_MODULE_CONTRACT

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, create_autospec

import pytest

from video2pptx.bootstrap.application import ApplicationServices
from video2pptx.gui.controllers.timeline_controller import TimelineController

# -- helpers ----------------------------------------------------------------


def _spy_signal() -> tuple[list, callable]:
    calls: list = []

    def _spy(*args):
        calls.append(args)

    return calls, _spy


@pytest.fixture
def services() -> MagicMock:
    return create_autospec(ApplicationServices, instance=True)


@pytest.fixture
def controller(services: MagicMock) -> TimelineController:
    return TimelineController(services=services)


# -- integration tests (real repository) -----------------------------------


@pytest.fixture
def real_project(tmp_path: Path) -> Path:
    """Create a real canonical project with 3 slides and return its location."""
    from video2pptx.domain.project import Project
    from video2pptx.domain.slide import Slide
    from video2pptx.domain.slide import SlideId as DomainSlideId
    from video2pptx.domain.time import TimeInterval
    from video2pptx.infrastructure.persistence.file_project_repository import (
        FileProjectRepository,
    )

    repo = FileProjectRepository()
    project = Project(name="timeline-test", output_dir=str(tmp_path / "tl-project"))
    # Add 3 slides
    slides = [
        Slide(slide_id=DomainSlideId.new(), interval=TimeInterval(0.0, 10.0), index=1, representative_timestamp=5.0),
        Slide(slide_id=DomainSlideId.new(), interval=TimeInterval(10.0, 25.0), index=2, representative_timestamp=17.5),
        Slide(slide_id=DomainSlideId.new(), interval=TimeInterval(25.0, 40.0), index=3, representative_timestamp=32.5),
    ]
    project.replace_detected_slides(slides)
    location = tmp_path / "tl-project"
    repo.create(location, project)
    return location


class TestAddSlideIntegration:
    def test_add_slide_at_gap(self, real_project: Path) -> None:
        svc = ApplicationServices()
        ctrl = TimelineController(services=svc)

        slide_id = ctrl.add_slide(real_project, 12.0)  # inside slide 2
        assert slide_id is not None

        view = svc.repository.load(real_project)
        assert view.project.slide_count == 4

    def test_add_slide_emits_slidesChanged(self, real_project: Path) -> None:
        svc = ApplicationServices()
        ctrl = TimelineController(services=svc)

        calls, spy = _spy_signal()
        ctrl.slidesChanged.connect(spy)
        ctrl.add_slide(real_project, 30.0)

        assert len(calls) >= 1

    def test_add_slide_negative_timestamp_emits_error(
        self, real_project: Path
    ) -> None:
        svc = ApplicationServices()
        ctrl = TimelineController(services=svc)

        calls, spy = _spy_signal()
        ctrl.errorOccurred.connect(spy)
        slide_id = ctrl.add_slide(real_project, -1.0)

        assert slide_id is None
        assert len(calls) >= 1


class TestDeleteSlideIntegration:
    def test_delete_existing_slide(self, real_project: Path) -> None:
        svc = ApplicationServices()
        ctrl = TimelineController(services=svc)

        loaded = svc.repository.load(real_project)
        first_id = loaded.project.slides[0].slide_id

        result = ctrl.delete_slide(real_project, first_id.value)
        assert result is True

        loaded2 = svc.repository.load(real_project)
        assert loaded2.project.slide_count == 2

    def test_delete_nonexistent_slide_emits_error(
        self, real_project: Path
    ) -> None:
        svc = ApplicationServices()
        ctrl = TimelineController(services=svc)

        calls, spy = _spy_signal()
        ctrl.errorOccurred.connect(spy)

        result = ctrl.delete_slide(real_project, "nonexistent-id")
        assert result is False
        assert len(calls) >= 1


class TestMoveSlideIntegration:
    def test_move_slide_to_new_interval(self, real_project: Path) -> None:
        svc = ApplicationServices()
        ctrl = TimelineController(services=svc)

        loaded = svc.repository.load(real_project)
        slide_id = loaded.project.slides[0].slide_id.value

        result = ctrl.move_slide(real_project, slide_id, 2.0, 8.0)
        assert result is True

        loaded2 = svc.repository.load(real_project)
        moved = loaded2.project.get_slide(slide_id)
        assert moved is not None
        assert moved.interval.start == 2.0
        assert moved.interval.end == 8.0

    def test_move_slide_overlap_emits_error(self, real_project: Path) -> None:
        svc = ApplicationServices()
        ctrl = TimelineController(services=svc)

        loaded = svc.repository.load(real_project)
        slide_id = loaded.project.slides[0].slide_id.value

        calls, spy = _spy_signal()
        ctrl.errorOccurred.connect(spy)

        # Move slide 0 to overlap with slide 1
        result = ctrl.move_slide(real_project, slide_id, 5.0, 15.0)
        assert result is False
        assert len(calls) >= 1


class TestResizeSlideIntegration:
    def test_resize_slide_end(self, real_project: Path) -> None:
        svc = ApplicationServices()
        ctrl = TimelineController(services=svc)

        loaded = svc.repository.load(real_project)
        slide_id = loaded.project.slides[0].slide_id.value

        result = ctrl.resize_slide(real_project, slide_id, 7.0)
        assert result is True

        loaded2 = svc.repository.load(real_project)
        resized = loaded2.project.get_slide(slide_id)
        assert resized is not None
        assert resized.interval.end == 7.0


class TestClearImageIntegration:
    def test_clear_slide_image(self, real_project: Path) -> None:
        svc = ApplicationServices()
        ctrl = TimelineController(services=svc)

        loaded = svc.repository.load(real_project)
        slide_id = loaded.project.slides[0].slide_id.value

        result = ctrl.clear_slide_image(real_project, slide_id)
        assert result is True

        loaded2 = svc.repository.load(real_project)
        cleared = loaded2.project.get_slide(slide_id)
        assert cleared is not None
        assert cleared.image is None


class TestSignalEmissionIntegration:
    def test_slidesChanged_on_add(self, real_project: Path) -> None:
        svc = ApplicationServices()
        ctrl = TimelineController(services=svc)

        calls, spy = _spy_signal()
        ctrl.slidesChanged.connect(spy)
        ctrl.add_slide(real_project, 15.0)

        assert len(calls) >= 1

    def test_slidesChanged_on_delete(self, real_project: Path) -> None:
        svc = ApplicationServices()
        ctrl = TimelineController(services=svc)

        calls, spy = _spy_signal()
        ctrl.slidesChanged.connect(spy)
        loaded = svc.repository.load(real_project)
        ctrl.delete_slide(real_project, loaded.project.slides[0].slide_id.value)

        assert len(calls) >= 1

    def test_slidesChanged_on_move(self, real_project: Path) -> None:
        svc = ApplicationServices()
        ctrl = TimelineController(services=svc)

        calls, spy = _spy_signal()
        ctrl.slidesChanged.connect(spy)
        loaded = svc.repository.load(real_project)
        ctrl.move_slide(real_project, loaded.project.slides[0].slide_id.value, 2.0, 8.0)

        assert len(calls) >= 1

    def test_slidesChanged_on_resize(self, real_project: Path) -> None:
        svc = ApplicationServices()
        ctrl = TimelineController(services=svc)

        calls, spy = _spy_signal()
        ctrl.slidesChanged.connect(spy)
        loaded = svc.repository.load(real_project)
        ctrl.resize_slide(real_project, loaded.project.slides[0].slide_id.value, 8.0)

        assert len(calls) >= 1

    def test_slidesChanged_on_clear_image(self, real_project: Path) -> None:
        svc = ApplicationServices()
        ctrl = TimelineController(services=svc)

        calls, spy = _spy_signal()
        ctrl.slidesChanged.connect(spy)
        loaded = svc.repository.load(real_project)
        ctrl.clear_slide_image(real_project, loaded.project.slides[0].slide_id.value)

        assert len(calls) >= 1
