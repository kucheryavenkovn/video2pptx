# FILE: src/video2pptx/gui/controllers/timeline_controller.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: QObject-based timeline controller — CRUD slide intervals, representative
#            timestamps, and notes through ApplicationServices with revision-safe persistence.
#   SCOPE: add/delete/move/resize slides; load subtitles; set/clear slide frames;
#          each operation loads → mutates → saves with revision tracking.
#   DEPENDS: PySide6.QtCore, video2pptx.bootstrap.application,
#            video2pptx.domain.project, video2pptx.domain.identifiers,
#            video2pptx.domain.slide, video2pptx.domain.time
#   LINKS: M-GUI-TIMELINE-CTRL
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   TimelineController - slide CRUD with reload-mutate-save cycle and Qt signals
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject, Signal

from video2pptx.bootstrap.application import ApplicationServices
from video2pptx.domain.identifiers import SlideId
from video2pptx.domain.project import Project
from video2pptx.infrastructure.persistence.errors import (
    ProjectRevisionConflict,
)


class TimelineController(QObject):
    """Qt-aware controller for slide CRUD on a project.

    Each mutating operation follows a strict reload → mutate → save cycle,
    ensuring optimistic concurrency (revision check) on every write.
    """

    slidesChanged = Signal()
    errorOccurred = Signal(str)

    def __init__(
        self,
        services: ApplicationServices,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._services = services
        self._revision: str | None = None

    # -- slide CRUD ---------------------------------------------------------

    def add_slide(
        self,
        project_location: str | Path,
        timestamp: float,
    ) -> SlideId | None:
        """Add a manual slide at *timestamp*.

        Returns the new SlideId or None on error.
        """
        loaded = self._reload(project_location)
        if loaded is None:
            return None

        try:
            slide_id = loaded.project.add_slide(timestamp)
        except Exception as exc:
            logger.exception("[TimelineController][add_slide] Domain error")
            self.errorOccurred.emit(str(exc))
            return None

        if not self._resave(loaded.project, loaded.location, loaded.revision):
            return None

        logger.info(
            "[TimelineController][add_slide] Added | slide_id={} timestamp={}",
            slide_id,
            timestamp,
        )
        self.slidesChanged.emit()
        return slide_id

    def delete_slide(
        self,
        project_location: str | Path,
        slide_id: str | SlideId,
    ) -> bool:
        """Delete a slide by its SlideId. Returns True on success."""
        loaded = self._reload(project_location)
        if loaded is None:
            return False

        try:
            loaded.project.remove_slide(slide_id)
        except Exception as exc:
            logger.exception("[TimelineController][delete_slide] Domain error")
            self.errorOccurred.emit(str(exc))
            return False

        if not self._resave(loaded.project, loaded.location, loaded.revision):
            return False

        self.slidesChanged.emit()
        return True

    def move_slide(
        self,
        project_location: str | Path,
        slide_id: str | SlideId,
        start: float,
        end: float,
    ) -> bool:
        """Move a slide to a new [start, end] interval. Returns True on success."""
        loaded = self._reload(project_location)
        if loaded is None:
            return False

        try:
            loaded.project.move_slide(slide_id, start, end)
        except Exception as exc:
            logger.exception("[TimelineController][move_slide] Domain error")
            self.errorOccurred.emit(str(exc))
            return False

        if not self._resave(loaded.project, loaded.location, loaded.revision):
            return False

        self.slidesChanged.emit()
        return True

    def resize_slide(
        self,
        project_location: str | Path,
        slide_id: str | SlideId,
        end: float,
    ) -> bool:
        """Resize a slide's end boundary. Returns True on success."""
        loaded = self._reload(project_location)
        if loaded is None:
            return False

        try:
            loaded.project.resize_slide(slide_id, end)
        except Exception as exc:
            logger.exception("[TimelineController][resize_slide] Domain error")
            self.errorOccurred.emit(str(exc))
            return False

        if not self._resave(loaded.project, loaded.location, loaded.revision):
            return False

        self.slidesChanged.emit()
        return True

    def clear_slide_image(
        self,
        project_location: str | Path,
        slide_id: str | SlideId,
    ) -> bool:
        """Clear a slide's representative image. Returns True on success."""
        loaded = self._reload(project_location)
        if loaded is None:
            return False

        try:
            loaded.project.clear_image(slide_id)
        except Exception as exc:
            logger.exception("[TimelineController][clear_slide_image] Domain error")
            self.errorOccurred.emit(str(exc))
            return False

        if not self._resave(loaded.project, loaded.location, loaded.revision):
            return False

        self.slidesChanged.emit()
        return True

    # -- internal helpers ---------------------------------------------------

    def _reload(self, project_location: str | Path):
        """Load the current project state from disk. Returns LoadedProject or None."""
        location = Path(project_location)
        try:
            return self._services.repository.load(location)
        except Exception as exc:
            logger.exception("[TimelineController] Reload failed | location={}", location)
            self.errorOccurred.emit(str(exc))
            return None

    def _resave(self, project: Project, location: Path, revision: str | None) -> bool:
        """Save with revision check. Updates internal revision cache. Returns True on success."""
        try:
            result = self._services.repository.save(
                project,
                location,
                expected_revision=revision,
            )
            self._revision = result.revision
            return True
        except ProjectRevisionConflict as exc:
            logger.exception("[TimelineController] Revision conflict | location={}", location)
            self.errorOccurred.emit(str(exc))
            return False
        except Exception as exc:
            logger.exception("[TimelineController] Save failed | location={}", location)
            self.errorOccurred.emit(str(exc))
            return False
