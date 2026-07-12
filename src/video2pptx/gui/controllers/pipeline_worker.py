# FILE: src/video2pptx/gui/controllers/pipeline_worker.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Execute one operation-scoped application service stage on a QThread.
#   SCOPE: Stage dispatch and result/error emission; no thread creation or GUI mutation.
#   DEPENDS: PySide6.QtCore, M-APP-BOOTSTRAP
#   LINKS: M-GUI-PIPELINE-WORKER, V-REF-GUI-ADAPTER
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   PipelineWorker - QObject worker that dispatches one stage and emits its result
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from video2pptx.application.dto import ServiceResult
from video2pptx.bootstrap.application import ApplicationServices


class PipelineWorker(QObject):
    """QThread-bound execution object for one pipeline stage."""

    completed = Signal(ServiceResult)
    failed = Signal(str)

    def __init__(
        self,
        services: ApplicationServices,
        stage: str,
        location: Path,
        params: dict,
    ) -> None:
        super().__init__()
        self._services = services
        self._stage = stage
        self._location = location
        self._params = params

    @Slot()
    def run(self) -> None:
        try:
            service = getattr(self._services, f"{self._service_name()}_service")
            result = service.execute(self._location, **self._params)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        if result.success:
            self.completed.emit(result)
        else:
            self.failed.emit(result.error or f"{self._stage} failed")

    def _service_name(self) -> str:
        return {"detect": "detection", "align": "alignment", "validate": "validation"}.get(
            self._stage, self._stage
        )
