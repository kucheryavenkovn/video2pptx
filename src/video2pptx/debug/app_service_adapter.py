# FILE: src/video2pptx/debug/app_service_adapter.py
# VERSION: 1.2.0
# START_MODULE_CONTRACT
#   PURPOSE: Thin transport adapter between MCP tools and Phase 16 Application Services.
#            No old pipeline calls, no business orchestration, no manual persistence.
#   SCOPE: McpServiceAdapter.execute_command — parse input → call service → map ServiceResult to dict
#   DEPENDS: video2pptx.bootstrap
#   LINKS: M-MCP-ADAPTER
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   McpServiceAdapter - parse MCP command → call Phase 16 service → map result
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.2.0 - Accept ApplicationServices in constructor, remove legacy factory imports
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path
from typing import Any

from loguru import logger

from video2pptx.bootstrap import ApplicationServices


class McpServiceAdapter:
    """Thin MCP → Phase 16 Application Services adapter.

    Responsibilities:
    - Parse MCP command and arguments
    - Call the appropriate Phase 16 Application Service
    - Map ServiceResult to the expected MCP dict response
    - Forward exceptions as error dicts

    Does NOT:
    - Call old pipeline (app_service, detect_slides, etc.)
    - Build configs manually
    - Persist state flags
    - Know about tool name remapping
    """

    def __init__(self, services: ApplicationServices | None = None) -> None:
        self._services = services or ApplicationServices()

    # Mapping: MCP tool name → (service property name, method name)
    _SERVICE_MAP: dict[str, tuple[str, str]] = {
        "preview": ("preview_service", "preview"),
        "quick_preview": ("preview_service", "preview"),
        "detect": ("detection_service", "detect"),
        "auto_align": ("alignment_service", "align"),
        "process_notes": ("notes_service", "notes"),
        "export_md": ("export_service", "export"),
        "export_pptx": ("export_service", "export"),
        "auto": ("auto_service", "auto"),
    }

    # Accepted params per command (others are filtered out)
    _PARAMS_MAP: dict[str, set[str]] = {
        "preview": {"video_path", "sample_fps", "slide_roi", "ignore_rois", "threshold", "min_stable_duration"},
        "quick_preview": {"video_path", "sample_fps", "slide_roi", "ignore_rois", "threshold", "min_stable_duration"},
        "detect": {"video_path", "sample_fps", "slide_roi", "ignore_rois", "threshold", "min_stable_duration", "min_slide_duration", "dedupe_enabled"},
        "auto_align": {"subtitles_path", "dry_run", "max_shift_sec", "include_manual"},
        "process_notes": {"subtitles_path", "mode"},
        "export_md": {"output_path", "format", "overwrite", "dry_run"},
        "export_pptx": {"output_path", "format", "overwrite", "dry_run"},
        "auto": {"mode", "video_path", "subtitles_path", "sample_fps", "slide_roi", "ignore_rois", "threshold", "min_stable_duration", "min_slide_duration", "dedupe_enabled", "notes_mode", "export_format", "export_output_path", "dry_run"},
    }

    @staticmethod
    def _resolve_slide_id(project, kwargs: dict) -> str | None:
        uid = kwargs.get("uid")
        if uid:
            return str(uid)
        index = kwargs.get("index")
        if index is not None:
            if isinstance(index, int):
                idx = index - 1 if index >= 1 else index
                if 0 <= idx < len(project.slides):
                    return str(project.slides[idx].slide_id)
        return None

    def _handle_crud(self, command: str, project_location: Path, **kwargs: Any) -> dict[str, Any] | None:
        """Handle project/slide CRUD commands via repository. Returns None if command not recognized."""
        _CRUD_COMMANDS = {"project_save", "video_import", "subtitle_import",
                          "slide_add", "slide_delete", "slide_move", "slide_resize"}
        if command not in _CRUD_COMMANDS:
            return None
        repo = self._services.repository
        loaded = repo.load(project_location)
        proj = loaded.project

        if command == "project_save":
            repo.save(proj, project_location, expected_revision=loaded.revision)
            return {"success": True, "stage": command, "data": {"saved": True}}
        elif command == "video_import":
            path = str(kwargs.get("path", ""))
            proj.video_path = path
            repo.save(proj, project_location, expected_revision=loaded.revision)
            return {"success": True, "stage": command, "data": {"video": path}}
        elif command == "subtitle_import":
            path = str(kwargs.get("path", ""))
            proj.subtitle_path = path
            repo.save(proj, project_location, expected_revision=loaded.revision)
            return {"success": True, "stage": command, "data": {"subtitles": path}}
        elif command == "slide_add":
            ts = kwargs.get("ts", 0.0)
            slide_id = proj.add_slide(ts)
            repo.save(proj, project_location, expected_revision=loaded.revision)
            return {"success": True, "stage": command, "data": {"uid": str(slide_id), "slide_id": str(slide_id)}, "uid": str(slide_id)}
        elif command == "slide_delete":
            uid = self._resolve_slide_id(proj, kwargs)
            if uid is None:
                return {"success": False, "error": "slide not found", "stage": command}
            proj.remove_slide(uid)
            repo.save(proj, project_location, expected_revision=loaded.revision)
            return {"success": True, "stage": command, "data": {"deleted": True}}
        elif command == "slide_move":
            uid = self._resolve_slide_id(proj, kwargs)
            if uid is None:
                return {"success": False, "error": "slide not found", "stage": command}
            proj.move_slide(uid, kwargs.get("start", 0.0), kwargs.get("end", 5.0))
            repo.save(proj, project_location, expected_revision=loaded.revision)
            return {"success": True, "stage": command, "data": {"moved": True}}
        elif command == "slide_resize":
            uid = self._resolve_slide_id(proj, kwargs)
            if uid is None:
                return {"success": False, "error": "slide not found", "stage": command}
            proj.resize_slide(uid, kwargs.get("end", 5.0))
            repo.save(proj, project_location, expected_revision=loaded.revision)
            return {"success": True, "stage": command, "data": {"resized": True}}
        return None

    def execute_command(self, command: str, project_location: Path, **kwargs: Any) -> dict[str, Any]:
        """Execute an MCP command through the appropriate Phase 16 service.

        Args:
            command: MCP tool name (e.g. 'detect', 'preview', 'auto_align')
            project_location: Path to the project directory
            kwargs: Tool-specific arguments forwarded to the service
        Returns:
            dict matching the old contract (success, data fields, error, stage)
        """
        from video2pptx.application.errors import StageFailureError

        crud_result = self._handle_crud(command, project_location, **kwargs)
        if crud_result is not None:
            return crud_result

        entry = self._SERVICE_MAP.get(command)
        if entry is None:
            return {"success": False, "error": f"unknown command: {command}", "stage": command}

        service_attr, _stage_name = entry

        if command in {"export_md", "export_pptx"}:
            suffix = "md" if command == "export_md" else "pptx"
            kwargs.setdefault("format", "markdown" if suffix == "md" else "pptx")
            kwargs.setdefault("output_path", str(project_location / f"deck.{suffix}"))

        allowed = self._PARAMS_MAP.get(command)
        filtered_kwargs = {
            key: value
            for key, value in kwargs.items()
            if allowed is None or key in allowed
        }

        try:
            service = getattr(self._services, service_attr)
            result = service.execute(
                project_location,
                **filtered_kwargs,
            )
            d = result.to_dict()
            d["stage"] = command
            return d

        except StageFailureError as exc:
            logger.error(f"[McpAdapter] Stage failed | command={command} error={exc}")
            return {
                "success": False,
                "error": str(exc),
                "stage": command,
            }
        except Exception as exc:
            logger.error(f"[McpAdapter] Unexpected failure | command={command} error={exc}")
            return {
                "success": False,
                "error": str(exc),
                "stage": command,
            }
