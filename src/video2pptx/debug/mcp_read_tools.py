# FILE: src/video2pptx/debug/mcp_read_tools.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Extended MCP read tools — get_app_state, get_ui_state, get_project (extended), get_timeline,
#            get_slide, get_subtitle_clip, list_artifacts, capture_screenshot.
#   SCOPE: Synchronous read functions wrapping ProjectModel, TimelineModel, UiStateReader
#   DEPENDS: M-PROJECT-MODEL, M-TIMELINE-MODEL, M-UI-STATE-READER
#   LINKS: M-MCP-READ-TOOLS
#   ROLE: INTEGRATION
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   get_app_state - backend, version, config summary
#   get_ui_state - window title, status, busy, buttons
#   get_project - video/subtitle/cue count/slide count/pipeline states/artifact paths/stale flags
#   get_timeline - slide/subtitle/score tracks with UID/intervals/manual/image_path
#   get_slide - single slide by uid or index
#   get_subtitle_clip - single subtitle clip by uid or index
#   list_artifacts - enumerate project files with sizes/mtimes
#   capture_screenshot - grab MainWindow pixmap → base64 PNG
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from video2pptx.gui.ui_state import read_ui_state


def get_app_state(project_model=None, timeline=None, version: str = "0.6.0") -> dict[str, Any]:
    state: dict[str, Any] = {
        "version": version,
        "backend": "auto",
        "has_project": False,
        "project_path": None,
    }
    if project_model and project_model.project_path:
        state["has_project"] = True
        state["project_path"] = str(project_model.project_path)
    return state


def get_ui_state(main_window=None) -> dict[str, Any]:
    return read_ui_state(main_window)


def get_project(project_model=None) -> dict[str, Any]:
    if project_model is None or project_model.project_data is None:
        return {"error": "no project"}
    proj = project_model.project_data
    result: dict[str, Any] = {
        "name": proj.name,
        "project_dir": str(project_model.project_path) if project_model.project_path else None,
        "video": str(proj.video) if proj.video else None,
        "subtitle_path": str(proj.subtitles) if proj.subtitles else None,
        "video_duration": proj.video_duration if hasattr(proj, "video_duration") else 0.0,
        "subtitle_cues": len(proj.subtitle_clips) if hasattr(proj, "subtitle_clips") and proj.subtitle_clips else 0,
        "slides_count": len(proj.slides),
        "pipeline_state": {
            "preview_done": bool(getattr(proj.state, "preview_done", False)),
            "detect_done": bool(getattr(proj.state, "detect_done", False)),
            "align_done": bool(getattr(proj.state, "align_done", False)),
            "notes_done": bool(getattr(proj.state, "notes_done", False)),
            "md_exported": bool(getattr(proj.state, "md_exported", False)),
            "pptx_exported": bool(getattr(proj.state, "pptx_exported", False)),
            "auto_done": bool(getattr(proj.state, "auto_done", False)),
        },
        "artifact_paths": _find_artifact_paths(project_model.project_path) if project_model.project_path else {},
    }
    return result


def _find_artifact_paths(project_dir: Path) -> dict[str, str | None]:
    project_dir = Path(project_dir)
    return {
        "project_json": str(project_dir / "project.json") if (project_dir / "project.json").is_file() else None,
        "slides_json": str(project_dir / "slides.json") if (project_dir / "slides.json").is_file() else None,
        "deck_md": str(project_dir / "deck.md") if (project_dir / "deck.md").is_file() else None,
        "deck_pptx": str(project_dir / "deck.pptx") if (project_dir / "deck.pptx").is_file() else None,
        "alignment_report": str(project_dir / "alignment_report.json") if (project_dir / "alignment_report.json").is_file() else None,
        "slides_dir": str(project_dir / "slides") if (project_dir / "slides").is_dir() else None,
    }


def _serialize_timeline(timeline) -> dict[str, Any]:
    if timeline is None:
        return {"duration": 0, "tracks": {}}
    from video2pptx.timeline_model import (
        MarkerClip,
        ScoreClip,
        ScoreTrack,
        SlideClip,
        SubtitleClip,
    )
    tracks: dict[str, Any] = {}
    for name in timeline.track_names():
        track = timeline.track(name)
        if track is None:
            continue
        clips = []
        for clip in track.clips():
            base = {
                "uid": clip.uid,
                "start_sec": clip.start_sec,
                "end_sec": clip.end_sec,
                "duration": clip.duration,
            }
            if isinstance(clip, SlideClip):
                base["type"] = "slide"
                base["index"] = clip.index
                base["image_path"] = clip.image_path
                base["transcript_len"] = len(clip.transcript)
                base["notes_len"] = len(clip.notes)
                base["manual"] = clip.manual
            elif isinstance(clip, SubtitleClip):
                base["type"] = "subtitle"
                base["text"] = clip.plaintext[:80]
            elif isinstance(clip, MarkerClip):
                base["type"] = "marker"
                base["snapped_ts"] = clip.snapped_ts
                base["snap_mode"] = clip.snap_mode
            elif isinstance(clip, ScoreClip):
                base["type"] = "score"
                base["value"] = clip.value
                base["method"] = clip.method
            clips.append(base)
        track_info: dict[str, Any] = {"name": name, "clip_count": len(clips), "clips": clips}
        if isinstance(track, ScoreTrack):
            track_info["min_value"] = track.min_value
            track_info["max_value"] = track.max_value
            track_info["method"] = track.method
        tracks[name] = track_info
    return {"duration": timeline.duration, "px_per_sec": getattr(timeline, "px_per_sec", 0), "tracks": tracks}


def get_timeline(timeline=None) -> dict[str, Any]:
    return _serialize_timeline(timeline)


def get_slide(timeline, uid: str | None = None, index: int | None = None) -> dict[str, Any] | None:
    if timeline is None:
        return None
    track = timeline.track("slides")
    if track is None:
        return None
    from video2pptx.timeline_model import SlideClip
    for clip in track.clips():
        if not isinstance(clip, SlideClip):
            continue
        if uid and clip.uid == uid:
            return {
                "uid": clip.uid,
                "index": clip.index,
                "start_sec": clip.start_sec,
                "end_sec": clip.end_sec,
                "duration": clip.duration,
                "image_path": clip.image_path,
                "manual": clip.manual,
                "transcript": clip.transcript,
                "notes": clip.notes,
                "llm_description": getattr(clip, "llm_description", ""),
            }
        if index is not None and clip.index == index:
            return {
                "uid": clip.uid,
                "index": clip.index,
                "start_sec": clip.start_sec,
                "end_sec": clip.end_sec,
                "duration": clip.duration,
                "image_path": clip.image_path,
                "manual": clip.manual,
                "transcript": clip.transcript,
                "notes": clip.notes,
                "llm_description": getattr(clip, "llm_description", ""),
            }
    return None


def get_subtitle_clip(timeline, uid: str | None = None, index: int | None = None) -> dict[str, Any] | None:
    if timeline is None:
        return None
    from video2pptx.timeline_model import SubtitleClip
    # Try subtitles track first, then subtitle_clips
    track = timeline.track("subtitles") or timeline.track("subtitle_clips")
    if track is None:
        return None
    clips = track.clips()
    target = None
    if uid:
        target = next((c for c in clips if getattr(c, "uid", None) == uid), None)
    elif index is not None and 0 <= index < len(clips):
        target = clips[index]
    if target is None or not isinstance(target, SubtitleClip):
        return None
    return {
        "uid": target.uid,
        "start_sec": target.start_sec,
        "end_sec": target.end_sec,
        "duration": target.duration,
        "text": target.plaintext,
    }


def list_artifacts(project_dir: str | Path | None) -> list[dict[str, Any]]:
    if project_dir is None:
        return []
    base = Path(project_dir)
    if not base.is_dir():
        return []
    artifacts = []
    for f in base.iterdir():
        if f.is_file():
            try:
                st = f.stat()
                artifacts.append({
                    "name": f.name,
                    "path": str(f),
                    "size_bytes": st.st_size,
                    "mtime": st.st_mtime,
                })
            except OSError:
                pass
    return sorted(artifacts, key=lambda x: x["name"])


def capture_screenshot(main_window=None) -> dict[str, Any]:
    if main_window is None:
        return {"error": "no window"}
    try:
        from PySide6.QtCore import QBuffer, QByteArray
        pixmap = main_window.grab()
        ba = QByteArray()
        buf = QBuffer(ba)
        buf.open(QBuffer.OpenModeFlag.WriteOnly)
        pixmap.save(buf, "PNG")
        import base64
        b64 = base64.b64encode(ba.data()).decode("ascii")
        return {"mime": "image/png", "data": b64, "size_bytes": len(ba.data())}
    except Exception as e:
        logger.error(f"[McpRead] Screenshot failed: {e}")
        return {"error": str(e)}
