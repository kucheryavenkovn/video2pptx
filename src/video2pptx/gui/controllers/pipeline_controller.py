# FILE: src/video2pptx/gui/controllers/pipeline_controller.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: QObject-based pipeline stage controller — runs preview, detect, align, notes,
#            export, validate, and auto stages through ApplicationServices with Qt progress signals.
#   SCOPE: Execute individual stage services (preview/detect/align/notes/export/validate/auto)
#          via ApplicationServices, forwarding progress updates and ServiceResult through Qt signals.
#          Own QThread lifecycle and operation-scoped progress/cancellation context.
#   DEPENDS: PySide6.QtCore, video2pptx.bootstrap.application,
#            video2pptx.application.dto, video2pptx.application.observer
#   LINKS: M-GUI-PIPELINE-CTRL
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   SignalProgressObserver - QObject implementing ProgressObserver protocol, emits Qt signal
#   PipelineController - run stage services with progress/finished/error Qt signals
# END_MODULE_MAP

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject, QThread, QTimer, Signal

from video2pptx.application.base import ServiceContext
from video2pptx.application.cancellation import CancellationToken
from video2pptx.application.dto import ProgressUpdate, ServiceResult
from video2pptx.bootstrap.application import ApplicationServices
from video2pptx.gui.controllers.pipeline_worker import PipelineWorker


@dataclass
class PipelineStartResult:
    """Result of attempting to start a pipeline operation."""

    accepted: bool
    requested_stage: str
    active_stage: str | None = None


class SignalProgressObserver(QObject):
    """QObject that implements ProgressObserver and emits a Qt progress signal."""

    progressUpdated = Signal(int, str)  # percent, message

    def on_progress(self, update: ProgressUpdate) -> None:
        self.progressUpdated.emit(update.percent, update.message)


class PipelineController(QObject):
    """Qt-aware controller for running pipeline stages through ApplicationServices.

    Owns operation lifecycle: busy state, active stage, cancellation.
    Signals are thread-safe (queued connections if crossing threads).
    """

    progress = Signal(int, str)          # percent, message
    stageFinished = Signal(ServiceResult)  # result from the finished stage
    error = Signal(str)                   # error message
    busyChanged = Signal(bool)            # operation started/finished
    operationStarted = Signal(str)        # stage name when accepted
    operationRejected = Signal(str, str)  # (requested_stage, active_stage)

    def __init__(
        self,
        services: ApplicationServices,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._services = services
        self._thread: QThread | None = None
        self._worker: PipelineWorker | None = None
        self._cancellation: CancellationToken | None = None
        self._observer: SignalProgressObserver | None = None
        self._active_stage: str | None = None

    @property
    def is_busy(self) -> bool:
        return self._thread is not None

    @property
    def active_stage(self) -> str | None:
        return self._active_stage

    # -- individual stage runners -------------------------------------------

    def run_preview(
        self,
        project_location: str | Path,
        *,
        video_path: str = "",
        sample_fps: float | str | None = None,
        slide_roi: str | None = None,
        ignore_rois: list[str] | None = None,
        threshold: float | str | None = None,
        min_stable_duration: float | None = None,
    ) -> PipelineStartResult:
        return self._run(
            "preview",
            project_location,
            video_path=video_path,
            sample_fps=sample_fps,
            slide_roi=slide_roi,
            ignore_rois=ignore_rois or [],
            threshold=threshold,
            min_stable_duration=min_stable_duration,
        )

    def run_detect(
        self,
        project_location: str | Path,
        *,
        video_path: str = "",
        sample_fps: float | str | None = None,
        slide_roi: str | None = None,
        ignore_rois: list[str] | None = None,
        threshold: float | str | None = None,
        min_stable_duration: float | None = None,
        min_slide_duration: float | None = None,
        dedupe_enabled: bool | None = None,
    ) -> PipelineStartResult:
        return self._run(
            "detect",
            project_location,
            video_path=video_path,
            sample_fps=sample_fps,
            slide_roi=slide_roi,
            ignore_rois=ignore_rois or [],
            threshold=threshold,
            min_stable_duration=min_stable_duration,
            min_slide_duration=min_slide_duration,
            dedupe_enabled=dedupe_enabled,
        )

    def run_align(
        self,
        project_location: str | Path,
        *,
        subtitles_path: str = "",
        dry_run: bool = False,
        max_shift_sec: float = 3.0,
        include_manual: bool = False,
    ) -> None:
        return self._run(
            "align",
            project_location,
            subtitles_path=subtitles_path,
            dry_run=dry_run,
            max_shift_sec=max_shift_sec,
            include_manual=include_manual,
        )

    def run_notes(
        self,
        project_location: str | Path,
        *,
        subtitles_path: str = "",
        mode: str = "basic",
    ) -> None:
        return self._run(
            "notes",
            project_location,
            subtitles_path=subtitles_path,
            mode=mode,
        )

    def run_export(
        self,
        project_location: str | Path,
        *,
        output_path: str = "",
        format: str = "markdown",
        overwrite: bool = True,
        dry_run: bool = False,
    ) -> None:
        return self._run(
            "export",
            project_location,
            output_path=output_path,
            format=format,
            overwrite=overwrite,
            dry_run=dry_run,
        )

    def run_validate(
        self,
        project_location: str | Path,
        *,
        check_storage: bool = True,
        check_aggregate: bool = True,
        check_media: bool = True,
        check_artifacts: bool = True,
        check_exports: bool = True,
    ) -> None:
        return self._run(
            "validate",
            project_location,
            check_storage=check_storage,
            check_aggregate=check_aggregate,
            check_media=check_media,
            check_artifacts=check_artifacts,
            check_exports=check_exports,
        )

    def run_auto(
        self,
        project_location: str | Path,
        *,
        mode: str = "full",
        video_path: str = "",
        subtitles_path: str = "",
        sample_fps: float = 2.0,
        slide_roi: str = "",
        ignore_rois: list[str] | None = None,
        threshold: float = 0.95,
        min_stable_duration: float = 2.0,
        min_slide_duration: float = 2.0,
        dedupe_enabled: bool = True,
        notes_mode: str = "basic",
        export_format: str = "markdown",
        export_output_path: str = "",
        dry_run: bool = False,
    ) -> None:
        return self._run(
            "auto",
            project_location,
            mode=mode,
            video_path=video_path,
            subtitles_path=subtitles_path,
            sample_fps=sample_fps,
            slide_roi=slide_roi,
            ignore_rois=ignore_rois or [],
            threshold=threshold,
            min_stable_duration=min_stable_duration,
            min_slide_duration=min_slide_duration,
            dedupe_enabled=dedupe_enabled,
            notes_mode=notes_mode,
            export_format=export_format,
            export_output_path=export_output_path,
            dry_run=dry_run,
        )

    # -- internal dispatch --------------------------------------------------

    def _run(self, stage: str, project_location: str | Path, **params) -> PipelineStartResult:
        """Schedule a stage with a scoped context. Returns PipelineStartResult."""
        if self._thread is not None:
            rejected = PipelineStartResult(
                accepted=False, requested_stage=stage, active_stage=self._active_stage
            )
            self.operationRejected.emit(stage, self._active_stage or "")
            return rejected

        location = Path(project_location)
        observer = SignalProgressObserver(self)
        observer.progressUpdated.connect(self.progress.emit)
        cancellation = CancellationToken()
        ctx = ServiceContext(
            repository=self._services.repository,
            observer=observer,
            cancellation=cancellation,
        )
        scoped = self._services.scoped(ctx)
        thread = QThread(self)
        worker = PipelineWorker(scoped, stage, location, params)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.completed.connect(self._finish)
        worker.failed.connect(self._fail)
        worker.completed.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._operation_stopped)
        self._active_stage = stage
        self._observer = observer
        self._cancellation = cancellation
        self._thread = thread
        self._worker = worker
        self.busyChanged.emit(True)
        self.operationStarted.emit(stage)
        thread.start()
        return PipelineStartResult(accepted=True, requested_stage=stage, active_stage=stage)

    def cancel(self) -> None:
        if self._cancellation is not None:
            self._cancellation.trigger()

    def _finish(self, result: ServiceResult) -> None:
        self.stageFinished.emit(result)

    def _fail(self, message: str) -> None:
        logger.error("[PipelineController][_fail] Pipeline failed | error={}", message)
        self.error.emit(message)

    def _operation_stopped(self) -> None:
        QTimer.singleShot(0, self._clear_operation)

    def _clear_operation(self) -> None:
        self._active_stage = None
        self._worker = None
        self._thread = None
        self._observer = None
        self._cancellation = None
        self.busyChanged.emit(False)
