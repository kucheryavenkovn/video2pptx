# FILE: src/video2pptx/application/services/auto_service.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Coordinate full/resume/force by composing stage services without duplicating stage algorithms.
#   SCOPE: AutoService.execute — orchestrates preview → detect → align → notes → export → validate
#   DEPENDS: video2pptx.application.base, video2pptx.application.dto, video2pptx.application.errors,
#            video2pptx.application.services.*
#   LINKS: M-APP-AUTO, V-APP-AUTO, V-REF-APP-SERVICES
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   AutoService - orchestrates stage services for full/resume/force modes
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add auto orchestration service
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path

from loguru import logger

from video2pptx.application.base import ServiceContext
from video2pptx.application.dto import ServiceResult
from video2pptx.application.errors import StageFailureError
from video2pptx.application.services.alignment_service import AlignmentService
from video2pptx.application.services.detection_service import DetectionService
from video2pptx.application.services.export_service import ExportService
from video2pptx.application.services.notes_service import NotesService
from video2pptx.application.services.preview_service import PreviewService
from video2pptx.application.services.validation_service import ValidationService

_STAGES = ("preview", "detect", "align", "notes", "export", "validate")


class AutoService:
    """Orchestrate stage services for full/resume/force modes."""

    def __init__(
        self,
        context: ServiceContext,
        preview_service: PreviewService,
        detection_service: DetectionService,
        alignment_service: AlignmentService,
        notes_service: NotesService,
        export_service: ExportService,
        validation_service: ValidationService,
    ) -> None:
        self._ctx = context
        self._preview = preview_service
        self._detect = detection_service
        self._align = alignment_service
        self._notes = notes_service
        self._export = export_service
        self._validate = validation_service

    def execute(
        self,
        project_location: Path,
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
    ) -> ServiceResult:
        repo = self._ctx.repository
        if repo is None:
            return ServiceResult.fail("auto", "Repository not configured")

        results: dict[str, ServiceResult] = {}
        failed_stage: str | None = None

        if mode == "force":
            # Load and invalidate all SUCCEEDED stages
            loaded = repo.load(project_location)
            for stage in _STAGES:
                pipeline_stage = _pipeline_stage_name(stage)
                loaded.project.pipeline.start(pipeline_stage)
            repo.save(loaded.project, loaded.location, expected_revision=loaded.revision)

        for stage in _STAGES:
            if failed_stage is not None:
                self._skip(stage, results, f"halted after {failed_stage}")
                continue
            if mode == "resume":
                loaded = repo.load(project_location)
                pipeline_stage = _pipeline_stage_name(stage)
                if not loaded.project.pipeline.can_run(pipeline_stage):
                    self._skip(stage, results, "already SUCCEEDED")
                    continue

            self._ctx.report_progress(0, f"Running {stage}")
            result = self._run_stage(
                stage,
                project_location,
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
            results[stage] = result
            if not result.success:
                failed_stage = stage
                logger.error(f"[AutoService] Stage {stage} failed | error={result.error}")
                # Mark remaining as skipped
                remaining = _STAGES[_STAGES.index(stage) + 1:]
                for rs in remaining:
                    self._skip(rs, results, f"halted after {failed_stage}")
                break

        self._ctx.report_progress(100, "Auto complete")
        all_ok = failed_stage is None

        logger.info(
            f"[AutoService] Done | mode={mode} success={all_ok} "
            f"failed_stage={failed_stage} stages={list(results.keys())}"
        )

        return ServiceResult.ok(
            "auto",
            data={
                "mode": mode,
                "success": all_ok,
                "failed_stage": failed_stage,
                "results": {k: v.to_dict() for k, v in results.items()},
            },
        )

    def _run_stage(
        self,
        stage: str,
        location: Path,
        **kwargs,
    ) -> ServiceResult:
        try:
            if stage == "preview":
                return self._preview.execute(
                    location, kwargs["video_path"],
                    sample_fps=kwargs["sample_fps"],
                    slide_roi=kwargs["slide_roi"],
                    ignore_rois=kwargs["ignore_rois"],
                    threshold=kwargs["threshold"],
                    min_stable_duration=kwargs["min_stable_duration"],
                )
            elif stage == "detect":
                return self._detect.execute(
                    location, kwargs["video_path"],
                    sample_fps=kwargs["sample_fps"],
                    slide_roi=kwargs["slide_roi"],
                    ignore_rois=kwargs["ignore_rois"],
                    threshold=kwargs["threshold"],
                    min_stable_duration=kwargs["min_stable_duration"],
                    min_slide_duration=kwargs["min_slide_duration"],
                    dedupe_enabled=kwargs["dedupe_enabled"],
                )
            elif stage == "align":
                return self._align.execute(
                    location, kwargs["subtitles_path"],
                    dry_run=kwargs["dry_run"],
                )
            elif stage == "notes":
                return self._notes.execute(
                    location, subtitles_path=kwargs["subtitles_path"],
                    mode=kwargs["notes_mode"],
                )
            elif stage == "export":
                return self._export.execute(
                    location,
                    output_path=kwargs["export_output_path"],
                    format=kwargs["export_format"],
                    overwrite=True,
                    dry_run=kwargs["dry_run"],
                )
            elif stage == "validate":
                return self._validate.execute(location)
            else:
                return ServiceResult.fail(stage, f"Unknown stage: {stage}")
        except StageFailureError as e:
            return ServiceResult.fail(stage, str(e))
        except Exception as e:
            logger.error(f"[AutoService] Unexpected failure in {stage} | error={e}")
            return ServiceResult.fail(stage, str(e))

    def _skip(
        self,
        stage: str,
        results: dict[str, ServiceResult],
        reason: str,
    ) -> None:
        results[stage] = ServiceResult(success=True, stage=stage, data={"skipped": True, "reason": reason})


def _pipeline_stage_name(stage: str) -> str:
    mapping = {
        "export": "markdown_export",
        "validate": "auto",
    }
    return mapping.get(stage, stage)
