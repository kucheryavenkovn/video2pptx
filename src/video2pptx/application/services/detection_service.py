# FILE: src/video2pptx/application/services/detection_service.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Canonical CV detection use case with project-bound input resolution.
#   SCOPE: DetectionService.execute — resolves video_path, decoder_backend, and all detection
#          settings from canonical Project when command overrides are absent.
#   DEPENDS: video2pptx.application.base, video2pptx.application.dto, video2pptx.application.errors,
#            video2pptx.application.ports.slide_detector, video2pptx.domain
#   LINKS: M-APP-DETECT, V-REF-DETECTION-INPUT
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   DetectionService - loads project, resolves inputs, detects slides, saves with revision
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.2.0 - Resolve analysis_max_side from Project.detection (Phase 19)
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
from video2pptx.application.ports.slide_detector import SlideDetectorPort


class DetectionService:
    """Canonical detection use case with project-bound input resolution.

    # START_CONTRACT: DetectionService.execute
    #   PURPOSE: Detect slides using canonical Project settings, resolving all inputs
    #            from Project.detection and Project.video_path when overrides are None.
    #   INPUTS: { project_location: Path, video_path: str|None, sample_fps: float|str|None,
    #             slide_roi: str|None, ignore_rois: list[str]|None, threshold: float|str|None,
    #             min_stable_duration: float|None, min_slide_duration: float|None,
    #             dedupe_enabled: bool|None, decoder_backend: str|None,
    #             analysis_max_side: int|None }
    #   OUTPUTS: ServiceResult with slides_count, effective_config, effective_video_path, warnings
    #   SIDE_EFFECTS: mutates Project, saves via repository
    #   LINKS: M-APP-DETECT
    # END_CONTRACT: DetectionService.execute
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
        video_path: str | None = None,
        *,
        sample_fps: float | str | None = None,
        slide_roi: str | None = None,
        ignore_rois: list[str] | None = None,
        threshold: float | str | None = None,
        min_stable_duration: float | None = None,
        min_slide_duration: float | None = None,
        dedupe_enabled: bool | None = None,
        decoder_backend: str | None = None,
        analysis_max_side: int | None = None,
    ) -> ServiceResult:
        repo = self._ctx.repository
        if repo is None:
            return ServiceResult.fail("detect", "Repository not configured")

        try:
            loaded = repo.load(Path(project_location))
            self._ctx.check_cancelled("detect")

            project = loaded.project
            dc = project.detection

            # START_BLOCK_RESOLVE_INPUTS
            effective_video = resolve_project_input(video_path, project.video_path, field="video")
            eff_decoder = resolve_detection_override(decoder_backend, dc.decoder_backend)
            eff_sample_fps = resolve_detection_override(sample_fps, dc.sample_fps)
            eff_slide_roi = normalize_roi(resolve_detection_override(slide_roi, dc.slide_roi))
            eff_ignore_rois = dc.ignore_rois if ignore_rois is None else ignore_rois
            eff_threshold = resolve_detection_override(threshold, dc.threshold)
            eff_min_stable = resolve_detection_override(min_stable_duration, dc.min_stable_duration)
            eff_min_slide = resolve_detection_override(min_slide_duration, dc.min_slide_duration)
            eff_dedupe = resolve_detection_override(dedupe_enabled, dc.dedupe_enabled)
            eff_analysis_max_side = resolve_detection_override(
                analysis_max_side, dc.analysis_max_side
            )
            # END_BLOCK_RESOLVE_INPUTS

            project.pipeline.start("detect")
            self._ctx.report_progress(10, "Starting detection")
            logger.info(
                "[DetectionService] Resolved input | project_video={} override_video={} effective_video={}",
                project.video_path or "(none)", video_path or "(none)", effective_video,
            )
            logger.info(
                "[DetectionService] Effective config | sample_fps={} threshold={} "
                "min_slide={} min_stable={} dedupe={} roi={} decoder={} analysis_max_side={}",
                eff_sample_fps, eff_threshold, eff_min_slide,
                eff_min_stable, eff_dedupe, eff_slide_roi, eff_decoder, eff_analysis_max_side,
            )

            # START_BLOCK_DETECTOR_CALL
            video_path_resolved = effective_video
            output = self._detector.detect(
                video_path_resolved,
                Path(project_location),
                sample_fps=eff_sample_fps,
                slide_roi=eff_slide_roi,
                ignore_rois=eff_ignore_rois,
                threshold=eff_threshold,
                min_stable_duration=eff_min_stable,
                min_slide_duration=eff_min_slide,
                dedupe_enabled=eff_dedupe,
                decoder_backend=eff_decoder,
                analysis_max_side=eff_analysis_max_side,
            )
            # END_BLOCK_DETECTOR_CALL
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
                    "effective_video_path": effective_video,
                    "effective_config": {
                        "sample_fps": eff_sample_fps,
                        "threshold": eff_threshold,
                        "min_slide_duration": eff_min_slide,
                        "min_stable_duration": eff_min_stable,
                        "dedupe_enabled": eff_dedupe,
                        "decoder_backend": eff_decoder,
                    },
                },
                revision=save_result.revision,
                warnings=tuple(warnings),
            )
        except PreconditionError:
            raise
        except Exception as exc:
            logger.error(f"[DetectionService] Failed | error={exc}")
            raise StageFailureError("detect", str(exc), cause=exc) from exc
