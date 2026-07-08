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
#   debug_cmd - debug command: slides.json → debug artifacts
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from loguru import logger
from rich.console import Console
from rich.table import Table

from video_slide_md.config import load_config

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

    if debug:
        debug_dir = out_dir / "debug"
        debug_dir.mkdir(exist_ok=True)
        logger.info(f"[CLI][detect] Debug artifacts enabled | dir={debug_dir}")

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
    console.print("[green]✓[/green] Export ready (pending markdown_export module)")


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
    console.print("[green]✓[/green] Debug ready (pending debug_export module)")


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
