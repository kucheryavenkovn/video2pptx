# FILE: src/video2pptx/cli.py
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
#   detect - detect command: video + subtitles → slides.json + images (all-in-one)
#   detect_slides - detect-slides command: video → slides.json + screenshots (standalone)
#   notes_cmd - notes command: slides.json + subtitles → enriched notes
#   export_md - export-md command: slides.json → deck.md
#   export_pptx - export-pptx command: slides.json → deck.pptx
#   debug_cmd - debug command: slides.json → debug artifacts
#   llm_process - llm-process command: slides.json → enriched slides.json with LLM vision + transcript correction
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

import numpy as np
import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from video2pptx.config import load_config
from video2pptx.detect_slides import run_detect_slides
from video2pptx.markdown_export import export_to_markdown
from video2pptx.models import SlidesDocument
from video2pptx.notes_pipeline import run_notes
from video2pptx.pptx_export import export_to_pptx
from video2pptx.project_manager import create_project, open_project
from video2pptx.roi import SlideRegion, parse_ignore_rois, parse_roi
from video2pptx.roi_tool import roi_tool_main
from video2pptx.subtitles import align_cues_to_segments, parse_subtitles
from video2pptx.video_decode import VideoDecoder

app = typer.Typer(name="video2pptx")
project_app = typer.Typer(name="project", help="Manage projects - create, open, info")
app.add_typer(project_app, name="project")
console = Console()


@app.command()
def detect(
    video: str = typer.Argument(..., help="Path to video file"),
    subtitles: str | None = typer.Option(None, "--subtitles", help="Path to SRT/VTT file"),
    out: str = typer.Option("./out", "--out", help="Output directory"),
    config: str | None = typer.Option(None, "--config", "-c", help="Path to YAML config file"),
    sample_fps: float | None = typer.Option(None, "--sample-fps", help="Frame sampling rate"),
    decoder_backend: str | None = typer.Option(None, "--decoder-backend", help="Decoder backend"),
    slide_roi: str | None = typer.Option(None, "--slide-roi", help="ROI: auto, full, or x1,y1,x2,y2"),
    ignore_roi: list[str] | None = typer.Option(None, "--ignore-roi", help="Region to ignore"),
    threshold: str | None = typer.Option(None, "--threshold", help="Diff threshold or auto"),
    min_slide_duration: float | None = typer.Option(None, "--min-slide-duration", help="Min slide seconds"),
    min_stable_duration: float | None = typer.Option(None, "--min-stable-duration", help="Min stable seconds"),
    dedupe: bool = typer.Option(True, "--dedupe/--no-dedupe", help="Enable neighbor deduplication"),
    export_md: bool = typer.Option(False, "--export-md", help="Export deck.md after detection"),
    export_pptx: bool = typer.Option(False, "--export-pptx", help="Export .pptx after detection"),
    notes_mode: str = typer.Option("basic", "--notes-mode", help="Notes processing mode: basic or llm"),
    llm: bool = typer.Option(False, "--llm", help="Enable LLM vision analysis + transcript correction via LM Studio"),
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

    # START_BLOCK_RUN_DETECT
    doc = run_detect_slides(
        video_path=video_path,
        out_dir=out_dir,
        cfg=cfg,
    )
    segments = doc.slides
    json_path = out_dir / "slides.json"
    console.print(f"[green]✓[/green] Detected {len(segments)} slides")
    # END_BLOCK_RUN_DETECT

    # START_BLOCK_ALIGN_SUBTITLES
    if subs_path:
        content = subs_path.read_text(encoding="utf-8")
        fmt = "vtt" if subs_path.suffix.lower() == ".vtt" else "srt"
        cues = parse_subtitles(content, format=fmt)
        align_cues_to_segments(segments, cues)
        json_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
        logger.info(f"[CLI][detect] Subtitles aligned | cues={len(cues)}")
    # END_BLOCK_ALIGN_SUBTITLES

    # START_BLOCK_LLM_PROCESSING
    if llm:
        console.print("[blue]i[/blue] Starting LLM vision analysis + transcript correction...")
        from video2pptx.llm_orchestrator import run_llm_pipeline
        run_llm_pipeline(
            slides_path=json_path,
            llm_config=cfg.llm,
            slides_dir=out_dir / "slides",
        )
        doc = SlidesDocument.model_validate_json(json_path.read_text(encoding="utf-8"))
        console.print(f"[green]✓[/green] LLM enriched: {json_path.resolve()}")
    # END_BLOCK_LLM_PROCESSING

    # START_BLOCK_OPTIONAL_EXPORT
    if export_md:
        md_path = out_dir / "deck.md"
        export_to_markdown(
            doc,
            md_path,
            slides_dir=str(out_dir),
            title=video_path.stem,
        )
        console.print(f"[green]✓[/green] Deck: {md_path.resolve()}")

    if export_pptx:
        pptx_path = out_dir / "deck.pptx"
        export_to_pptx(doc, pptx_path, slides_dir=out_dir, title=video_path.stem, notes_mode=notes_mode)
        console.print(f"[green]✓[/green] PPTX: {pptx_path.resolve()}")

    if debug:
        debug_dir = out_dir / "debug"
        debug_dir.mkdir(exist_ok=True)
        from video2pptx.debug_export import export_debug_csv, export_debug_report

        if doc.score_values:
            export_debug_csv(doc.score_values, doc.score_timestamps, debug_dir / "diff_scores.csv")

        export_debug_report(doc.slides, str(video_path), debug_dir / "debug_report.txt")

        # Contact sheet
        decoder = VideoDecoder(
            video_path=video_path,
            sample_fps=cfg.video.sample_fps,
            backend=cfg.video.decoder_backend,
        )
        ignore_rois = parse_ignore_rois(cfg.detection.ignore_rois)
        slide_region = SlideRegion(
            roi=parse_roi(cfg.detection.slide_roi).roi,
            ignore_rois=ignore_rois,
        )
        sample_tolerance = 0.5 / max(cfg.video.sample_fps, 0.1)
        rep_frames_contact: dict[float, np.ndarray] = {}
        for vf in decoder.iter_frames():
            for seg in doc.slides:
                ts = seg.representative_timestamp
                if ts not in rep_frames_contact and abs(vf.timestamp - ts) < sample_tolerance:
                    rep_frames_contact[ts] = slide_region.process(vf.image)
                    break
        if rep_frames_contact:
            from video2pptx.debug_export import export_contact_sheet
            export_contact_sheet(doc.slides, rep_frames_contact, debug_dir / "contact_sheet.jpg")
        # END_BLOCK_OPTIONAL_EXPORT

    logger.info(f"[CLI][detect] Detection complete | output={out_dir}")
    console.print("[green]Done.[/green]")


@app.command(name="detect-slides")
def detect_slides(
    video: str = typer.Argument(..., help="Path to video file"),
    out: str = typer.Option("./out", "--out", help="Output directory"),
    config: str | None = typer.Option(None, "--config", "-c", help="Path to YAML config file"),
    sample_fps: float | None = typer.Option(None, "--sample-fps", help="Frame sampling rate"),
    decoder_backend: str | None = typer.Option(None, "--decoder-backend", help="Decoder backend"),
    slide_roi: str | None = typer.Option(None, "--slide-roi", help="ROI: auto, full, or x1,y1,x2,y2"),
    ignore_roi: list[str] | None = typer.Option(None, "--ignore-roi", help="Region to ignore"),
    threshold: str | None = typer.Option(None, "--threshold", help="Diff threshold or auto"),
    min_slide_duration: float | None = typer.Option(None, "--min-slide-duration", help="Min slide seconds"),
    min_stable_duration: float | None = typer.Option(None, "--min-stable-duration", help="Min stable seconds"),
    dedupe: bool = typer.Option(True, "--dedupe/--no-dedupe", help="Enable neighbor deduplication"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug artifacts"),
):
    # START_CONTRACT: detect_slides
    #   PURPOSE: Standalone slide detection — video → slides.json + screenshots, no subtitles required
    #   INPUTS: video path, output dir, config, detection parameters
    #   OUTPUTS: directory with slides/ and slides.json
    #   SIDE_EFFECTS: creates output directory, writes slides.json and images
    #   LINKS: M-CLI
    # END_CONTRACT: detect_slides

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

    out_dir = Path(out)
    out_dir.mkdir(parents=True, exist_ok=True)

    video_path = Path(video)
    if not video_path.is_file():
        console.print(f"[red]Video file not found: {video}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]✓[/green] Output: {out_dir.resolve()}")
    console.print(f"[green]✓[/green] Video: {video_path.resolve()}")

    doc = run_detect_slides(
        video_path=video_path,
        out_dir=out_dir,
        cfg=cfg,
    )

    console.print(f"[green]✓[/green] Slides: {len(doc.slides)} detected")
    console.print("[green]Done.[/green]")


@app.command(name="notes")
def notes_cmd(
    slides_json: str = typer.Argument(..., help="Path to slides.json from detect-slides"),
    subtitles: str | None = typer.Option(None, "--subtitles", help="Path to SRT/VTT file"),
    slides_dir: str | None = typer.Option(None, "--slides-dir", help="Directory with slide images for vision context"),
    notes_mode: str = typer.Option("basic", "--notes-mode", help="Notes mode: basic or llm"),
):
    # START_CONTRACT: notes_cmd
    #   PURPOSE: Post-process notes — load slides.json, align subtitles, build notes, save enriched document
    #   INPUTS: slides.json path, optional SRT, slides dir, notes mode
    #   OUTPUTS: updated slides.json with cleaned transcript
    #   SIDE_EFFECTS: overwrites slides.json
    #   LINKS: M-CLI
    # END_CONTRACT: notes_cmd

    json_path = Path(slides_json)
    if not json_path.is_file():
        console.print(f"[red]File not found: {slides_json}[/red]")
        raise typer.Exit(code=1)

    subs_path = Path(subtitles) if subtitles else None
    if subtitles and subs_path and not subs_path.is_file():
        console.print(f"[red]Subtitles file not found: {subtitles}[/red]")
        raise typer.Exit(code=1)

    slides_dir_path = Path(slides_dir) if slides_dir else None

    llm_config = None
    if notes_mode == "llm":
        cfg = load_config()
        llm_config = cfg.llm
        if not llm_config.enabled:
            llm_config.enabled = True
        logger.info(f"[CLI][notes] LLM mode | model={llm_config.model} base_url={llm_config.base_url}")

    logger.info(f"[CLI][notes] Starting notes processing | slides={slides_json} mode={notes_mode}")

    run_notes(
        slides_json=json_path,
        subtitles_path=subs_path,
        slides_dir=slides_dir_path,
        notes_mode=notes_mode,
        llm_config=llm_config,
    )

    console.print(f"[green]✓[/green] Notes updated: {json_path.resolve()}")
    console.print("[green]Done.[/green]")


@app.command(name="roi-tool")
def roi_tool_cmd(
    video: str = typer.Argument(..., help="Path to video file"),
    frame_ts: float | None = typer.Option(None, "--frame-ts", help="Frame timestamp to display"),
):
    # START_CONTRACT: roi_tool_cmd
    #   PURPOSE: Open video frame in GUI, user drags rectangle, prints ignore-roi coordinates
    #   INPUTS: video path, optional frame timestamp
    #   OUTPUTS: prints "x1,y1,x2,y2" to stdout
    #   SIDE_EFFECTS: opens OpenCV window, blocks for user input
    #   LINKS: M-CLI
    # END_CONTRACT: roi_tool_cmd

    video_path = Path(video)
    if not video_path.is_file():
        console.print(f"[red]Video file not found: {video}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]✓[/green] Video: {video_path.resolve()}")
    console.print("[blue]i[/blue] Drag rectangle over area to ignore, press Enter to confirm, Esc to cancel")

    roi_tool_main(video_path=video_path, frame_ts=frame_ts)

    console.print("[green]Done.[/green]")


@app.command()
def export_md(
    slides_json: str = typer.Argument(..., help="Path to slides.json"),
    out: str | None = typer.Option(None, "--out", "-o", help="Output path (default: next to slides.json)"),
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

    doc = SlidesDocument.model_validate_json(json_path.read_text(encoding="utf-8"))
    out_path = Path(out) if out else json_path.parent / "deck.md"
    export_to_markdown(
        doc,
        out_path,
        slides_dir=str(json_path.parent),
        image_as_background=image_as_background,
        transcript_location=transcript_location,
        include_timecodes=include_timecodes,
    )
    console.print(f"[green]✓[/green] Deck: {out_path.resolve()}")


@app.command()
def export_pptx(
    slides_json: str = typer.Argument(..., help="Path to slides.json"),
    out: str | None = typer.Option(None, "--out", "-o", help="Output path (default: next to slides.json)"),
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

    from video2pptx.models import SlidesDocument
    from video2pptx.pptx_export import export_to_pptx

    doc = SlidesDocument.model_validate_json(json_path.read_text(encoding="utf-8"))
    out_path = Path(out) if out else json_path.parent / "deck.pptx"
    export_to_pptx(doc, out_path, slides_dir=json_path.parent, notes_mode=notes_mode)
    console.print(f"[green]✓[/green] PPTX: {out_path.resolve()}")


@app.command(name="debug")
def debug_cmd(
    slides_json: str = typer.Argument(..., help="Path to slides.json"),
    out: str | None = typer.Option(None, "--out", "-o", help="Output directory"),
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

    from video2pptx.debug_export import export_debug_report
    from video2pptx.models import SlidesDocument

    doc = SlidesDocument.model_validate_json(json_path.read_text(encoding="utf-8"))
    out_dir = Path(out) if out else json_path.parent / "debug"
    out_dir.mkdir(parents=True, exist_ok=True)

    report = export_debug_report(doc.slides, doc.video.path, out_dir / "debug_report.txt")
    console.print(f"[green]✓[/green] Report: {report.resolve()}")


@app.command(name="llm-process")
def llm_process(
    slides_json: str = typer.Argument(..., help="Path to slides.json from detect"),
    out: str | None = typer.Option(None, "--out", "-o", help="Output path for enriched slides.json"),
    slides_dir: str | None = typer.Option(None, "--slides-dir", help="Directory with slide images"),
    config: str | None = typer.Option(None, "--config", "-c", help="Path to YAML config file"),
    model: str | None = typer.Option(None, "--model", help="LLM model name override"),
    base_url: str | None = typer.Option(None, "--base-url", help="LM Studio API base URL override"),
):
    # START_CONTRACT: llm_process
    #   PURPOSE: LLM process command — enrich slides.json with vision analysis and corrected transcript
    #   INPUTS: slides.json path, output path, slides dir, config, model/base_url overrides
    #   OUTPUTS: enriched slides.json with llm_description, slide_context, corrected transcript
    #   SIDE_EFFECTS: calls LM Studio API, writes enriched slides.json + analysis sidecars
    #   LINKS: M-CLI
    # END_CONTRACT: llm_process

    json_path = Path(slides_json)
    if not json_path.is_file():
        console.print(f"[red]File not found: {slides_json}[/red]")
        raise typer.Exit(code=1)

    logger.info(f"[CLI][llm_process] Starting LLM processing for {slides_json}")

    cfg = load_config(config_path=config)
    llm_cfg = cfg.llm

    # CLI overrides for LLM config
    if model:
        llm_cfg.model = model
    if base_url:
        llm_cfg.base_url = base_url

    if not llm_cfg.enabled:
        llm_cfg.enabled = True

    slides_dir_path = Path(slides_dir) if slides_dir else json_path.parent / "slides"
    out_path = Path(out) if out else json_path

    console.print(f"[green]✓[/green] Model: {llm_cfg.model}")
    console.print(f"[green]✓[/green] Base URL: {llm_cfg.base_url}")
    console.print(f"[green]✓[/green] Slides dir: {slides_dir_path.resolve()}")

    from video2pptx.llm_orchestrator import run_llm_pipeline

    result = run_llm_pipeline(
        slides_path=json_path,
        llm_config=llm_cfg,
        slides_dir=slides_dir_path,
        output_path=out_path,
    )
    console.print(f"[green]✓[/green] Enriched: {result.resolve()}")


@project_app.command(name="create")
def project_create(
    video: str = typer.Argument(..., help="Path to video file"),
    project_dir: str = typer.Argument(..., help="Output project directory"),
    subtitles: str | None = typer.Option(None, "--subtitles", help="Path to SRT/VTT file"),
    name: str | None = typer.Option(None, "--name", "-n", help="Project name"),
):
    # START_CONTRACT: project_create
    #   PURPOSE: Create a new project with video and optional subtitles
    #   INPUTS: video path, project directory, optional subtitles path, optional name
    #   OUTPUTS: project.json created with all settings
    #   SIDE_EFFECTS: creates project directory, writes project.json
    #   LINKS: M-CLI
    # END_CONTRACT: project_create

    video_path = Path(video)
    if not video_path.is_file():
        console.print(f"[red]Video file not found: {video}[/red]")
        raise typer.Exit(code=1)

    subs_path = Path(subtitles) if subtitles else None
    if subtitles and subs_path and not subs_path.is_file():
        console.print(f"[red]Subtitles file not found: {subtitles}[/red]")
        raise typer.Exit(code=1)

    try:
        proj = create_project(
            project_dir=project_dir,
            video_path=video_path,
            subtitles_path=subs_path,
            name=name,
        )
    except (FileNotFoundError, FileExistsError) as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)

    console.print(f"[green]✓[/green] Project created: {Path(project_dir).resolve()}")
    console.print(f"[green]✓[/green] Video: {proj.video}")
    if proj.subtitles:
        console.print(f"[green]✓[/green] Subtitles: {proj.subtitles}")


@project_app.command(name="open")
def project_open_cmd(
    project_dir: str = typer.Argument(..., help="Path to project directory"),
):
    # START_CONTRACT: project_open_cmd
    #   PURPOSE: Open an existing project and display its info
    #   INPUTS: project directory path
    #   OUTPUTS: project info printed to console
    #   SIDE_EFFECTS: none
    #   LINKS: M-CLI
    # END_CONTRACT: project_open_cmd

    try:
        proj = open_project(project_dir)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)

    table = Table(title=f"Project: {proj.name}")
    table.add_column("Key", style="cyan")
    table.add_column("Value")

    table.add_row("Name", proj.name)
    table.add_row("Video", proj.video)
    table.add_row("Subtitles", proj.subtitles or "(none)")
    table.add_row("Detect done", "✓" if proj.state.detect_done else "—")
    table.add_row("Notes done", "✓" if proj.state.notes_done else "—")
    table.add_row("LLM done", "✓" if proj.state.llm_done else "—")
    table.add_row("Slides JSON", proj.slides_json or "(none)")

    console.print(table)


@project_app.command(name="info")
def project_info_cmd(
    project_dir: str = typer.Argument(..., help="Path to project directory"),
):
    # START_CONTRACT: project_info_cmd
    #   PURPOSE: Quick info print for a project (alias for open with less output)
    #   INPUTS: project directory path
    #   OUTPUTS: one-line project status
    #   SIDE_EFFECTS: none
    #   LINKS: M-CLI
    # END_CONTRACT: project_info_cmd

    try:
        proj = open_project(project_dir)
    except FileNotFoundError as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(code=1)

    state_parts = []
    if proj.state.detect_done:
        state_parts.append("detected")
    if proj.state.notes_done:
        state_parts.append("notes")
    if proj.state.llm_done:
        state_parts.append("llm")

    state_str = ", ".join(state_parts) if state_parts else "fresh"
    console.print(f"[green]{proj.name}[/green] — {state_str} — {proj.video}")


@app.command()
def gui() -> None:
    """Launch the desktop GUI application."""
    import sys

    from PySide6.QtWidgets import QApplication

    from video2pptx.gui import MainWindow

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("video2pptx")
    window = MainWindow()
    window.show()
    sys.exit(qt_app.exec())


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
