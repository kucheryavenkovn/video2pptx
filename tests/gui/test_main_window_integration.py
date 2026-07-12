# FILE: tests/gui/test_main_window_integration.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Step 8.5 regression gate for real MainWindow/controller integration.
#   SCOPE: Async execution, scoped progress, lifecycle ordering, SlideId adaptation,
#          ArtifactRef persistence, revision ownership, Qt state, playback, and LOC gate.
#   DEPENDS: M-GUI-MAIN, M-GUI-PROJECT-CTRL, M-GUI-PIPELINE-CTRL, M-GUI-TIMELINE-CTRL
#   LINKS: V-REF-GUI-ADAPTER, F-0058, F-0063, F-0064, F-0065, F-0066, F-0067,
#          F-0068, F-0069, F-0070
#   ROLE: TEST
#   MAP_MODE: NONE
# END_MODULE_CONTRACT

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from video2pptx.application.dto import ServiceResult
from video2pptx.bootstrap.application import ApplicationServices
from video2pptx.domain.artifacts import ArtifactRef
from video2pptx.domain.project import Project
from video2pptx.gui.controllers.pipeline_controller import PipelineController
from video2pptx.gui.controllers.project_controller import ProjectController
from video2pptx.gui.controllers.timeline_controller import TimelineController


def _window(qtbot):
    from video2pptx.gui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)
    return window


def test_pipeline_returns_before_service_finishes(qtbot) -> None:
    services = MagicMock()
    services.repository = MagicMock()

    def slow_execute(*args, **kwargs):
        time.sleep(0.2)
        return ServiceResult.ok("detect")

    services.detection_service.execute.side_effect = slow_execute
    services.scoped.return_value = services
    controller = PipelineController(services)

    started = time.perf_counter()
    controller.run_detect(Path("project"))

    assert time.perf_counter() - started < 0.1
    qtbot.waitUntil(lambda: services.detection_service.execute.called, timeout=1000)
    qtbot.waitUntil(lambda: controller._thread is None, timeout=2000)


def test_real_service_progress_reaches_controller(tmp_path: Path, qtbot) -> None:
    services = ApplicationServices()
    location = tmp_path / "progress"
    services.repository.create(location, Project(name="progress", output_dir=str(location)))
    controller = PipelineController(services)
    progress: list[tuple[int, str]] = []
    controller.progress.connect(lambda percent, message: progress.append((percent, message)))

    controller.run_validate(location)
    qtbot.waitUntil(lambda: bool(progress), timeout=2000)

    assert progress[-1][0] == 100


def test_create_flow_updates_real_main_window(tmp_path: Path, qtbot) -> None:
    window = _window(qtbot)
    target = tmp_path / "created"

    with patch("video2pptx.gui.main_window.QFileDialog.getExistingDirectory", return_value=str(target)):
        window._on_new_project()

    assert window._project_ctrl.project is not None
    assert window._project_ctrl.project.name == "created"
    assert "created" in window.windowTitle()


def test_video_changed_uses_qt_enabled_state(tmp_path: Path, qtbot) -> None:
    window = _window(qtbot)
    video = tmp_path / "video.mp4"
    video.touch()

    window._model.videoChanged.emit(str(video))

    assert window._btn_detect.isEnabled()
    assert window._btn_quick_preview.isEnabled()


def test_delete_resolves_display_index_to_slide_id(tmp_path: Path, qtbot) -> None:
    window = _window(qtbot)
    location = tmp_path / "uid"
    window._project_ctrl.create(tmp_path, "uid")
    slide_id = window._project_ctrl.project.add_slide(5.0)
    window._project_ctrl.save()
    window._model.open(str(location))
    window._timeline_ctrl.delete_slide = MagicMock(return_value=True)

    with patch.object(window, "_confirm", return_value=True):
        window._on_delete_slide(0)

    assert window._timeline_ctrl.delete_slide.call_args.args[1] == slide_id


def test_set_slide_image_persists_artifact_ref(tmp_path: Path) -> None:
    services = ApplicationServices()
    location = tmp_path / "frame"
    project = Project(name="frame", output_dir=str(location))
    slide_id = project.add_slide(5.0)
    services.repository.create(location, project)
    image = ArtifactRef.parse("slides/manual.png")
    image.resolve(location).parent.mkdir(parents=True)
    image.resolve(location).touch()
    controller = TimelineController(services)

    assert controller.set_slide_image(location, slide_id, image)
    reopened = services.repository.load(location)
    assert reopened.project.get_slide(slide_id).image == image


def test_project_save_reloads_revision_after_timeline_mutation(tmp_path: Path) -> None:
    services = ApplicationServices()
    project_controller = ProjectController(services)
    project_controller.create(tmp_path, "revision")
    location = tmp_path / "revision"
    timeline = TimelineController(services)
    errors: list[str] = []
    project_controller.errorOccurred.connect(errors.append)

    timeline.add_slide(location, 5.0)
    project_controller.save()

    assert errors == []


def test_main_window_is_below_step_8_loc_limit() -> None:
    source = Path("src/video2pptx/gui/main_window.py")
    assert len(source.read_text(encoding="utf-8").splitlines()) < 600


def test_playback_routes_to_video_player(qtbot) -> None:
    window = _window(qtbot)
    from video2pptx.debug.mcp_operations import clear_registry
    from video2pptx.debug.mcp_server import _handle_rpc, mcp_process_queue

    clear_registry()
    window._video_player.play = MagicMock()
    _handle_rpc(
        "tools/call",
        {"name": "video_play", "arguments": {}},
        window._model,
        window._model.timeline,
        window,
    )
    mcp_process_queue(window._model, window)

    window._video_player.play.assert_called_once_with()
