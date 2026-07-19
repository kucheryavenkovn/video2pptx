# FILE: src/video2pptx/detect_slides.py
# VERSION: 0.6.0
# START_MODULE_CONTRACT
#   PURPOSE: Standalone slide detection pipeline — video → slides.json + screenshots, no subtitles required
#   SCOPE: Two-pass detection, streaming full-res representatives, stage counts, RSS sampling
#   DEPENDS: models, config, video_decode, roi, frame_features, slide_detector, segmenter, streaming_representatives, detection_metrics
#   LINKS: M-DETECT-SLIDES, M-DETECT-METRICS, Phase-21
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   run_detect_slides - main entry: video_path + config -> slidedoc with screenshots + counts
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v0.6.0 - Phase 21: DetectionCounts + streaming Pass 2 (O(frames+targets), ≤2 live frames)
# END_CHANGE_SUMMARY

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import cv2  # noqa: F401 — kept for tests that monkeypatch detect_slides.cv2
from loguru import logger

from video2pptx.config import AppConfig
from video2pptx.detection_counts import DetectionCounts
from video2pptx.detection_metrics import (
    InstrumentedIterator,
    RssSampler,
    measure,
)
from video2pptx.detection_metrics import (
    collect as _collect_metrics,
)
from video2pptx.models import SlidesDocument, VideoInfo
from video2pptx.roi import SlideRegion, parse_ignore_rois, parse_roi
from video2pptx.segmenter import build_segments
from video2pptx.slide_detector import detect_changes
from video2pptx.streaming_representatives import (
    StreamingPass2Result,
    stream_representatives_and_dedupe,
)
from video2pptx.video_decode import VideoDecoder


def _rss_now_mb() -> float | None:
    try:
        import psutil

        return psutil.Process().memory_info().rss / 1_000_000
    except Exception:
        return None


_LAST_DETECTION_COUNTS: DetectionCounts | None = None


def get_last_detection_counts() -> DetectionCounts | None:
    """Return DetectionCounts from the most recent run_detect_slides call."""
    return _LAST_DETECTION_COUNTS


def run_detect_slides(
    video_path: Path,
    out_dir: Path,
    cfg: AppConfig,
    quick_mode: bool = False,
    progress_callback: Callable[[int, str], None] | None = None,
) -> SlidesDocument:
    global _LAST_DETECTION_COUNTS
    sampler = RssSampler(interval=0.2)
    counts = DetectionCounts()
    _LAST_DETECTION_COUNTS = counts

    with _collect_metrics() as metrics, measure("total"):
        rss_before = _rss_now_mb()
        if rss_before is not None:
            metrics.gauge_rss_before_mb.value = rss_before
        sampler.start()

        try:
            slides_dir = out_dir / "slides"
            slides_dir.mkdir(parents=True, exist_ok=True)

            decoder = VideoDecoder(
                video_path=video_path,
                sample_fps=cfg.video.sample_fps,
                backend=cfg.video.decoder_backend,
            )
            info = decoder.get_info()
            analysis_max_side = cfg.video.analysis_max_side
            logger.info(
                f"[DetectSlides][run_detect_slides] Video opened | "
                f"duration={info.duration:.2f}s {info.width}x{info.height} fps={info.fps:.2f} "
                f"analysis_max_side={analysis_max_side}"
            )

            ignore_rois = parse_ignore_rois(cfg.detection.ignore_rois)
            slide_region = SlideRegion(
                roi=parse_roi(cfg.detection.slide_roi).roi,
                ignore_rois=ignore_rois,
            )

            sample_tolerance = 0.5 / max(cfg.video.sample_fps, 0.1)

            logger.info("[DetectSlides][run_detect_slides] Pass 1/2: detecting changes")
            frames_iter = (
                (f.timestamp, f.image)
                for f in InstrumentedIterator(
                    decoder.iter_frames(),
                    metrics.counter_frames_sampled,
                    timer=metrics.timer_pass1_decode_or_frame_advance,
                )
            )
            if quick_mode:
                from video2pptx.frame_features import quick_extract as _extract
                from video2pptx.frame_features import quick_visual_distance as _dist
            else:
                from video2pptx.frame_features import extract_features as _extract
                from video2pptx.frame_features import visual_distance as _dist

            # detect_changes already applies debounce; recompute candidate count via scores/log
            # by intercepting: run raw then debounce for counts
            changes, all_features, all_scores = detect_changes(
                frames=frames_iter,
                slide_region=slide_region,
                threshold=cfg.detection.threshold,
                min_stable_duration=cfg.detection.min_stable_duration,
                sample_fps=cfg.video.sample_fps,
                video_duration=info.duration,
                progress_callback=progress_callback,
                extract_fn=_extract,
                distance_fn=_dist,
                quick_mode=quick_mode,
                analysis_max_side=analysis_max_side,
            )

            counts.sampled_frames = len(all_features)
            counts.debounced_changes = len(changes)
            counts.candidate_changes = int(
                getattr(detect_changes, "last_candidate_count", len(changes))
            )

            # Raw interval count before min-duration filter
            n_raw_intervals = len(changes) + 1 if info.duration > 0 else 0
            counts.segments_before_min_duration = n_raw_intervals

            segments = build_segments(
                changes=changes,
                video_duration=info.duration,
                min_slide_duration=cfg.detection.min_slide_duration,
            )
            counts.segments_after_min_duration = len(segments)
            counts.segments_before_dedupe = len(segments)

            if progress_callback is not None:
                progress_callback(
                    100,
                    f"Debounce / segment building: {len(segments)} segments after duration filter",
                )

            logger.info(
                "[DetectSlides] Stage counts pre-Pass2 | sampled={} debounced={} "
                "segments_before_dur≈{} segments_after_dur={}",
                counts.sampled_frames,
                counts.debounced_changes,
                counts.segments_before_min_duration,
                counts.segments_after_min_duration,
            )

            # Keep historical log phrases for markers/tests ("saving screenshots")
            if cfg.detection.dedupe_enabled and len(segments) > 1:
                logger.info(
                    "[DetectSlides][run_detect_slides] Pass 2/2: deduplicating segments "
                    "& saving screenshots (streaming)"
                )
            else:
                logger.info(
                    "[DetectSlides][run_detect_slides] Pass 2/2: saving screenshots (streaming)"
                )

            if progress_callback is not None:
                progress_callback(
                    0,
                    f"Pass 2/2: captured 0/{len(segments)} representative frames",
                )

            # Always open second pass (two-pass contract). Empty targets: prime generator only.
            pass2_source = decoder.iter_frames()
            with measure("pass2_stream"):
                if segments:
                    pass2 = stream_representatives_and_dedupe(
                        frames=InstrumentedIterator(
                            pass2_source,
                            metrics.counter_pass2_frames_sampled,
                            timer=metrics.timer_pass2_decode_or_frame_advance,
                        ),
                        segments=segments,
                        slide_region=slide_region,
                        slides_dir=slides_dir,
                        sample_tolerance=sample_tolerance,
                        dedupe_enabled=cfg.detection.dedupe_enabled,
                        progress_callback=progress_callback,
                    )
                else:
                    # Start generator (call-count / two-pass surface) then stop without full re-read
                    try:
                        next(pass2_source)
                    except StopIteration:
                        pass
                    pass2 = StreamingPass2Result(
                        segments=[],
                        decoded_frames=0,
                        target_count=0,
                        captured_count=0,
                        missing_count=0,
                        peak_live_fullres_frames=0,
                        peak_live_frame_bytes=0,
                        wall_seconds=0.0,
                        screenshots_written=0,
                        comparisons=0,
                    )

            segments = pass2.segments
            counts.segments_after_dedupe = len(segments)
            counts.screenshots_written = pass2.screenshots_written
            counts.pass2_decoded_frames = pass2.decoded_frames
            counts.pass2_target_count = pass2.target_count
            counts.pass2_captured_count = pass2.captured_count
            counts.pass2_missing_count = pass2.missing_count
            counts.pass2_peak_live_fullres_frames = pass2.peak_live_fullres_frames
            counts.pass2_peak_live_frame_bytes = pass2.peak_live_frame_bytes
            counts.pass2_wall_seconds = pass2.wall_seconds
            counts.extra["pass2_comparisons"] = pass2.comparisons

            if progress_callback is not None and cfg.detection.dedupe_enabled:
                progress_callback(
                    100,
                    f"Deduplication: {counts.segments_before_dedupe} → "
                    f"{counts.segments_after_dedupe} slides",
                )

            metrics.counter_representative_frames.value = pass2.captured_count
            metrics.counter_screenshots_written.value = pass2.screenshots_written
            metrics.counter_slides_detected.value = len(segments)

            doc = SlidesDocument(
                video=VideoInfo(
                    path=str(video_path.resolve()),
                    duration=info.duration,
                    width=info.width,
                    height=info.height,
                    fps=info.fps,
                ),
                slides=segments,
                score_timestamps=[f.timestamp for f in all_features[1:]],
                score_values=all_scores,
            )
            _LAST_DETECTION_COUNTS = counts

            json_path = out_dir / "slides.json"
            json_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
            logger.info(
                f"[DetectSlides][run_detect_slides] Document saved | "
                f"path={json_path} slides={len(segments)} counts={counts.to_dict()}"
            )

            return doc
        finally:
            sampler.stop()
            rss_after = _rss_now_mb()
            if rss_after is not None:
                metrics.gauge_rss_after_mb.value = rss_after
            peak = max(rss_before or 0, sampler.peak_mb, rss_after or 0)
            if peak > 0:
                metrics.gauge_rss_peak_mb.value = peak
