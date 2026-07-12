# FILE: src/video2pptx/bootstrap/application.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Neutral composition root providing all wired Application Services
#            for both MCP and CLI transport adapters.
#   SCOPE: ApplicationServices — lazy singleton container for PreviewService,
#          DetectionService, AlignmentService, NotesService, ExportService,
#          ValidationService, AutoService
#   DEPENDS: video2pptx.infrastructure.persistence.file_project_repository,
#            video2pptx.adapters, video2pptx.application.services,
#            video2pptx.application.base
#   LINKS: M-APP-BOOTSTRAP
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ApplicationServices - neutral wired composition of all application services
#   ApplicationServices.scoped - create an operation-scoped composition with a supplied context
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Add operation-scoped composition for GUI progress/cancellation
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


class ApplicationServices:
    """Neutral composition root for all application services.

    Lazily creates each service with shared repository and ServiceContext.
    Single instance is safe to share across transport adapters.
    """

    def __init__(
        self,
        repository: FileProjectRepository | None = None,
        context: ServiceContext | None = None,
    ) -> None:
        self._repository = repository or FileProjectRepository()
        self._context = context or ServiceContext(repository=self._repository)
        self._preview: PreviewService | None = None
        self._detect: DetectionService | None = None
        self._align: AlignmentService | None = None
        self._notes: NotesService | None = None
        self._export: ExportService | None = None
        self._validate: ValidationService | None = None
        self._auto: AutoService | None = None

    @property
    def context(self) -> ServiceContext:
        return self._context

    @property
    def repository(self) -> FileProjectRepository:
        return self._repository

    def scoped(self, context: ServiceContext) -> ApplicationServices:
        """Create a fresh service composition sharing storage but using *context*."""
        if context.repository is not self._repository:
            raise ValueError("Scoped ServiceContext must use the shared repository")
        return type(self)(repository=self._repository, context=context)

    @property
    def preview_service(self) -> PreviewService:
        if self._preview is None:
            self._preview = PreviewService(
                analyzer=LegacyPreviewAnalyzer(),
                context=self._context,
            )
        return self._preview

    @property
    def detection_service(self) -> DetectionService:
        if self._detect is None:
            self._detect = DetectionService(
                detector=LegacySlideDetector(),
                context=self._context,
            )
        return self._detect

    @property
    def alignment_service(self) -> AlignmentService:
        if self._align is None:
            self._align = AlignmentService(
                aligner=LegacyAligner(),
                context=self._context,
            )
        return self._align

    @property
    def notes_service(self) -> NotesService:
        if self._notes is None:
            self._notes = NotesService(
                processor=LegacyNotesProcessor(),
                context=self._context,
            )
        return self._notes

    @property
    def export_service(self) -> ExportService:
        if self._export is None:
            self._export = ExportService(
                exporter=LegacyExporter(),
                context=self._context,
            )
        return self._export

    @property
    def validation_service(self) -> ValidationService:
        if self._validate is None:
            self._validate = ValidationService(
                context=self._context,
            )
        return self._validate

    @property
    def auto_service(self) -> AutoService:
        if self._auto is None:
            self._auto = AutoService(
                context=self._context,
                preview_service=self.preview_service,
                detection_service=self.detection_service,
                alignment_service=self.alignment_service,
                notes_service=self.notes_service,
                export_service=self.export_service,
                validation_service=self.validation_service,
            )
        return self._auto
