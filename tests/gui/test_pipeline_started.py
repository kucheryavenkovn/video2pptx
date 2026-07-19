# FILE: tests/gui/test_pipeline_started.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Phase 21 Wave 3 — operationStarted fires before worker thread starts
#   ROLE: TEST
#   LINKS: M-GUI-PIPELINE-CTRL, Phase-21
# END_MODULE_CONTRACT

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, create_autospec

import pytest

from video2pptx.application.dto import ServiceResult
from video2pptx.bootstrap.application import ApplicationServices
from video2pptx.gui.controllers.pipeline_controller import PipelineController


@pytest.fixture
def services() -> MagicMock:
    svc = create_autospec(ApplicationServices, instance=True)
    svc.detection_service = MagicMock()
    svc.repository = MagicMock()

    def scoped(context):
        svc.context = context
        return svc

    svc.scoped.side_effect = scoped
    return svc


def test_operation_started_before_first_progress(services, qtbot) -> None:
    events: list[str] = []
    controller = PipelineController(services=services)

    def on_started(stage: str) -> None:
        events.append(f"started:{stage}")

    def on_progress(pct: int, msg: str) -> None:
        events.append(f"progress:{pct}")

    controller.operationStarted.connect(on_started)
    controller.progress.connect(on_progress)

    def execute(*args, **kwargs):
        # Progress during worker run — must happen after operationStarted
        controller._services.context.report_progress(10, "Starting detection")
        return ServiceResult.ok("detect", data={"slides_count": 1})

    services.detection_service.execute.side_effect = execute

    result = controller.run_detect(Path("/tmp/phase21-detect"))
    assert result.accepted is True
    qtbot.waitUntil(lambda: any(e.startswith("progress:") for e in events), timeout=3000)
    qtbot.waitUntil(lambda: controller._thread is None, timeout=10000)

    assert events[0].startswith("started:")
    assert any(e.startswith("progress:") for e in events)
    started_idx = next(i for i, e in enumerate(events) if e.startswith("started:"))
    progress_idx = next(i for i, e in enumerate(events) if e.startswith("progress:"))
    assert started_idx < progress_idx
