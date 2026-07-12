# FILE: src/video2pptx/application/services/preview_service.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Canonical waveform-only preview use case with revision-safe persistence and no slide invalidation.
#   SCOPE: PreviewService.execute
#   DEPENDS: video2pptx.application.base, video2pptx.application.dto, video2pptx.application.errors,
#            video2pptx.application.ports.preview_analyzer
#   LINKS: M-APP-PREVIEW, V-APP-PREVIEW, V-REF-APP-SERVICES
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   PreviewService - loads project, computes preview scores, saves with revision
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add revision-safe preview service
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path

from loguru import logger

from video2pptx.application.base import (
    ServiceContext,
    normalize_roi,
    resolve_detection_override,
    resolve_project_input,
)
from video2pptx.application.dto import ServiceResult
from video2pptx.application.errors import PreconditionError, StageFailureError
from video2pptx.application.ports.preview_analyzer import PreviewAnalyzerPort


class PreviewService:
    """Canonical preview use case — compute scores without creating slides."""

    def __init__(
        self,
        analyzer: PreviewAnalyzerPort,
        context: ServiceContext,
    ) -> None:
        self._analyzer = analyzer
        self._ctx = context

    def execute(
        self,
        project_location: Path,
        video_path: str | None = None,
        *,
        sample_fps: float | str | None = None,
        slide_roi: str | None = None,
        ignore_rois: list[str] | None = None,
        threshold: float | str | None = None,
        min_stable_duration: float | None = None,
    ) -> ServiceResult:
        repo = self._ctx.repository
        if repo is None:
            return ServiceResult.fail("preview", "Repository not configured")

        try:
            loaded = repo.load(Path(project_location))
            self._ctx.check_cancelled("preview")

            project = loaded.project
            dc = project.detection
            effective_video = resolve_project_input(video_path, project.video_path, field="video")
            eff_fps = resolve_detection_override(sample_fps, dc.sample_fps)
            eff_roi = normalize_roi(resolve_detection_override(slide_roi, dc.slide_roi))
            eff_ignore = dc.ignore_rois if ignore_rois is None else ignore_rois
            eff_threshold = resolve_detection_override(threshold, dc.threshold)
            eff_stable = resolve_detection_override(min_stable_duration, dc.min_stable_duration)

            project.pipeline.start("preview")
            self._ctx.report_progress(10, "Starting preview")

            output = self._analyzer.analyze(
                effective_video,
                sample_fps=eff_fps,
                slide_roi=eff_roi,
                ignore_rois=eff_ignore,
                threshold=eff_threshold,
                min_stable_duration=eff_stable,
            )
            self._ctx.check_cancelled("preview")
            self._ctx.report_progress(80, "Scores computed")

            project.score_timestamps = list(output.score_timestamps)
            project.score_values = list(output.score_values)
            project.pipeline.succeed("preview")

            save_result = repo.save(
                project,
                loaded.location,
                expected_revision=loaded.revision,
            )
            self._ctx.report_progress(100, "Preview saved")

            logger.info(
                f"[PreviewService] Preview done | scores={len(output.score_timestamps)} "
                f"revision={save_result.revision}"
            )

            return ServiceResult.ok(
                "preview",
                data={
                    "score_count": len(output.score_timestamps),
                    "video_duration": output.video_duration,
                },
                revision=save_result.revision,
                warnings=tuple(save_result.warnings),
            )
        except PreconditionError:
            raise
        except Exception as exc:
            logger.error(f"[PreviewService] Failed | error={exc}")
            raise StageFailureError("preview", str(exc), cause=exc) from exc
