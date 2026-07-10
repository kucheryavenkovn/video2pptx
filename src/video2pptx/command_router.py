# FILE: src/video2pptx/command_router.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Unify slide CRUD into one canonical path. Public 1-based slide_index, internal 0-based, uid preferred.
#            GUI/MCP/CLI → router → ProjectModel. Fixes off-by-one.
#   SCOPE: slide_add, slide_delete, slide_move, slide_resize, slide_set_frame, slide_clear_image, slide_show_image
#   DEPENDS: M-PROJECT-MODEL, M-APP-SERVICE
#   LINKS: M-CANONICAL-COMMANDS
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   slide_add - create manual slide at timestamp, return uid + 1-based index
#   slide_delete - remove by uid or 1-based index
#   slide_move - set start/end by uid or index
#   slide_resize - set end boundary by uid or index
#   slide_set_frame - capture current video frame as slide rep image
#   slide_clear_image - remove slide image
#   resolve_uid - helper: uid or index → actual uid
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Route move and resize by stable UID without index conversion
# END_CHANGE_SUMMARY

from __future__ import annotations

from typing import Any


def resolve_uid(slides: list, uid: str | None = None, index: int | None = None) -> str | None:
    """Resolve a slide's UID from either a uid string or a 1-based index.
    Returns None if not found.
    """
    if uid:
        for s in slides:
            if getattr(s, "uid", None) == uid:
                return uid
        return None
    if index is not None:
        idx = index - 1
        if 0 <= idx < len(slides):
            return getattr(slides[idx], "uid", None)
        return None
    return None


def slide_add(project_model, ts: float, **kwargs: Any) -> dict[str, Any]:
    """Add manual slide at timestamp. Returns {uid, index, success, error}."""
    if project_model is None:
        return {"success": False, "error": "no project"}
    try:
        uid = project_model.add_slide(ts)
        slides = project_model.project_data.slides if project_model.project_data else []
        idx = next((i + 1 for i, s in enumerate(slides) if getattr(s, "uid", None) == uid), None)
        return {"success": True, "uid": uid, "index": idx}
    except Exception as e:
        return {"success": False, "error": str(e)}


def slide_delete(project_model, uid: str | None = None, index: int | None = None, **kwargs: Any) -> dict[str, Any]:
    """Delete slide by uid or 1-based index. Returns {success, uid, error}."""
    if project_model is None:
        return {"success": False, "error": "no project"}
    slides = project_model.project_data.slides if project_model.project_data else []
    target_uid = resolve_uid(slides, uid, index)
    if target_uid is None:
        return {"success": False, "error": f"slide not found: uid={uid} index={index}"}
    try:
        project_model.delete_slide_by_uid(target_uid)
        return {"success": True, "uid": target_uid}
    except Exception as e:
        return {"success": False, "error": str(e)}


def slide_move(project_model, start: float, end: float, uid: str | None = None, index: int | None = None, **kwargs: Any) -> dict[str, Any]:
    """Move slide to new start/end times. Returns {success, uid, error}."""
    if project_model is None:
        return {"success": False, "error": "no project"}
    slides = project_model.project_data.slides if project_model.project_data else []
    target_uid = resolve_uid(slides, uid, index)
    if target_uid is None:
        return {"success": False, "error": f"slide not found: uid={uid} index={index}"}
    try:
        project_model.move_slide(target_uid, start, end)
        return {"success": True, "uid": target_uid}
    except Exception as e:
        return {"success": False, "error": str(e)}


def slide_resize(project_model, end: float, uid: str | None = None, index: int | None = None, **kwargs: Any) -> dict[str, Any]:
    """Resize slide end boundary. Equivalent to slide_move with current start."""
    if project_model is None:
        return {"success": False, "error": "no project"}
    slides = project_model.project_data.slides if project_model.project_data else []
    target_uid = resolve_uid(slides, uid, index)
    if target_uid is None:
        return {"success": False, "error": f"slide not found: uid={uid} index={index}"}
    try:
        project_model.resize_slide(target_uid, end)
        return {"success": True, "uid": target_uid}
    except Exception as e:
        return {"success": False, "error": str(e)}


def slide_set_frame(project_model, uid: str | None = None, index: int | None = None, **kwargs: Any) -> dict[str, Any]:
    """Set current video frame as slide image. Implementation depends on video player integration."""
    if project_model is None:
        return {"success": False, "error": "no project"}
    slides = project_model.project_data.slides if project_model.project_data else []
    target_uid = resolve_uid(slides, uid, index)
    if target_uid is None:
        return {"success": False, "error": f"slide not found: uid={uid} index={index}"}
    try:
        project_model.set_slide_frame(target_uid)
        return {"success": True, "uid": target_uid}
    except Exception as e:
        return {"success": False, "error": str(e)}


def slide_clear_image(project_model, uid: str | None = None, index: int | None = None, **kwargs: Any) -> dict[str, Any]:
    """Clear slide representative image."""
    if project_model is None:
        return {"success": False, "error": "no project"}
    slides = project_model.project_data.slides if project_model.project_data else []
    target_uid = resolve_uid(slides, uid, index)
    if target_uid is None:
        return {"success": False, "error": f"slide not found: uid={uid} index={index}"}
    try:
        project_model.clear_slide_image(target_uid)
        return {"success": True, "uid": target_uid}
    except Exception as e:
        return {"success": False, "error": str(e)}
