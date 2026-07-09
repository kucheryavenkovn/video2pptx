# FILE: src/video_slide_md/gui/marker_manager.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: CRUD for user-defined blue markers on Project. Persisted in project.json. Calls SmartSnap on creation.
#   SCOPE: Add/delete/get/resnap markers. Each marker stores original_ts, snapped_ts, snap_mode.
#   DEPENDS: M-PROJECT, M-GUI-SMART-SNAP
#   LINKS: M-GUI-MARKER-MANAGER
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   MarkerEntry - TypedDict for marker data
#   add_marker - create marker at timestamp, snap it, persist
#   delete_marker - remove marker by timestamp
#   get_markers - return list of markers from project
#   resnap_marker - re-run snap on existing marker
# END_MODULE_MAP

from __future__ import annotations

from typing import TypedDict

from loguru import logger

from video_slide_md.gui.smart_snap import smart_snap
from video_slide_md.project_manager import Project, save_project


class MarkerEntry(TypedDict, total=False):
    # START_CONTRACT: MarkerEntry
    #   PURPOSE: Typed dict for a single user-defined marker
    #   INPUTS: { original_ts: float, snapped_ts: float, snap_mode: str }
    #   OUTPUTS: { MarkerEntry }
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-MARKER-MANAGER
    # END_CONTRACT: MarkerEntry
    original_ts: float
    snapped_ts: float
    snap_mode: str


def add_marker(
    project: Project,
    timestamp: float,
    snap_mode: str = "hybrid",
    snap_flat_threshold: float = 0.05,
) -> MarkerEntry:
    # START_CONTRACT: add_marker
    #   PURPOSE: Add a user-defined marker at timestamp, snap to nearest scene boundary
    #   INPUTS: { project: Project, timestamp: float, snap_mode: str, snap_flat_threshold: float }
    #   OUTPUTS: MarkerEntry — the created marker
    #   SIDE_EFFECTS: updates project.markers, saves project.json
    #   LINKS: M-GUI-MARKER-MANAGER
    # END_CONTRACT: add_marker

    # START_BLOCK_ADD_MARKER
    snapped = smart_snap(timestamp, project, snap_mode, snap_flat_threshold)

    entry: MarkerEntry = {
        "original_ts": timestamp,
        "snapped_ts": snapped,
        "snap_mode": snap_mode,
    }

    project.markers.append(entry)
    save_project(project)

    logger.info(
        f"[GUI-MarkerManager][add_marker] Marker added | "
        f"original={timestamp:.3f} snapped={snapped:.3f} mode={snap_mode}"
    )
    return entry
    # END_BLOCK_ADD_MARKER


def delete_marker(project: Project, timestamp: float) -> bool:
    # START_CONTRACT: delete_marker
    #   PURPOSE: Remove a marker by its original timestamp
    #   INPUTS: { project: Project, timestamp: float }
    #   OUTPUTS: bool — True if removed, False if not found
    #   SIDE_EFFECTS: updates project.markers, saves project.json
    #   LINKS: M-GUI-MARKER-MANAGER
    # END_CONTRACT: delete_marker

    # START_BLOCK_DELETE_MARKER
    before = len(project.markers)
    project.markers = [
        m for m in project.markers
        if not (isinstance(m, dict) and m.get("original_ts") == timestamp)
    ]
    removed = len(project.markers) < before

    if removed:
        save_project(project)
        logger.info(f"[GUI-MarkerManager][delete_marker] Marker deleted | original={timestamp:.3f}")
    else:
        logger.info(f"[GUI-MarkerManager][delete_marker] Marker not found | original={timestamp:.3f}")

    return removed
    # END_BLOCK_DELETE_MARKER


def get_markers(project: Project) -> list[MarkerEntry]:
    # START_CONTRACT: get_markers
    #   PURPOSE: Return list of marker entries from project
    #   INPUTS: { project: Project }
    #   OUTPUTS: list[MarkerEntry]
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-MARKER-MANAGER
    # END_CONTRACT: get_markers

    # START_BLOCK_GET_MARKERS
    result: list[MarkerEntry] = []
    for m in project.markers:
        if isinstance(m, dict):
            result.append({
                "original_ts": float(m.get("original_ts", 0)),
                "snapped_ts": float(m.get("snapped_ts", 0)),
                "snap_mode": str(m.get("snap_mode", "hybrid")),
            })
    return result
    # END_BLOCK_GET_MARKERS


def resnap_marker(
    project: Project,
    timestamp: float,
    snap_mode: str | None = None,
    snap_flat_threshold: float = 0.05,
) -> MarkerEntry | None:
    # START_CONTRACT: resnap_marker
    #   PURPOSE: Re-run snap on an existing marker with (optionally new) settings
    #   INPUTS: { project: Project, timestamp: float, snap_mode: str | None, snap_flat_threshold: float }
    #   OUTPUTS: MarkerEntry | None — updated marker or None if not found
    #   SIDE_EFFECTS: updates marker in project.markers, saves project.json
    #   LINKS: M-GUI-MARKER-MANAGER
    # END_CONTRACT: resnap_marker

    # START_BLOCK_RESNAP_MARKER
    for i, m in enumerate(project.markers):
        if isinstance(m, dict) and m.get("original_ts") == timestamp:
            mode = snap_mode or str(m.get("snap_mode", "hybrid"))
            snapped = smart_snap(timestamp, project, mode, snap_flat_threshold)

            updated: MarkerEntry = {
                "original_ts": timestamp,
                "snapped_ts": snapped,
                "snap_mode": mode,
            }
            project.markers[i] = updated
            save_project(project)

            logger.info(
                f"[GUI-MarkerManager][resnap_marker] Marker re-snapped | "
                f"original={timestamp:.3f} snapped={snapped:.3f} mode={mode}"
            )
            return updated

    logger.info(f"[GUI-MarkerManager][resnap_marker] Marker not found | original={timestamp:.3f}")
    return None
    # END_BLOCK_RESNAP_MARKER
