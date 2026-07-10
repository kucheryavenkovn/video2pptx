# FILE: src/video2pptx/app_service.py
# VERSION: 0.3.0
# START_MODULE_CONTRACT
#   PURPOSE: Centralized application service — single entry point for detect, preview, align, notes, export, auto
#   SCOPE: Command handlers that GUI slots, MCP tools, and CLI all delegate to. No Qt, no HTTP.
#   DEPENDS: M-DETECT-SLIDES, M-NOTES, M-MD-EXPORT, M-PPTX-EXPORT, M-AUTO-ALIGN, M-VIDEO-DECODE, M-FRAME-FEATURES
#   LINKS: M-APP-SERVICE
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   CommandResult - typed success/failure result returned by all application commands
#   execute_command - dispatch a named command with kwargs, returns result dict
#   run_detect - canonical slide detection: video → slides.json + screenshots
#   run_preview - quick score computation without creating slides
#   run_auto_align - align visual boundaries to subtitle anchors
#   run_export_md - slides.json → deck.md
#   run_export_pptx - slides.json → deck.pptx
#   run_auto - full pipeline: detect → align → notes → export
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v0.4.0 - Add process_notes command to execute_command dispatcher
#   v0.2.0 - Auto Align apply writes report and slides atomically
# END_CHANGE_SUMMARY

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

from video2pptx.config import AppConfig
from video2pptx.models import SlidesDocument
from video2pptx.video_decode import VideoDecoder


@dataclass
class CommandResult:
    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    stage: str = ""

    def to_dict(self) -> dict:
        d = {"success": self.success, **self.data}
        if self.error:
            d["error"] = self.error
        if self.stage:
            d["stage"] = self.stage
        return d


def run_detect(
    video_path: Path,
    out_dir: Path,
    cfg: AppConfig,
    progress_callback: Callable[[int, str], None] | None = None,
) -> CommandResult:
    # START_CONTRACT: run_detect
    #   PURPOSE: Canonical slide detection — delegates to run_detect_slides, returns structured result
    #   INPUTS: { video_path, out_dir, cfg, progress_callback }
    #   OUTPUTS: CommandResult with slides count, json path, score data
    #   SIDE_EFFECTS: creates slides/, slides.json
    #   LINKS: M-APP-SERVICE
    # END_CONTRACT: run_detect

    from video2pptx.detect_slides import run_detect_slides

    try:
        doc = run_detect_slides(
            video_path=video_path,
            out_dir=out_dir,
            cfg=cfg,
            progress_callback=progress_callback,
        )
        return CommandResult(
            success=True,
            data={
                "slides_count": len(doc.slides),
                "slides_json": str(out_dir / "slides.json"),
                "score_timestamps": doc.score_timestamps,
                "score_values": doc.score_values,
                "video_duration": doc.video.duration,
            },
            stage="detect",
        )
    except Exception as e:
        logger.error(f"[AppService][run_detect] Failed | error={e}")
        return CommandResult(success=False, error=str(e), stage="detect")


def run_preview(
    video_path: Path,
    out_dir: Path,
    cfg: AppConfig,
    progress_callback: Callable[[int, str], None] | None = None,
) -> CommandResult:
    # START_CONTRACT: run_preview
    #   PURPOSE: Quick preview — compute diff scores via keyframes without creating slides
    #   INPUTS: { video_path, out_dir, cfg, progress_callback }
    #   OUTPUTS: CommandResult with score_timestamps, score_values
    #   SIDE_EFFECTS: none (does not create slides.json or modify existing slides)
    #   LINKS: M-APP-SERVICE
    # END_CONTRACT: run_preview

    from video2pptx.frame_features import quick_extract, quick_visual_distance
    from video2pptx.roi import SlideRegion, parse_ignore_rois, parse_roi
    from video2pptx.slide_detector import detect_changes

    try:
        decoder = VideoDecoder(
            video_path=video_path,
            sample_fps=cfg.video.sample_fps,
            backend=cfg.video.decoder_backend,
        )
        info = decoder.get_info()
        logger.info(
            f"[AppService][run_preview] Video opened | "
            f"duration={info.duration:.2f}s {info.width}x{info.height}"
        )

        ignore_rois = parse_ignore_rois(cfg.detection.ignore_rois)
        slide_region = SlideRegion(
            roi=parse_roi(cfg.detection.slide_roi).roi,
            ignore_rois=ignore_rois,
        )

        # Collect all frames first for quick mode (avoids double decode)
        all_frames = list(decoder.iter_frames())
        frames_input = ((f.timestamp, f.image) for f in all_frames)

        _, all_features, all_scores = detect_changes(
            frames=frames_input,
            slide_region=slide_region,
            threshold=cfg.detection.threshold,
            min_stable_duration=cfg.detection.min_stable_duration,
            sample_fps=cfg.video.sample_fps,
            video_duration=info.duration,
            progress_callback=progress_callback,
            extract_fn=quick_extract,
            distance_fn=quick_visual_distance,
        )

        # Timestamps for scores (skip first frame since scores are between frames)
        score_ts = [f.timestamp for f in all_features[1:]]
        return CommandResult(
            success=True,
            data={
                "score_timestamps": score_ts,
                "score_values": all_scores,
                "video_duration": info.duration,
            },
            stage="preview",
        )
    except Exception as e:
        logger.error(f"[AppService][run_preview] Failed | error={e}")
        return CommandResult(success=False, error=str(e), stage="preview")


def run_auto_align(
    slides_json: Path,
    subtitles_path: Path | None,
    max_shift_sec: float = 3.0,
    dry_run: bool = False,
    include_manual: bool = False,
) -> CommandResult:
    # START_CONTRACT: run_auto_align
    #   PURPOSE: Align visual slide boundaries to subtitle anchors
    #   INPUTS: { slides_json, subtitles_path, max_shift_sec, dry_run, include_manual }
    #   OUTPUTS: CommandResult with alignment report, moved count, avg/max shift
    #   SIDE_EFFECTS: writes alignment_report.json, updates slides.json (unless dry_run)
    #   LINKS: M-APP-SERVICE, M-AUTO-ALIGN
    # END_CONTRACT: run_auto_align

    from video2pptx.auto_align import align_slides_to_subtitles

    if not slides_json.is_file():
        return CommandResult(success=False, error=f"slides.json not found: {slides_json}", stage="align")
    if subtitles_path is None or not subtitles_path.is_file():
        return CommandResult(success=False, error="Subtitles required for alignment", stage="align")

    try:
        doc = SlidesDocument.model_validate_json(slides_json.read_text(encoding="utf-8"))
        report = align_slides_to_subtitles(
            slides=doc.slides,
            subtitles_path=subtitles_path,
            max_shift_sec=max_shift_sec,
            dry_run=dry_run,
            include_manual=include_manual,
            video_duration=doc.video.duration,
        )

        if not dry_run:
            report_path = slides_json.parent / "alignment_report.json"
            from video2pptx.utils.json_io import write_json_atomic

            write_json_atomic(report_path, report.to_dict(), indent=2)
            write_json_atomic(slides_json, doc.model_dump(mode="json"), indent=2)

        return CommandResult(
            success=True,
            data={
                "alignment_report": report.to_dict(),
                "boundaries_total": report.boundaries_total,
                "boundaries_moved": report.boundaries_moved,
                "avg_shift": report.avg_shift,
                "max_shift": report.max_shift,
                "dry_run": dry_run,
            },
            stage="align",
        )
    except Exception as e:
        logger.error(f"[AppService][run_auto_align] Failed | error={e}")
        return CommandResult(success=False, error=str(e), stage="align")


def run_export_md(
    slides_json: Path,
    out_path: Path | None = None,
    title: str = "Presentation",
    image_as_background: bool = True,
    transcript_location: str = "body",
    include_timecodes: bool = True,
) -> CommandResult:
    # START_CONTRACT: run_export_md
    #   PURPOSE: Export slides.json to Marp Markdown deck.md
    #   INPUTS: { slides_json, out_path, title, image_as_background, transcript_location, include_timecodes }
    #   OUTPUTS: CommandResult with deck path
    #   SIDE_EFFECTS: writes deck.md
    #   LINKS: M-APP-SERVICE
    # END_CONTRACT: run_export_md

    from video2pptx.markdown_export import export_to_markdown

    if not slides_json.is_file():
        return CommandResult(success=False, error=f"slides.json not found: {slides_json}", stage="export_md")
    try:
        doc = SlidesDocument.model_validate_json(slides_json.read_text(encoding="utf-8"))
        target = out_path or slides_json.parent / "deck.md"
        export_to_markdown(
            doc,
            target,
            slides_dir=str(slides_json.parent),
            title=title,
            image_as_background=image_as_background,
            transcript_location=transcript_location,
            include_timecodes=include_timecodes,
        )
        return CommandResult(success=True, data={"deck_md": str(target)}, stage="export_md")
    except Exception as e:
        logger.error(f"[AppService][run_export_md] Failed | error={e}")
        return CommandResult(success=False, error=str(e), stage="export_md")


def run_export_pptx(
    slides_json: Path,
    out_path: Path | None = None,
    title: str = "Presentation",
    notes_mode: str = "basic",
) -> CommandResult:
    # START_CONTRACT: run_export_pptx
    #   PURPOSE: Export slides.json to PPTX with speaker notes
    #   INPUTS: { slides_json, out_path, title, notes_mode }
    #   OUTPUTS: CommandResult with pptx path
    #   SIDE_EFFECTS: writes deck.pptx
    #   LINKS: M-APP-SERVICE
    # END_CONTRACT: run_export_pptx

    from video2pptx.pptx_export import export_to_pptx

    if not slides_json.is_file():
        return CommandResult(success=False, error=f"slides.json not found: {slides_json}", stage="export_pptx")
    try:
        doc = SlidesDocument.model_validate_json(slides_json.read_text(encoding="utf-8"))
        target = out_path or slides_json.parent / "deck.pptx"
        export_to_pptx(
            doc,
            target,
            slides_dir=slides_json.parent,
            title=title,
            notes_mode=notes_mode,
        )
        return CommandResult(success=True, data={"deck_pptx": str(target)}, stage="export_pptx")
    except Exception as e:
        logger.error(f"[AppService][run_export_pptx] Failed | error={e}")
        return CommandResult(success=False, error=str(e), stage="export_pptx")


def run_auto(
    video_path: Path,
    out_dir: Path,
    subtitles_path: Path | None,
    cfg: AppConfig,
    mode: str = "full",
    progress_callback: Callable[[int, str], None] | None = None,
) -> CommandResult:
    # START_CONTRACT: run_auto
    #   PURPOSE: Full pipeline: detect → align (if subs) → notes → export
    #   INPUTS: { video_path, out_dir, subtitles_path, cfg, mode, progress_callback }
    #   OUTPUTS: CommandResult with all stage results
    #   SIDE_EFFECTS: creates slides.json, deck.md, deck.pptx, alignment_report.json
    #   LINKS: M-APP-SERVICE
    # END_CONTRACT: run_auto

    stages: list[dict] = []

    def _progress(pct: int, msg: str) -> None:
        if progress_callback:
            progress_callback(pct, msg)

    # Stage 1: Detect
    _progress(5, "Detecting slides...")
    det = run_detect(video_path, out_dir, cfg)
    stages.append({"stage": "detect", "success": det.success, "data": det.data})
    if not det.success:
        return CommandResult(
            success=False, error=det.error, stage="detect",
            data={"stages": stages}
        )

    slides_json = out_dir / "slides.json"
    _progress(30, "Detection complete")

    if subtitles_path:
        # Stage 2: Auto Align
        _progress(35, "Aligning boundaries...")
        align = run_auto_align(slides_json, subtitles_path)
        stages.append({"stage": "align", "success": align.success, "data": align.data, "error": align.error})
        if not align.success:
            logger.warning(f"[AppService][run_auto] Align failed (continuing): {align.error}")
        _progress(55, "Alignment complete")

        # Stage 3: Notes
        _progress(60, "Processing notes...")
        from video2pptx.notes_pipeline import run_notes
        try:
            run_notes(
                slides_json=slides_json,
                subtitles_path=subtitles_path,
                slides_dir=out_dir / "slides",
                notes_mode="basic",
            )
            stages.append({"stage": "notes", "success": True})
        except Exception as e:
            stages.append({"stage": "notes", "success": False, "error": str(e)})
        _progress(75, "Notes complete")
    else:
        stages.append({"stage": "align", "success": True, "data": {"skipped": True}})
        stages.append({"stage": "notes", "success": True, "data": {"skipped": True}})

    # Stage 4: Export MD
    _progress(80, "Exporting Markdown...")
    md = run_export_md(slides_json)
    stages.append({"stage": "export_md", "success": md.success, "data": md.data})

    # Stage 5: Export PPTX
    _progress(90, "Exporting PPTX...")
    pptx = run_export_pptx(slides_json, notes_mode="basic")
    stages.append({"stage": "export_pptx", "success": pptx.success, "data": pptx.data})

    _progress(100, "Auto pipeline complete")

    all_ok = all(s.get("success", False) for s in stages if not s.get("data", {}).get("skipped"))
    return CommandResult(
        success=all_ok,
        data={"stages": stages, "slides_json": str(slides_json)},
        stage="auto",
    )


def execute_command(command: str, **kwargs: Any) -> dict[str, Any]:
    # START_CONTRACT: execute_command
    #   PURPOSE: Dispatch a named command with kwargs to the appropriate app_service function. Returns dict.
    #   INPUTS: { command: str, **kwargs }
    #   OUTPUTS: dict with success, data, error, stage
    #   SIDE_EFFECTS: depends on command
    #   LINKS: M-APP-SERVICE
    # END_CONTRACT: execute_command

    logger.info(f"[AppService][execute_command] Dispatching | command={command}")

    if command == "detect":
        result = run_detect(
            video_path=Path(kwargs["video_path"]),
            out_dir=Path(kwargs["out_dir"]),
            cfg=kwargs.get("cfg"),
            progress_callback=kwargs.get("progress_callback"),
        )
    elif command == "preview":
        result = run_preview(
            video_path=Path(kwargs["video_path"]),
            out_dir=Path(kwargs["out_dir"]),
            cfg=kwargs.get("cfg"),
            progress_callback=kwargs.get("progress_callback"),
        )
    elif command == "auto_align":
        result = run_auto_align(
            slides_json=Path(kwargs["slides_json"]),
            subtitles_path=Path(kwargs["subtitles_path"]) if kwargs.get("subtitles_path") else None,
            max_shift_sec=float(kwargs.get("max_shift_sec", 3.0)),
            dry_run=bool(kwargs.get("dry_run", False)),
            include_manual=bool(kwargs.get("include_manual", False)),
        )
    elif command == "export_md":
        result = run_export_md(
            slides_json=Path(kwargs["slides_json"]),
            out_path=Path(kwargs["out_path"]) if kwargs.get("out_path") else None,
            title=str(kwargs.get("title", "Presentation")),
        )
    elif command == "export_pptx":
        result = run_export_pptx(
            slides_json=Path(kwargs["slides_json"]),
            out_path=Path(kwargs["out_path"]) if kwargs.get("out_path") else None,
            title=str(kwargs.get("title", "Presentation")),
            notes_mode=str(kwargs.get("notes_mode", "basic")),
        )
    elif command == "process_notes":
        from video2pptx.notes_pipeline import run_notes as _run_notes

        doc = _run_notes(
            slides_json=Path(kwargs["slides_json"]),
            subtitles_path=Path(kwargs["subtitles_path"]) if kwargs.get("subtitles_path") else None,
            slides_dir=Path(kwargs["out_dir"]) / "slides" if kwargs.get("out_dir") else None,
            notes_mode=str(kwargs.get("mode", "basic")),
        )
        result = CommandResult(
            success=True,
            data={"slides_count": len(doc.slides)},
            stage="notes",
        )
    elif command == "auto":
        result = run_auto(
            video_path=Path(kwargs["video_path"]),
            out_dir=Path(kwargs["out_dir"]),
            subtitles_path=Path(kwargs["subtitles_path"]) if kwargs.get("subtitles_path") else None,
            cfg=kwargs.get("cfg"),
            mode=str(kwargs.get("mode", "full")),
            progress_callback=kwargs.get("progress_callback"),
        )
    else:
        return CommandResult(success=False, error=f"unknown command: {command}").to_dict()

    return result.to_dict()
