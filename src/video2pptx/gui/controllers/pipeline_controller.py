# FILE: src/video2pptx/gui/controllers/pipeline_controller.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: QObject-based pipeline stage controller — runs preview, detect, align, notes,
#            export, validate, and auto stages through ApplicationServices with Qt progress signals.
#   SCOPE: Execute individual stage services (preview/detect/align/notes/export/validate/auto)
#          via ApplicationServices, forwarding progress updates and ServiceResult through Qt signals.
#          Does NOT manage threading — the caller (MainWindow or QThread wrapper) decides threading.
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

from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject, Signal

from video2pptx.application.base import ServiceContext
from video2pptx.application.cancellation import CancellationToken
from video2pptx.application.dto import ProgressUpdate, ServiceResult
from video2pptx.bootstrap.application import ApplicationServices
from video2pptx.infrastructure.persistence.errors import ProjectNotFound


class SignalProgressObserver(QObject):
    """QObject that implements ProgressObserver and emits a Qt progress signal.

    Pass this observer's ``on_progress`` to ApplicationServices so that
    PipelineController (or any caller) can connect to its signal.
    """

    progressUpdated = Signal(int, str)  # percent, message

    def on_progress(self, update: ProgressUpdate) -> None:
        self.progressUpdated.emit(update.percent, update.message)


class PipelineController(QObject):
    """Qt-aware controller for running pipeline stages through ApplicationServices.

    Each ``run_*`` method creates a temporary ServiceContext with a fresh
    SignalProgressObserver, calls the corresponding ApplicationServices method,
    and emits ``stageFinished`` with the result.  Errors emit ``error``.

    Usage::

        ctrl = PipelineController(services)
        ctrl.progress.connect(on_progress)
        ctrl.stageFinished.connect(on_finished)

        # synchronous — wrap in QThread for GUI responsiveness
        ctrl.run_detect("/path/to/project", sample_fps=2.0)

    Signals are thread-safe (queued connections if crossing threads).
    """

    progress = Signal(int, str)          # percent, message
    stageFinished = Signal(ServiceResult)  # result from the finished stage
    error = Signal(str)                   # error message

    def __init__(
        self,
        services: ApplicationServices,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._services = services

    # -- individual stage runners -------------------------------------------

    def run_preview(
        self,
        project_location: str | Path,
        *,
        video_path: str = "",
        sample_fps: float = 2.0,
        slide_roi: str = "",
        ignore_rois: list[str] | None = None,
        threshold: float = 0.95,
        min_stable_duration: float = 2.0,
    ) -> None:
        self._run(
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
        sample_fps: float = 2.0,
        slide_roi: str = "",
        ignore_rois: list[str] | None = None,
        threshold: float = 0.95,
        min_stable_duration: float = 2.0,
        min_slide_duration: float = 2.0,
        dedupe_enabled: bool = True,
    ) -> None:
        self._run(
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
        self._run(
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
        self._run(
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
        self._run(
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
        self._run(
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
        self._run(
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

    def _run(self, stage: str, project_location: str | Path, **params) -> None:
        """Create a scoped ServiceContext, invoke the stage, and emit results."""
        location = Path(project_location)

        observer = SignalProgressObserver()
        observer.progressUpdated.connect(self.progress)
        ctx = ServiceContext(
            repository=self._services.repository,
            observer=observer,
            cancellation=CancellationToken(),
        )

        try:
            result = self._dispatch_stage(stage, location, ctx, params)
        except ProjectNotFound as exc:
            logger.error("[PipelineController][{}] Project not found | location={}", stage, location)
            self.error.emit(str(exc))
            return
        except Exception as exc:
            logger.exception("[PipelineController][{}] Unhandled error | location={}", stage, location)
            self.error.emit(str(exc))
            return

        if result.success:
            self.stageFinished.emit(result)
        else:
            self.error.emit(result.error or f"{stage} failed")

    def _dispatch_stage(
        self,
        stage: str,
        location: Path,
        ctx: ServiceContext,
        params: dict,
    ) -> ServiceResult:
        services = self._services
        if stage == "preview":
            return services.preview_service.execute(location, **params)
        elif stage == "detect":
            return services.detection_service.execute(location, **params)
        elif stage == "align":
            return services.alignment_service.execute(location, **params)
        elif stage == "notes":
            return services.notes_service.execute(location, **params)
        elif stage == "export":
            return services.export_service.execute(location, **params)
        elif stage == "validate":
            return services.validation_service.execute(location, **params)
        elif stage == "auto":
            return services.auto_service.execute(location, **params)
        else:
            raise ValueError(f"Unknown pipeline stage: {stage}")
