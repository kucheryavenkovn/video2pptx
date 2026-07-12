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
    """Canonical detection use case — replace slides and invalidate downstream.

    Uses project's canonical DetectionConfig as defaults; caller overrides are optional.
    """

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
        video_path: str = "",
        *,
        sample_fps: float | str | None = None,
        slide_roi: str | None = None,
        ignore_rois: list[str] | None = None,
        threshold: float | str | None = None,
        min_stable_duration: float | None = None,
        min_slide_duration: float | None = None,
        dedupe_enabled: bool | None = None,
    ) -> ServiceResult:
        repo = self._ctx.repository
        if repo is None:
            return ServiceResult.fail("detect", "Repository not configured")

        try:
            loaded = repo.load(Path(project_location))
            self._ctx.check_cancelled("detect")

            project = loaded.project
            dc = project.detection
            eff_sample_fps = sample_fps if sample_fps is not None else dc.sample_fps
            eff_slide_roi = slide_roi if slide_roi is not None else dc.slide_roi
            eff_ignore_rois = ignore_rois if ignore_rois is not None else dc.ignore_rois
            eff_threshold = threshold if threshold is not None else dc.threshold
            eff_min_stable = min_stable_duration if min_stable_duration is not None else dc.min_stable_duration
            eff_min_slide = min_slide_duration if min_slide_duration is not None else dc.min_slide_duration
            eff_dedupe = dedupe_enabled if dedupe_enabled is not None else dc.dedupe_enabled

            project.pipeline.start("detect")
            self._ctx.report_progress(10, "Starting detection")
            logger.info(
                "[DetectionService] Effective config | sample_fps={} threshold={} "
                "min_slide={} min_stable={} dedupe={} roi={}",
                eff_sample_fps, eff_threshold, eff_min_slide,
                eff_min_stable, eff_dedupe, eff_slide_roi,
            )

            output = self._detector.detect(
                video_path,
                Path(project_location),
                sample_fps=eff_sample_fps,
                slide_roi=eff_slide_roi,
                ignore_rois=eff_ignore_rois,
                threshold=eff_threshold,
                min_stable_duration=eff_min_stable,
                min_slide_duration=eff_min_slide,
                dedupe_enabled=eff_dedupe,
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

            warnings = list(save_result.warnings or [])
            if len(output.score_values) > 100 and len(output.slides) == 0:
                max_score = max(output.score_values)
                if max_score < float(eff_threshold) if isinstance(eff_threshold, (int, float)) else 0.0:
                    warnings.append(
                        f"No slide changes detected. Configured threshold={eff_threshold} is above "
                        f"maximum observed score={max_score:.4f}. "
                        "Check detection threshold or use threshold=auto."
                    )

            return ServiceResult.ok(
                "detect",
                data={
                    "slides_count": project.slide_count,
                    "video_duration": output.video_duration,
                    "effective_config": {
                        "sample_fps": eff_sample_fps,
                        "threshold": eff_threshold,
                        "min_slide_duration": eff_min_slide,
                        "min_stable_duration": eff_min_stable,
                        "dedupe_enabled": eff_dedupe,
                    },
                },
                revision=save_result.revision,
                warnings=tuple(warnings),
            )
        except Exception as exc:
            logger.error(f"[DetectionService] Failed | error={exc}")
            raise StageFailureError("detect", str(exc), cause=exc) from exc
