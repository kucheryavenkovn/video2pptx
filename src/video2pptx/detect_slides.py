# FILE: src/video2pptx/detect_slides.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Standalone slide detection pipeline — video → slides.json + screenshots, no subtitles required
#   SCOPE: One function: run_detect_slides() that opens video, detects changes, deduplicates, saves screenshots and slides.json
#   DEPENDS: models, config, video_decode, roi, frame_features, slide_detector, segmenter, dedupe
#   LINKS: M-DETECT-SLIDES
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   run_detect_slides - main entry: video_path + config → SlidesDocument with screenshots saved to disk
# END_MODULE_MAP

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import cv2
import numpy as np
from loguru import logger

from video2pptx.config import AppConfig
from video2pptx.dedupe import deduplicate_segments
from video2pptx.models import SlidesDocument, SlideSegment, VideoInfo
from video2pptx.roi import SlideRegion, parse_ignore_rois, parse_roi
from video2pptx.segmenter import build_segments
from video2pptx.slide_detector import detect_changes
from video2pptx.video_decode import VideoDecoder


def run_detect_slides(
    video_path: Path,
    out_dir: Path,
    cfg: AppConfig,
    quick_mode: bool = False,
    progress_callback: Callable[[int, str], None] | None = None,
) -> SlidesDocument:
    # START_CONTRACT: run_detect_slides
    #   PURPOSE: Run standalone slide detection — no subtitles, no export, only slides.json + screenshots
    #   INPUTS: {
    #       video_path: Path — path to video file,
    #       out_dir: Path — output directory (must exist),
    #       cfg: AppConfig — merged config with detection parameters
    #   }
    #   OUTPUTS: SlidesDocument — saved to slides.json in out_dir, screenshots saved to out_dir/slides/
    #   SIDE_EFFECTS: creates slides/*.png, writes slides.json, iterates video 3 times
    #   LINKS: M-DETECT-SLIDES
    # END_CONTRACT: run_detect_slides

    # START_BLOCK_SETUP_DIRS
    slides_dir = out_dir / "slides"
    slides_dir.mkdir(parents=True, exist_ok=True)
    # END_BLOCK_SETUP_DIRS

    # START_BLOCK_OPEN_VIDEO
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
    # END_BLOCK_OPEN_VIDEO

    # START_BLOCK_PARSE_ROI
    ignore_rois = parse_ignore_rois(cfg.detection.ignore_rois)
    slide_region = SlideRegion(
        roi=parse_roi(cfg.detection.slide_roi).roi,
        ignore_rois=ignore_rois,
    )
    # END_BLOCK_PARSE_ROI

    sample_tolerance = 0.5 / max(cfg.video.sample_fps, 0.1)

    # START_BLOCK_DETECT_CHANGES
    logger.info("[DetectSlides][run_detect_slides] Pass 1/3: detecting changes")
    frames_iter = ((f.timestamp, f.image) for f in decoder.iter_frames())
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
    )
    # END_BLOCK_DETECT_CHANGES

    # START_BLOCK_BUILD_SEGMENTS
    segments: list[SlideSegment] = build_segments(
        changes=changes,
        video_duration=info.duration,
        min_slide_duration=cfg.detection.min_slide_duration,
    )
    # END_BLOCK_BUILD_SEGMENTS

    # START_BLOCK_DEDUPE
    if cfg.detection.dedupe_enabled and len(segments) > 1:
        logger.info("[DetectSlides][run_detect_slides] Pass 2/3: deduplicating segments")
        rep_frames: dict[float, np.ndarray] = {}
        for vf in decoder.iter_frames():
            for s in segments:
                ts = s.representative_timestamp
                if ts not in rep_frames and abs(vf.timestamp - ts) < sample_tolerance:
                    rep_frames[ts] = slide_region.process(vf.image)
                    break
        segments = deduplicate_segments(segments, rep_frames)
    # END_BLOCK_DEDUPE

    # START_BLOCK_SAVE_SCREENSHOTS
    logger.info("[DetectSlides][run_detect_slides] Pass 3/3: saving screenshots")
    saved_timestamps: set[float] = set()
    for vf in decoder.iter_frames():
        for seg in segments:
            ts = seg.representative_timestamp
            if ts not in saved_timestamps and abs(vf.timestamp - ts) < sample_tolerance:
                cropped = slide_region.process(vf.image)
                fname = f"slide_{seg.index:03d}.png"
                cv2.imwrite(str(slides_dir / fname), cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR))
                seg.image = f"slides/{fname}"
                saved_timestamps.add(ts)
                break
    # END_BLOCK_SAVE_SCREENSHOTS

    # START_BLOCK_BUILD_DOCUMENT
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
    # END_BLOCK_BUILD_DOCUMENT

    return doc
