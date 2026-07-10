# FILE: src/video2pptx/debug/mcp_write_tools.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Full MCP write tool set — project/video/subtitle/preview/detect/align/notes/llm/export/auto/
#            slide-CRUD/video-transport/settings/app_shutdown. Each delegates to app_service via operation
#            lifecycle; enforces confirm for destructive.
#   SCOPE: Tool dispatch table, schema definitions, tool metadata for MCP tools/list
#   DEPENDS: M-MCP-OPERATIONS, M-APP-SERVICE, M-CANONICAL-COMMANDS, M-CONFIRM-POLICY
#   LINKS: M-MCP-WRITE-TOOLS
#   ROLE: INTEGRATION
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   dispatch_write - submit write tool to operation lifecycle
#   get_write_tool_defs - return canonical write tool metadata for tools/list
#   is_sync_tool - classify tool as synchronous (no op lifecycle)
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Treat Auto Align dry-run as non-destructive
# END_CHANGE_SUMMARY

from __future__ import annotations

from typing import Any

from video2pptx.debug.confirm import require_confirm
from video2pptx.debug.mcp_operations import submit


def _arg(type_: str, description: str, required: bool = False, **extra: Any) -> dict[str, Any]:
    d: dict[str, Any] = {"type": type_, "description": description}
    if extra:
        d.update(extra)
    return d, required


def _build_schema(properties: dict[str, tuple], additional: bool = False) -> dict[str, Any]:
    props = {k: v[0] for k, v in properties.items()}
    required = [k for k, v in properties.items() if v[1]]
    schema: dict[str, Any] = {
        "type": "object",
        "properties": props,
        "additionalProperties": additional,
    }
    if required:
        schema["required"] = required
    return schema


_WRITE_TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "project_create",
        "description": "Create new project at directory path",
        "inputSchema": _build_schema({
            "path": _arg("string", "Project directory path", True),
            "name": _arg("string", "Project name", False),
        }),
    },
    {
        "name": "project_open",
        "description": "Open existing project by directory path",
        "inputSchema": _build_schema({
            "path": _arg("string", "Project directory path", True),
        }),
    },
    {
        "name": "project_close",
        "description": "Close current project (destructive — discards unsaved)",
        "inputSchema": _build_schema({
            "confirm": _arg("boolean", "Must be true to close", False),
        }),
    },
    {
        "name": "project_save",
        "description": "Save current project to disk",
        "inputSchema": _build_schema({}),
    },
    {
        "name": "video_import",
        "description": "Import video file into current project",
        "inputSchema": _build_schema({
            "path": _arg("string", "Full path to video file", True),
        }),
    },
    {
        "name": "subtitle_import",
        "description": "Import subtitle file (SRT/VTT) into current project",
        "inputSchema": _build_schema({
            "path": _arg("string", "Full path to subtitle file", True),
        }),
    },
    {
        "name": "quick_preview",
        "description": "Quick preview: compute diff scores only, no slides created",
        "inputSchema": _build_schema({}),
    },
    {
        "name": "detect",
        "description": "Detect slides via computer vision (CV only, no align/notes/export). Destructive on re-detection.",
        "inputSchema": _build_schema({
            "confirm": _arg("boolean", "Must be true to overwrite existing slides", False),
        }),
    },
    {
        "name": "auto_align",
        "description": "Align visual boundaries to subtitle anchors",
        "inputSchema": _build_schema({
            "max_shift_sec": _arg("number", "Max shift window in seconds", False, default=3.0),
            "dry_run": _arg("boolean", "Return plan without mutating project", False, default=False),
            "include_manual": _arg("boolean", "Allow shifting manual boundaries", False, default=False),
            "confirm": _arg("boolean", "Must be true to apply alignment", False),
        }),
    },
    {
        "name": "process_notes",
        "description": "Process subtitles into cleaned transcript notes",
        "inputSchema": _build_schema({
            "mode": _arg("string", "Notes mode: basic or llm", False, enum=["basic", "llm"]),
            "confirm": _arg("boolean", "Must be true to overwrite existing notes", False),
        }),
    },
    {
        "name": "llm_process",
        "description": "Run LLM vision analysis + transcript correction",
        "inputSchema": _build_schema({
            "confirm": _arg("boolean", "Must be true to run LLM", False),
        }),
    },
    {
        "name": "export_md",
        "description": "Export slides.json to Marp Markdown (deck.md)",
        "inputSchema": _build_schema({
            "overwrite": _arg("boolean", "Overwrite existing deck.md", False, default=True),
            "confirm": _arg("boolean", "Must be true if overwrite=false and file exists", False),
        }),
    },
    {
        "name": "export_pptx",
        "description": "Export slides.json to PPTX (deck.pptx)",
        "inputSchema": _build_schema({
            "overwrite": _arg("boolean", "Overwrite existing deck.pptx", False, default=True),
            "confirm": _arg("boolean", "Must be true if overwrite=false and file exists", False),
        }),
    },
    {
        "name": "auto",
        "description": "Full Auto pipeline: detect → align(if subs) → notes → export_md → export_pptx → save → validate",
        "inputSchema": _build_schema({
            "mode": _arg("string", "Pipeline mode", False, enum=["full", "resume", "force"], default="full"),
            "confirm": _arg("boolean", "Must be true to run auto", False),
        }),
    },
    {
        "name": "slide_add",
        "description": "Add manual slide at timestamp (1-based index returned)",
        "inputSchema": _build_schema({
            "ts": _arg("number", "Timestamp in seconds", True),
        }),
    },
    {
        "name": "slide_delete",
        "description": "Delete slide by UID or 1-based index",
        "inputSchema": _build_schema({
            "uid": _arg("string", "Slide UID (preferred)", False),
            "index": _arg("integer", "1-based slide index", False),
            "confirm": _arg("boolean", "Must be true to delete", False),
        }),
    },
    {
        "name": "slide_move",
        "description": "Move slide to new start/end times",
        "inputSchema": _build_schema({
            "uid": _arg("string", "Slide UID", False),
            "index": _arg("integer", "1-based slide index", False),
            "start": _arg("number", "New start time in seconds", True),
            "end": _arg("number", "New end time in seconds", True),
            "confirm": _arg("boolean", "Must be true to move", False),
        }),
    },
    {
        "name": "slide_resize",
        "description": "Resize slide by moving its end boundary",
        "inputSchema": _build_schema({
            "uid": _arg("string", "Slide UID", False),
            "index": _arg("integer", "1-based slide index", False),
            "end": _arg("number", "New end time in seconds", True),
            "confirm": _arg("boolean", "Must be true to resize", False),
        }),
    },
    {
        "name": "slide_set_frame",
        "description": "Set current video frame as slide representative image",
        "inputSchema": _build_schema({
            "uid": _arg("string", "Slide UID", False),
            "index": _arg("integer", "1-based slide index", False),
        }),
    },
    {
        "name": "slide_clear_image",
        "description": "Clear slide representative image",
        "inputSchema": _build_schema({
            "uid": _arg("string", "Slide UID", False),
            "index": _arg("integer", "1-based slide index", False),
            "confirm": _arg("boolean", "Must be true to clear image", False),
        }),
    },
    {
        "name": "video_seek",
        "description": "Seek video player to position in seconds",
        "inputSchema": _build_schema({
            "position": _arg("number", "Target position in seconds", True, minimum=0),
        }),
    },
    {
        "name": "video_play",
        "description": "Start video playback",
        "inputSchema": _build_schema({}),
    },
    {
        "name": "video_pause",
        "description": "Pause video playback",
        "inputSchema": _build_schema({}),
    },
    {
        "name": "project_settings_get",
        "description": "Get current project settings (ROI, thresholds, etc.)",
        "inputSchema": _build_schema({}),
    },
    {
        "name": "project_settings_update",
        "description": "Update project settings fields",
        "inputSchema": _build_schema({
            "settings": _arg("object", "Key-value pairs of settings to update", True),
            "confirm": _arg("boolean", "Must be true to update", False),
        }),
    },
    {
        "name": "app_settings_get",
        "description": "Get application-wide settings",
        "inputSchema": _build_schema({}),
    },
    {
        "name": "app_settings_update",
        "description": "Update application-wide settings",
        "inputSchema": _build_schema({
            "settings": _arg("object", "Key-value pairs to update", True),
            "confirm": _arg("boolean", "Must be true to update", False),
        }),
    },
    {
        "name": "app_shutdown",
        "description": "Gracefully shutdown application, MCP, and release port",
        "inputSchema": _build_schema({
            "confirm": _arg("boolean", "Must be true to shutdown", False),
        }),
    },
]


def get_write_tool_defs() -> list[dict[str, Any]]:
    return list(_WRITE_TOOL_DEFS)


def dispatch_write(tool: str, args: dict[str, Any] | None = None, trace_id: str = "") -> dict[str, Any]:
    """Submit a write tool to the operation lifecycle.
    Returns {operation_id, tool, status:'queued'} or error dict.
    """
    args = args or {}
    if not (tool == "auto_align" and args.get("dry_run") is True):
        require_confirm(tool, args)
    return submit(tool, args, trace_id=trace_id)


def is_sync_tool(tool: str) -> bool:
    """Returns True for tools that don't need async operation lifecycle."""
    return tool in {
        "get_app_state", "get_ui_state", "get_project",
        "get_timeline", "get_slide", "get_subtitle_clip",
        "list_artifacts", "capture_screenshot",
        "get_operation", "list_operations",
        "project_settings_get", "app_settings_get",
        "health", "get_capabilities",
    }
