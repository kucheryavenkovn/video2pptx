# FILE: src/video2pptx/adapters/legacy_preview.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Wrap old run_preview pipeline behind PreviewAnalyzerPort
#   SCOPE: LegacyPreviewAnalyzer.analyze — compute score waveform from video
#   DEPENDS: video2pptx.application.ports.preview_analyzer, video2pptx.frame_features,
#            video2pptx.roi, video2pptx.slide_detector, video2pptx.video_decode,
#            video2pptx.config
#   LINKS: M-PORT-PREVIEW, M-ADAPTERS
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   LegacyPreviewAnalyzer - adapt legacy preview scoring to PreviewAnalyzerPort
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Complete Phase 16 MCP port adapter integration
# END_CHANGE_SUMMARY

from __future__ import annotations

from video2pptx.application.ports.preview_analyzer import PreviewAnalyzerPort, PreviewOutput
from video2pptx.config import AppConfig
from video2pptx.frame_features import quick_extract, quick_visual_distance
from video2pptx.roi import SlideRegion, parse_ignore_rois, parse_roi
from video2pptx.slide_detector import detect_changes
from video2pptx.video_decode import VideoDecoder


class LegacyPreviewAnalyzer(PreviewAnalyzerPort):
    """Compute score waveform using old quick_extract/quick_visual_distance pipeline.

    No project state or files are modified — pure computation.
    """

    def analyze(
        self,
        video_path: str,
        *,
        sample_fps: float,
        slide_roi: str,
        ignore_rois: list[str],
        threshold: float,
        min_stable_duration: float,
    ) -> PreviewOutput:
        cfg = AppConfig(
            video={"sample_fps": sample_fps, "decoder_backend": "auto"},
            detection={
                "threshold": threshold,
                "min_stable_duration": min_stable_duration,
                "slide_roi": slide_roi,
                "ignore_rois": ignore_rois,
            },
        )

        decoder = VideoDecoder(
            video_path=video_path,
            sample_fps=cfg.video.sample_fps,
            backend=cfg.video.decoder_backend,
        )
        info = decoder.get_info()
        video_duration = info.duration

        ignore_rois_parsed = parse_ignore_rois(cfg.detection.ignore_rois)
        slide_region = SlideRegion(
            roi=parse_roi(cfg.detection.slide_roi).roi,
            ignore_rois=ignore_rois_parsed,
        )

        frames_iter = ((f.timestamp, f.image) for f in decoder.iter_frames())
        _, all_features, all_scores = detect_changes(
            frames=frames_iter,
            slide_region=slide_region,
            threshold=cfg.detection.threshold,
            min_stable_duration=cfg.detection.min_stable_duration,
            sample_fps=cfg.video.sample_fps,
            video_duration=video_duration,
            extract_fn=quick_extract,
            distance_fn=quick_visual_distance,
        )

        return PreviewOutput(
            score_timestamps=[feature.timestamp for feature in all_features[1:]],
            score_values=list(all_scores),
            video_duration=video_duration,
        )
