# FILE: src/video2pptx/debug/mcp_composition.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Legacy convenience factories that delegate to neutral bootstrap.
#            Kept for backward compat — new code should use ApplicationServices directly.
#   SCOPE: create_preview_service, create_detection_service, create_alignment_service,
#          create_notes_service, create_export_service, create_auto_service
#   DEPENDS: video2pptx.bootstrap
#   LINKS: M-MCP-ADAPTER, M-APP-BOOTSTRAP
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   create_preview_service - wired PreviewService via ApplicationServices
#   create_detection_service - wired DetectionService via ApplicationServices
#   create_alignment_service - wired AlignmentService via ApplicationServices
#   create_notes_service - wired NotesService via ApplicationServices
#   create_export_service - wired ExportService via ApplicationServices
#   create_auto_service - wired AutoService via ApplicationServices
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Delegate to neutral bootstrap/application.py
# END_CHANGE_SUMMARY

from __future__ import annotations

from video2pptx.bootstrap import ApplicationServices

_services: ApplicationServices | None = None


def _shared() -> ApplicationServices:
    global _services
    if _services is None:
        _services = ApplicationServices()
    return _services


def create_preview_service():
    return _shared().preview_service


def create_detection_service():
    return _shared().detection_service


def create_alignment_service():
    return _shared().alignment_service


def create_notes_service():
    return _shared().notes_service


def create_export_service():
    return _shared().export_service


def create_auto_service():
    return _shared().auto_service
