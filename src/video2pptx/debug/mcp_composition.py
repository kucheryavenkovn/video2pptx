# FILE: src/video2pptx/debug/mcp_composition.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Composition root for Phase 16 Application Services used by MCP adapter.
#            Wires port adapters, repository, and ServiceContext into ready-to-use services.
#   SCOPE: create_preview_service, create_detection_service, create_alignment_service,
#          create_notes_service, create_export_service, create_auto_service
#   DEPENDS: video2pptx.infrastructure.persistence.file_project_repository,
#            video2pptx.adapters, video2pptx.application.services
#   LINKS: M-MCP-ADAPTER
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   create_preview_service - wired PreviewService
#   create_detection_service - wired DetectionService
#   create_alignment_service - wired AlignmentService
#   create_notes_service - wired NotesService
#   create_export_service - wired ExportService
#   create_auto_service - wired AutoService
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Wire MCP application services to repository and port adapters
# END_CHANGE_SUMMARY

from __future__ import annotations

from video2pptx.adapters import (
    LegacyAligner,
    LegacyExporter,
    LegacyNotesProcessor,
    LegacyPreviewAnalyzer,
    LegacySlideDetector,
)
from video2pptx.application.base import ServiceContext
from video2pptx.application.services.alignment_service import AlignmentService
from video2pptx.application.services.auto_service import AutoService
from video2pptx.application.services.detection_service import DetectionService
from video2pptx.application.services.export_service import ExportService
from video2pptx.application.services.notes_service import NotesService
from video2pptx.application.services.preview_service import PreviewService
from video2pptx.application.services.validation_service import ValidationService
from video2pptx.infrastructure.persistence.file_project_repository import FileProjectRepository

_repo: FileProjectRepository | None = None
_ctx: ServiceContext | None = None


def _shared_repo() -> FileProjectRepository:
    global _repo
    if _repo is None:
        _repo = FileProjectRepository()
    return _repo


def _shared_context() -> ServiceContext:
    global _ctx
    if _ctx is None:
        _ctx = ServiceContext(repository=_shared_repo())
    return _ctx


def create_preview_service() -> PreviewService:
    return PreviewService(
        analyzer=LegacyPreviewAnalyzer(),
        context=_shared_context(),
    )


def create_detection_service() -> DetectionService:
    return DetectionService(
        detector=LegacySlideDetector(),
        context=_shared_context(),
    )


def create_alignment_service() -> AlignmentService:
    return AlignmentService(
        aligner=LegacyAligner(),
        context=_shared_context(),
    )


def create_notes_service() -> NotesService:
    return NotesService(
        processor=LegacyNotesProcessor(),
        context=_shared_context(),
    )


def create_export_service() -> ExportService:
    return ExportService(
        exporter=LegacyExporter(),
        context=_shared_context(),
    )


def create_auto_service() -> AutoService:
    return AutoService(
        context=_shared_context(),
        preview_service=create_preview_service(),
        detection_service=create_detection_service(),
        alignment_service=create_alignment_service(),
        notes_service=create_notes_service(),
        export_service=create_export_service(),
        validation_service=ValidationService(context=_shared_context()),
    )
