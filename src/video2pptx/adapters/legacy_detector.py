# FILE: src/video2pptx/adapters/legacy_detector.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Wrap old run_detect_slides pipeline behind SlideDetectorPort
#   SCOPE: LegacySlideDetector.detect — detect slides, save screenshots, return DetectionOutput
#   DEPENDS: video2pptx.application.ports.slide_detector, video2pptx.detect_slides,
#            video2pptx.domain.slide
#   LINKS: M-PORT-DETECTOR, M-ADAPTERS
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   LegacySlideDetector - adapt legacy CV detection to SlideDetectorPort
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.2.0 - Pass analysis_max_side into AppConfig video (Phase 19)
# END_CHANGE_SUMMARY

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from video2pptx.application.ports.slide_detector import DetectionOutput, SlideDetectorPort
from video2pptx.config import AppConfig
from video2pptx.detect_slides import run_detect_slides
from video2pptx.domain.slide import Slide


class LegacySlideDetector(SlideDetectorPort):
    """Run old CV detection pipeline, save screenshots, return domain Slides.

    Screenshots are written to ``out_dir / slides/`` as a side effect.
    No project state is modified — those are managed by DetectionService.
    """

    def detect(
        self,
        video_path: str,
        out_dir: Path,
        *,
        sample_fps: float,
        slide_roi: str,
        ignore_rois: list[str],
        threshold: float,
        min_stable_duration: float,
        min_slide_duration: float,
        dedupe_enabled: bool,
        decoder_backend: str = "auto",
        analysis_max_side: int | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> DetectionOutput:
        cfg = AppConfig(
            video={
                "sample_fps": sample_fps,
                "decoder_backend": decoder_backend,
                "analysis_max_side": analysis_max_side,
            },
            detection={
                "threshold": threshold,
                "min_stable_duration": min_stable_duration,
                "min_slide_duration": min_slide_duration,
                "slide_roi": slide_roi,
                "ignore_rois": ignore_rois,
                "dedupe_enabled": dedupe_enabled,
            },
        )

        doc = run_detect_slides(
            video_path=Path(video_path),
            out_dir=out_dir,
            cfg=cfg,
            progress_callback=progress_callback,
        )

        slides_domain = [Slide.from_dict(s.model_dump(mode="json")) for s in doc.slides]

        return DetectionOutput(
            slides=slides_domain,
            score_timestamps=list(doc.score_timestamps),
            score_values=list(doc.score_values),
            video_duration=doc.video.duration,
            screenshots_dir=out_dir / "slides",
        )
