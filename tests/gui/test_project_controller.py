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
