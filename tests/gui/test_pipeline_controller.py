# FILE: tests/gui/test_pipeline_controller.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit tests for PipelineController — stage dispatch, progress forwarding,
#            signal emission on success/error for preview/detect/align/notes/export/validate/auto.
#   SCOPE: signal wiring, service dispatch, error propagation
#   DEPENDS: PipelineController, pytest, PySide6, pytest-mock
#   LINKS: M-GUI-PIPELINE-CTRL
#   ROLE: TEST
#   MAP_MODE: NONE
# END_MODULE_CONTRACT

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, create_autospec

import pytest

from video2pptx.application.dto import ServiceResult
from video2pptx.bootstrap.application import ApplicationServices
from video2pptx.gui.controllers.pipeline_controller import PipelineController

# -- helpers ----------------------------------------------------------------


def _spy_signal() -> tuple[list, callable]:
    calls: list = []

    def _spy(*args):
        calls.append(args)

    return calls, _spy


@pytest.fixture
def services() -> MagicMock:
    svc = create_autospec(ApplicationServices, instance=True)
    svc.preview_service = MagicMock()
    svc.detection_service = MagicMock()
    svc.alignment_service = MagicMock()
    svc.notes_service = MagicMock()
    svc.export_service = MagicMock()
    svc.validation_service = MagicMock()
    svc.auto_service = MagicMock()
    svc.repository = MagicMock()
    def scoped(context):
        svc.context = context
        return svc
    svc.scoped.side_effect = scoped
    return svc


@pytest.fixture
def controller(services: MagicMock) -> PipelineController:
    return PipelineController(services=services)


SAMPLE_PROJECT = Path("/tmp/test-project")


def _wait(controller: PipelineController, qtbot) -> None:
    qtbot.waitUntil(lambda: controller._thread is None, timeout=10000)


# -- progress forwarding ----------------------------------------------------


class TestProgressForwarding:
    def test_progress_signal_emitted(self, controller: PipelineController, qtbot) -> None:
        calls, spy = _spy_signal()
        controller.progress.connect(spy)

        def execute(*args, **kwargs):
            controller._services.context.report_progress(42, "Detected candidates")
            return ServiceResult.ok("detect", data={"slides_count": 3})

        controller._services.detection_service.execute.side_effect = execute

        controller.run_detect(SAMPLE_PROJECT)
        qtbot.waitUntil(lambda: bool(calls), timeout=1000)
        _wait(controller, qtbot)
        assert calls == [(42, "Detected candidates")]


# -- successful dispatch ----------------------------------------------------


class TestDispatchSuccess:
    @pytest.mark.parametrize(
        "stage,run_method,service_attr,params",
        [
            ("preview", "run_preview", "preview_service",
             {"video_path": "", "sample_fps": 2.0, "slide_roi": "",
              "ignore_rois": [], "threshold": 0.95, "min_stable_duration": 2.0}),
            ("detect", "run_detect", "detection_service",
             {"video_path": "", "sample_fps": 2.0, "slide_roi": "",
              "ignore_rois": [], "threshold": 0.95,
              "min_stable_duration": 2.0, "min_slide_duration": 2.0,
              "dedupe_enabled": True}),
            ("align", "run_align", "alignment_service",
             {"subtitles_path": "", "dry_run": False,
              "max_shift_sec": 3.0, "include_manual": False}),
            ("notes", "run_notes", "notes_service",
             {"subtitles_path": "", "mode": "basic"}),
            ("export", "run_export", "export_service",
             {"output_path": "", "format": "markdown",
              "overwrite": True, "dry_run": False}),
            ("validate", "run_validate", "validation_service",
             {"check_storage": True, "check_aggregate": True,
              "check_media": True, "check_artifacts": True,
              "check_exports": True}),
        ],
    )
    def test_stage_dispatches_to_correct_service(
        self,
        controller: PipelineController,
        stage: str,
        run_method: str,
        service_attr: str,
        params: dict,
        qtbot,
    ) -> None:
        svc = getattr(controller._services, service_attr)
        svc.execute.return_value = ServiceResult.ok(stage)
        spy_calls, spy = _spy_signal()
        controller.stageFinished.connect(spy)

        getattr(controller, run_method)(SAMPLE_PROJECT, **params)
        _wait(controller, qtbot)

        svc.execute.assert_called_once()
        assert spy_calls == [(ServiceResult.ok(stage),)]

    def test_auto_dispatches_to_auto_service(
        self, controller: PipelineController, qtbot
    ) -> None:
        controller._services.auto_service.execute.return_value = ServiceResult.ok(
            "auto", data={"mode": "full"}
        )
        spy_calls, spy = _spy_signal()
        controller.stageFinished.connect(spy)

        controller.run_auto(SAMPLE_PROJECT, mode="full")
        _wait(controller, qtbot)

        controller._services.auto_service.execute.assert_called_once()
        assert spy_calls == [(ServiceResult.ok("auto", data={"mode": "full"}),)]


# -- error scenarios --------------------------------------------------------


class TestErrorScenarios:
    def test_error_on_service_failure(
        self, controller: PipelineController, qtbot
    ) -> None:
        controller._services.detection_service.execute.return_value = ServiceResult.fail(
            "detect", error="Detection failed"
        )
        spy_calls, spy = _spy_signal()
        controller.error.connect(spy)

        controller.run_detect(SAMPLE_PROJECT)
        _wait(controller, qtbot)

        assert len(spy_calls) == 1
        assert "Detection failed" in str(spy_calls[0][0])

    def test_error_on_exception(
        self, controller: PipelineController, qtbot
    ) -> None:
        controller._services.detection_service.execute.side_effect = RuntimeError(
            "Unexpected crash"
        )
        spy_calls, spy = _spy_signal()
        controller.error.connect(spy)

        controller.run_detect(SAMPLE_PROJECT)
        _wait(controller, qtbot)

        assert len(spy_calls) == 1

    def test_stage_finished_not_emitted_on_error(
        self, controller: PipelineController, qtbot
    ) -> None:
        controller._services.detection_service.execute.side_effect = RuntimeError("boom")
        finished_calls, finished_spy = _spy_signal()
        controller.stageFinished.connect(finished_spy)

        controller.run_detect(SAMPLE_PROJECT)
        _wait(controller, qtbot)

        assert len(finished_calls) == 0


# -- integration: real project + real services ------------------------------


class TestIntegration:
    def test_validate_on_real_project(self, tmp_path: Path, qtbot) -> None:
        """Validate requires an actual project on disk.  Create one first."""
        from video2pptx.bootstrap.application import ApplicationServices
        from video2pptx.domain.project import Project
        from video2pptx.infrastructure.persistence.file_project_repository import (
            FileProjectRepository,
        )

        real_services = ApplicationServices()
        ctrl = PipelineController(services=real_services)

        repo = FileProjectRepository()
        location = tmp_path / "integ-project"
        repo.create(location, Project(name="integ-test"))

        spy_calls, spy = _spy_signal()
        ctrl.stageFinished.connect(spy)

        ctrl.run_validate(location)
        _wait(ctrl, qtbot)

        assert len(spy_calls) == 1
        result = spy_calls[0][0]
        assert result.success
        assert result.stage == "validate"
