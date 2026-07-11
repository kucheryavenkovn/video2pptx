# FILE: src/video2pptx/application/services/detection_service.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Canonical CV detection use case applying a complete validated candidate set through the aggregate.
#   SCOPE: DetectionService.execute
#   DEPENDS: video2pptx.application.base, video2pptx.application.dto, video2pptx.application.errors,
#            video2pptx.application.ports.slide_detector, video2pptx.domain
#   LINKS: M-APP-DETECT, V-APP-DETECT, V-REF-APP-SERVICES
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   DetectionService - loads project, detects slides, replaces aggregate, saves with revision
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add revision-safe detection service
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path

from loguru import logger

from video2pptx.application.base import ServiceContext
from video2pptx.application.dto import ServiceResult
from video2pptx.application.errors import StageFailureError
from video2pptx.application.ports.slide_detector import SlideDetectorPort


class DetectionService:
    """Canonical detection use case — replace slides and invalidate downstream."""

    def __init__(
        self,
        detector: SlideDetectorPort,
        context: ServiceContext,
    ) -> None:
        self._detector = detector
        self._ctx = context

    def execute(
        self,
        project_location: Path,
        video_path: str,
        *,
        sample_fps: float,
        slide_roi: str,
        ignore_rois: list[str],
        threshold: float,
        min_stable_duration: float,
        min_slide_duration: float,
        dedupe_enabled: bool = True,
    ) -> ServiceResult:
        repo = self._ctx.repository
        if repo is None:
            return ServiceResult.fail("detect", "Repository not configured")

        try:
            loaded = repo.load(Path(project_location))
            self._ctx.check_cancelled("detect")

            project = loaded.project
            project.pipeline.start("detect")
            self._ctx.report_progress(10, "Starting detection")

            output = self._detector.detect(
                video_path,
                Path(project_location),
                sample_fps=sample_fps,
                slide_roi=slide_roi,
                ignore_rois=ignore_rois,
                threshold=threshold,
                min_stable_duration=min_stable_duration,
                min_slide_duration=min_slide_duration,
                dedupe_enabled=dedupe_enabled,
            )
            self._ctx.check_cancelled("detect")
            self._ctx.report_progress(70, f"Detected {len(output.slides)} candidates")

            project.replace_detected_slides(output.slides)
            project.score_timestamps = list(output.score_timestamps)
            project.score_values = list(output.score_values)
            project.pipeline.succeed("detect")

            save_result = repo.save(
                project,
                loaded.location,
                expected_revision=loaded.revision,
            )
            self._ctx.report_progress(100, "Detection saved")

            logger.info(
                f"[DetectionService] Detection done | slides={project.slide_count} "
                f"revision={save_result.revision}"
            )

            return ServiceResult.ok(
                "detect",
                data={
                    "slides_count": project.slide_count,
                    "video_duration": output.video_duration,
                },
                revision=save_result.revision,
                warnings=tuple(save_result.warnings),
            )
        except Exception as exc:
            logger.error(f"[DetectionService] Failed | error={exc}")
            raise StageFailureError("detect", str(exc), cause=exc) from exc
