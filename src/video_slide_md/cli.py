# FILE: src/video_slide_md/cli.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Typer CLI entry point for detect, export-md, debug, review commands
#   SCOPE: CLI argument parsing, output directory setup, orchestrating pipeline
#   DEPENDS: typer, rich, config, pathlib
#   LINKS: M-CLI
#   ROLE: ENTRY_POINT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   app - main Typer application
#   run - entry point for console_scripts
#   detect - detect command: video + subtitles → slides.json + images
#   export_md - export-md command: slides.json → deck.md
#   export_pptx - export-pptx command: slides.json → deck.pptx
#   debug_cmd - debug command: slides.json → debug artifacts
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np
import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from video_slide_md.config import load_config, AppConfig
from video_slide_md.dedupe import deduplicate_segments
from video_slide_md.frame_features import extract_features
from video_slide_md.markdown_export import export_to_markdown
from video_slide_md.pptx_export import export_to_pptx
from video_slide_md.models import SlideSegment, SlidesDocument, VideoInfo, SubtitleCue
from video_slide_md.roi import SlideRegion, parse_roi, parse_ignore_rois
from video_slide_md.segmenter import build_segments
from video_slide_md.slide_detector import detect_changes
from video_slide_md.subtitles import align_cues_to_segments, parse_subtitles
from video_slide_md.video_decode import VideoDecoder

app = typer.Typer(name="video-slide-md")
console = Console()


@app.command()
def detect(
    video: str = typer.Argument(..., help="Path to video file"),
    subtitles: Optional[str] = typer.Option(None, "--subtitles", help="Path to SRT/VTT file"),
    out: str = typer.Option("./out", "--out", help="Output directory"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to YAML config file"),
    sample_fps: Optional[float] = typer.Option(None, "--sample-fps", help="Frame sampling rate"),
    decoder_backend: Optional[str] = typer.Option(None, "--decoder-backend", help="Decoder backend"),
    slide_roi: Optional[str] = typer.Option(None, "--slide-roi", help="ROI: auto, full, or x1,y1,x2,y2"),
    ignore_roi: Optional[list[str]] = typer.Option(None, "--ignore-roi", help="Region to ignore"),
    threshold: Optional[str] = typer.Option(None, "--threshold", help="Diff threshold or auto"),
    min_slide_duration: Optional[float] = typer.Option(None, "--min-slide-duration", help="Min slide seconds"),
    min_stable_duration: Optional[float] = typer.Option(None, "--min-stable-duration", help="Min stable seconds"),
    dedupe: bool = typer.Option(True, "--dedupe/--no-dedupe", help="Enable neighbor deduplication"),
    export_md: bool = typer.Option(False, "--export-md", help="Export deck.md after detection"),
    export_pptx: bool = typer.Option(False, "--export-pptx", help="Export .pptx after detection"),
    notes_mode: str = typer.Option("basic", "--notes-mode", help="Notes processing mode: basic or llm"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug artifacts"),
):
    # START_CONTRACT: detect
    #   PURPOSE: Main detect command — video + subtitles → slides.json + images + optional deck.md
    #   INPUTS: video path, subtitles path, output dir, config path, detection parameters
    #   OUTPUTS: directory with slides/, slides.json, optional deck.md, optional debug/
    #   SIDE_EFFECTS: creates output directory, writes files
    #   LINKS: M-CLI
    # END_CONTRACT: detect

    # START_BLOCK_PARSE_CONFIG
    cli_overrides = _build_cli_overrides(
        sample_fps=sample_fps,
        decoder_backend=decoder_backend,
        slide_roi=slide_roi,
        ignore_roi=ignore_roi,
        threshold=threshold,
        min_slide_duration=min_slide_duration,
        min_stable_duration=min_stable_duration,
        dedupe=dedupe,
        debug=debug,
    )
    cfg = load_config(config_path=config, cli_overrides=cli_overrides)
    # END_BLOCK_PARSE_CONFIG

    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)
    slides_dir = out_dir / "slides"
    slides_dir.mkdir(exist_ok=True)

    video_path = Path(video)
    if not video_path.is_file():
        console.print(f"[red]Video file not found: {video}[/red]")
        raise typer.Exit(code=1)

    subs_path = Path(subtitles) if subtitles else None
    if subtitles and subs_path and not subs_path.is_file():
        console.print(f"[red]Subtitles file not found: {subtitles}[/red]")
        raise typer.Exit(code=1)

    logger.info(f"[CLI][detect] Starting detection | video={video} sample_fps={cfg.video.sample_fps}")

    console.print(f"[green]✓[/green] Output: {out_dir.resolve()}")
    console.print(f"[green]✓[/green] Video: {video_path.resolve()}")
    if subs_path:
        console.print(f"[green]✓[/green] Subtitles: {subs_path.resolve()}")

    # START_BLOCK_OPEN_VIDEO
    decoder = VideoDecoder(
        video_path=video_path,
        sample_fps=cfg.video.sample_fps,
        backend=cfg.video.decoder_backend,
    )
    info = decoder.get_info()
    logger.info(f"[CLI][detect] Video info | duration={info.duration:.2f} {info.width}x{info.height} fps={info.fps:.2f}")
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
    frames_iter = ((f.timestamp, f.image) for f in decoder.iter_frames())
    changes, all_features, all_scores = detect_changes(
        frames=frames_iter,
        slide_region=slide_region,
        threshold=cfg.detection.threshold,
        min_stable_duration=cfg.detection.min_stable_duration,
        sample_fps=cfg.video.sample_fps,
        video_duration=info.duration,
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
        # Re-iterate frames to collect representative images keyed by segment ts
        rep_frames: dict[float, np.ndarray] = {}
        for vf in decoder.iter_frames():
            for s in segments:
                ts = s.representative_timestamp
                if ts not in rep_frames and abs(vf.timestamp - ts) < sample_tolerance:
                    rep_frames[ts] = slide_region.process(vf.image)
                    break
        segments = deduplicate_segments(segments, rep_frames)
    # END_BLOCK_DEDUPE

    # START_BLOCK_ALIGN_SUBTITLES
    cues: list[SubtitleCue] = []
    if subs_path:
        content = subs_path.read_text(encoding="utf-8")
        fmt = "vtt" if subs_path.suffix.lower() == ".vtt" else "srt"
        cues = parse_subtitles(content, format=fmt)
        segments = align_cues_to_segments(segments, cues)
    # END_BLOCK_ALIGN_SUBTITLES

    # START_BLOCK_SAVE_SCREENSHOTS
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
    )
    json_path = out_dir / "slides.json"
    json_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    logger.info(f"[CLI][detect] Document saved | path={json_path} slides={len(segments)}")
    # END_BLOCK_BUILD_DOCUMENT

    # START_BLOCK_OPTIONAL_EXPORT
    if export_md:
        md_path = out_dir / "deck.md"
        export_to_markdown(doc, md_path, slides_dir="slides", title=video_path.stem)
        console.print(f"[green]✓[/green] Deck: {md_path.resolve()}")

    if export_pptx:
        pptx_path = out_dir / "deck.pptx"
        export_to_pptx(doc, pptx_path, slides_dir=out_dir, title=video_path.stem, notes_mode=notes_mode)
        console.print(f"[green]✓[/green] PPTX: {pptx_path.resolve()}")

    if debug:
        debug_dir = out_dir / "debug"
        debug_dir.mkdir(exist_ok=True)
        from video_slide_md.debug_export import export_debug_csv, export_debug_report

        if all_scores:
            ts_list = [f.timestamp for f in all_features[1:]]  # scores align with frame 1..N
            export_debug_csv(all_scores, ts_list, debug_dir / "diff_scores.csv")

        export_debug_report(segments, str(video_path), debug_dir / "debug_report.txt")

        # Contact sheet if PIL available
        rep_frames_contact: dict[float, np.ndarray] = {}
        for vf in decoder.iter_frames():
            for seg in segments:
                ts = seg.representative_timestamp
                if ts not in rep_frames_contact and abs(vf.timestamp - ts) < sample_tolerance:
                    rep_frames_contact[ts] = slide_region.process(vf.image)
                    break
        if rep_frames_contact:
            from video_slide_md.debug_export import export_contact_sheet
            export_contact_sheet(segments, rep_frames_contact, debug_dir / "contact_sheet.jpg")
        # END_BLOCK_OPTIONAL_EXPORT

    logger.info(f"[CLI][detect] Detection complete | output={out_dir}")
    console.print(f"[green]Done.[/green]")


@app.command()
def export_md(
    slides_json: str = typer.Argument(..., help="Path to slides.json"),
    out: Optional[str] = typer.Option(None, "--out", "-o", help="Output path (default: next to slides.json)"),
    image_as_background: bool = typer.Option(True, "--image-as-bg/--no-image-bg", help="Image as background"),
    transcript_location: str = typer.Option("body", "--transcript-location", help="Notes/body/comment"),
    include_timecodes: bool = typer.Option(True, "--timecodes/--no-timecodes", help="Include timecodes"),
):
    # START_CONTRACT: export_md
    #   PURPOSE: Export slides.json to Marp-formatted deck.md
    #   INPUTS: slides.json path, output path, formatting options
    #   OUTPUTS: deck.md file
    #   SIDE_EFFECTS: writes deck.md
    #   LINKS: M-CLI
    # END_CONTRACT: export_md

    json_path = Path(slides_json)
    if not json_path.is_file():
        console.print(f"[red]File not found: {slides_json}[/red]")
        raise typer.Exit(code=1)

    logger.info(f"[CLI][export_md] Exporting slides from {slides_json}")

    import json
    from video_slide_md.models import SlidesDocument
    from video_slide_md.markdown_export import export_to_markdown

    doc = SlidesDocument.model_validate_json(json_path.read_text(encoding="utf-8"))
    out_path = Path(out) if out else json_path.parent / "deck.md"
    export_to_markdown(doc, out_path)
    console.print(f"[green]✓[/green] Deck: {out_path.resolve()}")


@app.command()
def export_pptx(
    slides_json: str = typer.Argument(..., help="Path to slides.json"),
    out: Optional[str] = typer.Option(None, "--out", "-o", help="Output path (default: next to slides.json)"),
    notes_mode: str = typer.Option("basic", "--notes-mode", help="Notes processing mode: basic or llm"),
):
    # START_CONTRACT: export_pptx
    #   PURPOSE: Export slides.json to PPTX presentation
    #   INPUTS: slides.json path, output path, notes_mode
    #   OUTPUTS: deck.pptx file
    #   SIDE_EFFECTS: writes .pptx
    #   LINKS: M-CLI
    # END_CONTRACT: export_pptx

    json_path = Path(slides_json)
    if not json_path.is_file():
        console.print(f"[red]File not found: {slides_json}[/red]")
        raise typer.Exit(code=1)

    logger.info(f"[CLI][export_pptx] Exporting slides from {slides_json}")

    import json
    from video_slide_md.models import SlidesDocument
    from video_slide_md.pptx_export import export_to_pptx

    doc = SlidesDocument.model_validate_json(json_path.read_text(encoding="utf-8"))
    out_path = Path(out) if out else json_path.parent / "deck.pptx"
    export_to_pptx(doc, out_path, slides_dir=json_path.parent, notes_mode=notes_mode)
    console.print(f"[green]✓[/green] PPTX: {out_path.resolve()}")


@app.command(name="debug")
def debug_cmd(
    slides_json: str = typer.Argument(..., help="Path to slides.json"),
    out: Optional[str] = typer.Option(None, "--out", "-o", help="Output directory"),
):
    # START_CONTRACT: debug_cmd
    #   PURPOSE: Generate debug artifacts from slides.json
    #   INPUTS: slides.json path
    #   OUTPUTS: debug artifacts (diff_scores.csv, timeline.png, contact_sheet.jpg)
    #   SIDE_EFFECTS: writes files
    #   LINKS: M-CLI
    # END_CONTRACT: debug_cmd

    json_path = Path(slides_json)
    if not json_path.is_file():
        console.print(f"[red]File not found: {slides_json}[/red]")
        raise typer.Exit(code=1)

    logger.info(f"[CLI][debug] Generating debug for {slides_json}")

    import json
    from video_slide_md.models import SlidesDocument
    from video_slide_md.debug_export import export_debug_report

    doc = SlidesDocument.model_validate_json(json_path.read_text(encoding="utf-8"))
    out_dir = Path(out) if out else json_path.parent / "debug"
    out_dir.mkdir(parents=True, exist_ok=True)

    report = export_debug_report(doc.slides, doc.video.path, out_dir / "debug_report.txt")
    console.print(f"[green]✓[/green] Report: {report.resolve()}")


def _build_cli_overrides(**kwargs) -> dict:
    # START_CONTRACT: _build_cli_overrides
    #   PURPOSE: Build nested dict from flat CLI kwargs for merge_config
    #   INPUTS: flat kwargs from CLI options
    #   OUTPUTS: nested dict structured like AppConfig
    #   SIDE_EFFECTS: none
    #   LINKS: M-CLI
    # END_CONTRACT: _build_cli_overrides

    overrides: dict = {}

    fps = kwargs.get("sample_fps")
    if fps is not None:
        overrides.setdefault("video", {})["sample_fps"] = fps

    backend = kwargs.get("decoder_backend")
    if backend is not None:
        overrides.setdefault("video", {})["decoder_backend"] = backend

    roi = kwargs.get("slide_roi")
    if roi is not None:
        overrides.setdefault("detection", {})["slide_roi"] = roi

    ignore_rois = kwargs.get("ignore_roi")
    if ignore_rois:
        parsed = []
        for r in ignore_rois:
            parts = [int(x) for x in r.replace(" ", "").split(",")]
            if len(parts) == 4:
                parsed.append(parts)
            else:
                logger.warning(f"[CLI] Invalid --ignore-roi format: {r}")
        if parsed:
            overrides.setdefault("detection", {})["ignore_rois"] = parsed

    threshold = kwargs.get("threshold")
    if threshold is not None:
        try:
            overrides.setdefault("detection", {})["threshold"] = float(threshold)
        except ValueError:
            overrides.setdefault("detection", {})["threshold"] = threshold

    msd = kwargs.get("min_slide_duration")
    if msd is not None:
        overrides.setdefault("detection", {})["min_slide_duration"] = msd

    mst = kwargs.get("min_stable_duration")
    if mst is not None:
        overrides.setdefault("detection", {})["min_stable_duration"] = mst

    dedupe = kwargs.get("dedupe")
    if dedupe is not None:
        overrides.setdefault("detection", {})["dedupe_enabled"] = dedupe

    debug_flag = kwargs.get("debug")
    if debug_flag is not None:
        overrides.setdefault("debug", {})["save_sampled_frames"] = debug_flag
        overrides.setdefault("debug", {})["save_diff_scores"] = debug_flag
        overrides.setdefault("debug", {})["save_timeline"] = debug_flag
        overrides.setdefault("debug", {})["save_contact_sheet"] = debug_flag

    return overrides


def run():
    # START_CONTRACT: run
    #   PURPOSE: Console_scripts entry point
    #   INPUTS: none (reads sys.argv)
    #   OUTPUTS: int exit code via typer
    #   SIDE_EFFECTS: executes CLI commands
    #   LINKS: M-CLI
    # END_CONTRACT: run
    app()
