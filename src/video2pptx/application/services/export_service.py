# FILE: src/video2pptx/application/services/export_service.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Canonical staged Markdown/PPTX exports from immutable aggregate snapshots with output validation.
#   SCOPE: ExportService.execute — dry_run and apply modes
#   DEPENDS: video2pptx.application.base, video2pptx.application.dto, video2pptx.application.errors,
#            video2pptx.application.ports.presentation_exporter, video2pptx.domain
#   LINKS: M-APP-EXPORT, V-APP-EXPORT, V-REF-APP-SERVICES
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ExportService - loads project, stages export, validates output, saves revision
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Preserve the canonical project title in exports
#   v1.0.0 - Add revision-safe export service with overwrite guard
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path

from loguru import logger

from video2pptx.application.base import ServiceContext
from video2pptx.application.dto import ServiceResult
from video2pptx.application.errors import StageFailureError
from video2pptx.application.ports.presentation_exporter import PresentationExporterPort


class ExportService:
    """Canonical export use case — stage Markdown/PPTX and save with revision."""

    def __init__(
        self,
        exporter: PresentationExporterPort,
        context: ServiceContext,
    ) -> None:
        self._exporter = exporter
        self._ctx = context

    def execute(
        self,
        project_location: Path,
        *,
        output_path: str = "",
        format: str = "markdown",
        overwrite: bool = True,
        dry_run: bool = False,
    ) -> ServiceResult:
        repo = self._ctx.repository
        if repo is None:
            return ServiceResult.fail("export", "Repository not configured")

        try:
            loaded = repo.load(Path(project_location))
            self._ctx.check_cancelled("export")

            project = loaded.project
            effective_output = output_path or f"{project_location}/output"

            if not overwrite and Path(effective_output).exists():
                return ServiceResult.fail(
                    "export",
                    f"Output path already exists and overwrite=False: {effective_output}",
                )

            stage_name = "markdown_export" if format == "markdown" else "pptx_export"
            project.pipeline.start(stage_name)
            self._ctx.report_progress(20, f"Exporting to {format}")

            slides_data = project.to_slides_dict()
            output = self._exporter.export(
                slides_data,
                effective_output,
                format=format,
                title=project.name,
            )
            self._ctx.check_cancelled("export")
            self._ctx.report_progress(70, "Export staged")

            if not dry_run:
                project.pipeline.succeed(stage_name)
                save_result = repo.save(
                    project,
                    loaded.location,
                    expected_revision=loaded.revision,
                )
                self._ctx.report_progress(100, "Export saved")
                revision = save_result.revision
                warnings = tuple(save_result.warnings)
            else:
                revision = loaded.revision
                warnings = output.warnings

            logger.info(
                f"[ExportService] Export done | format={format} slides={output.slide_count} "
                f"dry_run={dry_run} output={output.output_path}"
            )

            return ServiceResult.ok(
                "export",
                data={
                    "format": output.format,
                    "output_path": output.output_path,
                    "slide_count": output.slide_count,
                    "image_count": output.image_count,
                    "dry_run": dry_run,
                },
                revision=revision,
                warnings=warnings,
            )
        except Exception as exc:
            logger.error(f"[ExportService] Failed | error={exc}")
            raise StageFailureError("export", str(exc), cause=exc) from exc
