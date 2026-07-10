# FILE: src/video2pptx/project_manager.py
# VERSION: 0.2.0
# START_MODULE_CONTRACT
#   PURPOSE: Project management — create, open, save project.json with video/subtitle paths, configs, pipeline state
#   SCOPE: Project model (Pydantic), project.json I/O, CLI-friendly helpers, state update
#   DEPENDS: pydantic, pathlib, config, M-ATOMIC-JSON
#   LINKS: M-PROJECT
#   ROLE: DATA_LAYER
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   Project - Pydantic model for project.json schema
#   ProjectState - pipeline progress flags
#   create_project - create project dir + project.json (video optional, auto-name from folder)
#   open_project - load and validate project.json from dir
#   save_project - write Project to project.json
#   import_video_to_project - set video path, auto-detect sibling subtitles
#   import_subtitles_to_project - set subtitle path
#   update_project_state - modify state flags and persist
#   load_slides_into_project - load slides from slides_json into project.slides (force flag added)
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v0.2.0 - Write project.json atomically through shared JSON I/O
#   v0.1.1 - load_slides_into_project: added force parameter to preserve manually-adjusted slides
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from video2pptx.config import DetectionConfig, LlmConfig, VideoConfig
from video2pptx.models import SlideSegment

SUBTITLE_EXTS = {".srt", ".vtt", ".ass", ".ssa", ".sub"}


class ProjectState(BaseModel):
    # START_CONTRACT: ProjectState
    #   PURPOSE: Pipeline progress flags indicating which stages have been completed
    #   INPUTS: { detect_done: bool, notes_done: bool, llm_done: bool,
    #             preview_done: bool, align_done: bool, md_exported: bool,
    #             pptx_exported: bool, auto_done: bool,
    #             stale flags for downstream invalidation }
    #   OUTPUTS: { ProjectState }
    #   SIDE_EFFECTS: none
    #   LINKS: M-PROJECT, M-PIPELINE-STATES
    # END_CONTRACT: ProjectState
    detect_done: bool = Field(default=False, description="Slide detection completed")
    notes_done: bool = Field(default=False, description="Notes processing completed")
    llm_done: bool = Field(default=False, description="LLM enrichment completed")
    preview_done: bool = Field(default=False, description="Quick Preview completed (scores exist)")
    align_done: bool = Field(default=False, description="Auto Align completed (boundaries adjusted)")
    md_exported: bool = Field(default=False, description="Markdown export completed")
    pptx_exported: bool = Field(default=False, description="PPTX export completed")
    auto_done: bool = Field(default=False, description="Full Auto pipeline completed (all stages, validated)")
    detect_stale: bool = Field(default=True, description="Detection results stale (needs re-run)")
    align_stale: bool = Field(default=True, description="Alignment results stale (needs re-run)")
    notes_stale: bool = Field(default=True, description="Notes results stale (needs re-run)")
    md_stale: bool = Field(default=True, description="MD export stale (needs re-export)")
    pptx_stale: bool = Field(default=True, description="PPTX export stale (needs re-export)")

    def mark_stale_downstream(self, stage: str) -> None:
        stage_order = ["detect", "align", "notes", "md", "pptx"]
        try:
            idx = stage_order.index(stage)
        except ValueError:
            return
        for s in stage_order[idx + 1:]:
            setattr(self, f"{s}_stale", True)
        if stage == "detect":
            self.align_done = False
            self.notes_done = False
            self.md_exported = False
            self.pptx_exported = False
            self.auto_done = False
        elif stage == "align":
            self.notes_done = False
            self.md_exported = False
            self.pptx_exported = False
            self.auto_done = False
        elif stage == "notes":
            self.md_exported = False
            self.pptx_exported = False
            self.auto_done = False
        elif stage == "md":
            self.pptx_exported = False
            self.auto_done = False


class Project(BaseModel):
    # START_CONTRACT: Project
    #   PURPOSE: Pydantic model for project.json schema — stores all settings and pipeline state
    #   INPUTS: { version, name, video, subtitles, detection, llm, state, slides_json, output_dir }
    #   OUTPUTS: { Project }
    #   SIDE_EFFECTS: none
    #   LINKS: M-PROJECT
    # END_CONTRACT: Project
    version: str = Field(default="1.0", description="Project schema version")
    name: str = Field(default="Untitled", description="Project name")
    video: str = Field(default="", description="Path to video file")
    subtitles: str | None = Field(default=None, description="Path to SRT/VTT subtitles file")
    video_config: VideoConfig = Field(default_factory=VideoConfig, description="Video source and decoding settings")
    detection: DetectionConfig = Field(default_factory=DetectionConfig, description="Detection settings")
    llm: LlmConfig = Field(default_factory=LlmConfig, description="LLM settings")
    state: ProjectState = Field(default_factory=ProjectState, description="Pipeline progress flags")
    slides_json: str | None = Field(default=None, description="Relative path to slides.json output")
    markers: list[dict[str, str | float]] = Field(default_factory=list, description="User-defined manual markers [{original_ts, snapped_ts, snap_mode}]")
    slides: list[SlideSegment] = Field(default_factory=list, description="Loaded slide segments (populated from slides_json)")
    backend: str = Field(default="auto", description="Preferred decoder backend: auto, opencv, pyav")
    output_dir: str = Field(default=".", description="Output directory (relative to project dir)")
    score_timestamps: list[float] = Field(default_factory=list, description="Score waveform timestamps from slides.json")
    score_values: list[float] = Field(default_factory=list, description="Score waveform values from slides.json")


def create_project(
    project_dir: str | Path,
    video_path: str | Path | None = None,
    subtitles_path: str | Path | None = None,
    name: str | None = None,
) -> Project:
    # START_CONTRACT: create_project
    #   PURPOSE: Create project directory and project.json with given parameters
    #   INPUTS: {
    #       project_dir: str|Path — output project directory,
    #       video_path: str|Path|None — optional path to video file,
    #       subtitles_path: str|Path|None — optional SRT/VTT path,
    #       name: str|None — optional project name
    #   }
    #   OUTPUTS: Project — saved to project.json in project_dir
    #   SIDE_EFFECTS: creates project_dir, writes project.json
    #   LINKS: M-PROJECT
    # END_CONTRACT: create_project

    proj_path = Path(project_dir)
    if proj_path.exists() and any(proj_path.iterdir()):
        raise FileExistsError(f"Project directory not empty: {proj_path}")

    proj_path.mkdir(parents=True, exist_ok=True)

    vid_str = ""
    vid_stem = "Untitled"
    if video_path:
        vid = Path(video_path).resolve()
        if not vid.is_file():
            raise FileNotFoundError(f"Video not found: {vid}")
        vid_str = str(vid)
        vid_stem = vid.stem

    subs = None
    if subtitles_path:
        s = Path(subtitles_path).resolve()
        if s.is_file():
            subs = str(s)

    proj = Project(
        name=name or vid_stem,
        video=vid_str,
        subtitles=subs,
        output_dir=str(proj_path.resolve()),
    )

    save_project(proj, proj_path)
    logger.info(f"[ProjectManager][create_project] Project created | path={proj_path} name={proj.name} video={'yes' if vid_str else 'no'}")

    return proj


def open_project(project_dir: str | Path) -> Project:
    # START_CONTRACT: open_project
    #   PURPOSE: Load project.json from a project directory, validate schema
    #   INPUTS: { project_dir: str|Path }
    #   OUTPUTS: Project
    #   SIDE_EFFECTS: reads project.json
    #   LINKS: M-PROJECT
    # END_CONTRACT: open_project

    proj_path = Path(project_dir).resolve()
    if not proj_path.is_dir():
        raise FileNotFoundError(f"Project directory not found: {proj_path}")

    json_path = proj_path / "project.json"
    if not json_path.is_file():
        raise FileNotFoundError(f"project.json not found in {proj_path}")

    proj = Project.model_validate_json(json_path.read_text(encoding="utf-8"))
    load_slides_into_project(proj)
    logger.info(f"[ProjectManager][open_project] Project loaded | path={json_path} name={proj.name} slides={len(proj.slides)}")

    return proj


def save_project(project: Project, project_dir: str | Path | None = None) -> None:
    # START_CONTRACT: save_project
    #   PURPOSE: Write Project to project.json in the given or configured project directory
    #   INPUTS: { project: Project, project_dir: str|Path|None }
    #   OUTPUTS: None
    #   SIDE_EFFECTS: writes project.json
    #   LINKS: M-PROJECT
    # END_CONTRACT: save_project

    if project_dir is not None:
        json_path = Path(project_dir) / "project.json"
    else:
        json_path = Path(project.output_dir) / "project.json"

    from video2pptx.utils.json_io import write_json_atomic

    write_json_atomic(
        json_path,
        project.model_dump(mode="json", exclude_none=True),
        indent=2,
    )


def import_video_to_project(
    project: Project,
    video_path: str | Path,
) -> Project:
    # START_CONTRACT: import_video_to_project
    #   PURPOSE: Set video path in project, auto-detect sibling subtitle file
    #   INPUTS: { project: Project, video_path: str|Path }
    #   OUTPUTS: Project — updated in-place and saved
    #   SIDE_EFFECTS: copies video to project dir if outside, saves project.json
    #   LINKS: M-PROJECT
    # END_CONTRACT: import_video_to_project

    vid = Path(video_path).resolve()
    if not vid.is_file():
        raise FileNotFoundError(f"Video not found: {vid}")

    project.video = str(vid)

    # Auto-detect sibling subtitle file
    if not project.subtitles:
        guessed = _find_sibling_subtitle(vid)
        if guessed:
            project.subtitles = str(guessed)
            logger.info(f"[ProjectManager][import_video] Auto-detected subtitles | path={guessed}")

    save_project(project)
    logger.info(f"[ProjectManager][import_video] Video set | path={vid}")
    return project


def import_subtitles_to_project(
    project: Project,
    subtitle_path: str | Path,
) -> Project:
    # START_CONTRACT: import_subtitles_to_project
    #   PURPOSE: Set subtitle path in project
    #   INPUTS: { project: Project, subtitle_path: str|Path }
    #   OUTPUTS: Project — updated in-place and saved
    #   SIDE_EFFECTS: saves project.json
    #   LINKS: M-PROJECT
    # END_CONTRACT: import_subtitles_to_project

    sub = Path(subtitle_path).resolve()
    if not sub.is_file():
        raise FileNotFoundError(f"Subtitles not found: {sub}")

    project.subtitles = str(sub)
    save_project(project)
    logger.info(f"[ProjectManager][import_subtitles] Subtitles set | path={sub}")
    return project


def _find_sibling_subtitle(video_path: Path) -> Path | None:
    # START_CONTRACT: _find_sibling_subtitle
    #   PURPOSE: Look for a subtitle file with same stem as video in same directory
    #   INPUTS: { video_path: Path }
    #   OUTPUTS: Path | None
    #   LINKS: M-PROJECT
    # END_CONTRACT: _find_sibling_subtitle

    parent = video_path.parent
    stem = video_path.stem

    for ext in SUBTITLE_EXTS:
        candidate = parent / f"{stem}{ext}"
        if candidate.is_file():
            return candidate

    # Fallback: any subtitle file in the same directory
    for ext in SUBTITLE_EXTS:
        for candidate in parent.glob(f"*{ext}"):
            return candidate

    return None


def update_project_state(project: Project, **state_kwargs: Any) -> Project:
    # START_CONTRACT: update_project_state
    #   PURPOSE: Update one or more state flags on a Project and persist. Supports stale downstream marking.
    #   INPUTS: { project: Project, **state_kwargs: state_flag=bool, slides_json=str|None }
    #   OUTPUTS: Project — updated in-place and saved
    #   SIDE_EFFECTS: writes project.json
    #   LINKS: M-PROJECT, M-PIPELINE-STATES
    # END_CONTRACT: update_project_state

    state_flag_keys = {
        "preview_done", "detect_done", "align_done", "notes_done", "llm_done",
        "md_exported", "pptx_exported", "auto_done",
        "detect_stale", "align_stale", "notes_stale", "md_stale", "pptx_stale",
    }

    for key, value in state_kwargs.items():
        if key in state_flag_keys:
            setattr(project.state, key, value)
        elif key == "slides_json":
            project.slides_json = value

    project.state.mark_stale_downstream(state_kwargs.get("_stage", ""))
    save_project(project)
    logger.info(
        f"[ProjectManager][update_project_state] State updated | "
        f"detect={project.state.detect_done} notes={project.state.notes_done} "
        f"align={project.state.align_done} auto={project.state.auto_done}"
    )
    return project


def load_slides_into_project(project: Project, force: bool = False) -> Project:
    # START_CONTRACT: load_slides_into_project
    #   PURPOSE: Load slides from slides_json into project.slides
    #   INPUTS: { project: Project, force: bool — overwrite existing slides (default False) }
    #   OUTPUTS: Project — updated in-place
    #   SIDE_EFFECTS: reads slides.json if it exists
    #   LINKS: M-PROJECT
    # END_CONTRACT: load_slides_into_project

    if not project.slides_json:
        project.slides = []
        return project

    slides_path = Path(project.output_dir) / project.slides_json
    if not slides_path.is_file():
        logger.warning(f"[ProjectManager][load_slides_into_project] slides.json not found | path={slides_path}")
        project.slides = []
        return project

    import json
    try:
        raw = json.loads(slides_path.read_text(encoding="utf-8"))
        # Preserve manually-adjusted positions on reopen; force overwrite after new detection
        if force or not project.slides:
            project.slides = [SlideSegment(**s) for s in raw.get("slides", [])]
        # Always load score waveform from detection artifact
        project.score_timestamps = raw.get("score_timestamps", [])
        project.score_values = raw.get("score_values", [])
        logger.info(f"[ProjectManager][load_slides_into_project] Loaded | count={len(project.slides)}")
    except Exception as exc:
        logger.error(f"[ProjectManager][load_slides_into_project] Failed | error={exc}")
        project.slides = []

    return project
