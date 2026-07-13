# FILE: src/video2pptx/detect_slides.py
# VERSION: 0.4.0
# START_MODULE_CONTRACT
#   PURPOSE: Standalone slide detection pipeline — video → slides.json + screenshots, no subtitles required
#   SCOPE: Two-pass detection, representative screenshots, protected RSS sampling, and slides.json persistence
#   DEPENDS: models, config, video_decode, roi, frame_features, slide_detector, segmenter, dedupe, detection_metrics
#   LINKS: M-DETECT-SLIDES, M-DETECT-METRICS
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   run_detect_slides - main entry: video_path + config -> SlidesDocument with screenshots saved to disk
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v0.4.0 - Restored protected persistence lifecycle and deterministic RSS peak semantics
# END_CHANGE_SUMMARY

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np
from loguru import logger

from video2pptx.config import AppConfig
from video2pptx.dedupe import deduplicate_segments
from video2pptx.detection_metrics import (
    InstrumentedIterator,
    RssSampler,
    measure,
)
from video2pptx.detection_metrics import (
    collect as _collect_metrics,
)
from video2pptx.models import SlidesDocument, SlideSegment, VideoInfo
from video2pptx.roi import SlideRegion, parse_ignore_rois, parse_roi
from video2pptx.segmenter import build_segments
from video2pptx.slide_detector import detect_changes
from video2pptx.video_decode import VideoDecoder


def _rss_now_mb() -> float | None:
    try:
        import psutil
        return psutil.Process().memory_info().rss / 1_000_000
    except Exception:
        return None


def run_detect_slides(
    video_path: Path,
    out_dir: Path,
    cfg: AppConfig,
    quick_mode: bool = False,
    progress_callback: Callable[[int, str], None] | None = None,
) -> SlidesDocument:
    sampler = RssSampler(interval=0.2)

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
            logger.info(
                f"[DetectSlides][run_detect_slides] Video opened | "
                f"duration={info.duration:.2f}s {info.width}x{info.height} fps={info.fps:.2f}"
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
            )

            segments: list[SlideSegment] = build_segments(
                changes=changes,
                video_duration=info.duration,
                min_slide_duration=cfg.detection.min_slide_duration,
            )

            rep_frames: dict[float, np.ndarray] = {}

            if cfg.detection.dedupe_enabled and len(segments) > 1:
                logger.info(
                    "[DetectSlides][run_detect_slides] Pass 2/2: deduplicating segments & saving screenshots"
                )
            else:
                logger.info("[DetectSlides][run_detect_slides] Pass 2/2: saving screenshots")

            pass2_decoder_iter = InstrumentedIterator(
                decoder.iter_frames(),
                metrics.counter_pass2_frames_sampled,
                timer=metrics.timer_pass2_decode_or_frame_advance,
            )
            for vf in pass2_decoder_iter:
                with measure("pass2_match_and_collect"):
                    for s in segments:
                        ts = s.representative_timestamp
                        if ts not in rep_frames and abs(vf.timestamp - ts) < sample_tolerance:
                            cropped = slide_region.process(vf.image)
                            rep_frames[ts] = cropped
                            metrics.counter_representative_frame_bytes.value += cropped.nbytes
                            break

            metrics.counter_representative_frames.value = len(rep_frames)

            with measure("pass2_dedupe"):
                if cfg.detection.dedupe_enabled and len(segments) > 1:
                    segments = deduplicate_segments(segments, rep_frames)

            with measure("pass2_screenshots"):
                for seg in segments:
                    cropped = rep_frames.get(seg.representative_timestamp)
                    if cropped is not None:
                        fname = f"slide_{seg.index:03d}.png"
                        bgr = cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR)
                        ok = cv2.imwrite(str(slides_dir / fname), bgr)
                        if ok:
                            metrics.counter_screenshots_written.increment()
                        seg.image = f"slides/{fname}"

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

            json_path = out_dir / "slides.json"
            json_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
            logger.info(
                f"[DetectSlides][run_detect_slides] Document saved | "
                f"path={json_path} slides={len(segments)}"
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
