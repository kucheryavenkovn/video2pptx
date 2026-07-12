# FILE: src/video2pptx/gui/controllers/project_controller.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: QObject-based project lifecycle controller — create, open, save, close projects
#            through ApplicationServices (FileProjectRepository). Bridges canonical domain.Project
#            state to the PySide6 GUI via Qt signals.
#   SCOPE: Create new canonical projects; open existing projects from disk (schema 2.0 with
#          automatic legacy migration); save with revision tracking; close and reset state;
#          expose canonical project via loaded_project property.
#   DEPENDS: PySide6.QtCore, video2pptx.bootstrap.application,
#            video2pptx.domain.project, video2pptx.infrastructure.persistence
#   LINKS: M-GUI-PROJECT-CTRL
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ProjectController - create/open/save/close lifecycle emitting Qt signals
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject, Signal

from video2pptx.application.ports.project_repository import LoadedProject
from video2pptx.bootstrap.application import ApplicationServices
from video2pptx.domain.project import Project
from video2pptx.infrastructure.persistence.errors import (
    ProjectAlreadyExists,
    ProjectNotFound,
    ProjectRevisionConflict,
)


class ProjectController(QObject):
    """Qt-aware lifecycle controller for video2pptx projects.

    Delegates persistence to ApplicationServices.repository and emits
    Qt signals so MainWindow and other widgets can react to state changes.
    """

    # START_BLOCK_SIGNALS
    projectOpened = Signal()
    projectClosed = Signal()
    stateChanged = Signal()
    errorOccurred = Signal(str)
    # END_BLOCK_SIGNALS

    def __init__(
        self,
        services: ApplicationServices | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._services = services or ApplicationServices()
        self._project: Project | None = None
        self._revision: str | None = None
        self._loaded: LoadedProject | None = None

    # -- lifecycle properties -----------------------------------------------

    @property
    def project(self) -> Project | None:
        """The currently open domain Project, or None."""
        return self._project

    @property
    def is_open(self) -> bool:
        return self._project is not None

    @property
    def revision(self) -> str | None:
        return self._revision

    @property
    def project_dir(self) -> str | None:
        return self._loaded.location if (self._loaded and self._loaded.location) else None

    # -- lifecycle operations -----------------------------------------------

    def create(self, parent_dir: str | Path, name: str = "Untitled") -> None:
        """Create a new canonical project under *parent_dir/name*.

        Emits ``projectOpened`` on success or ``errorOccurred`` on failure.
        """
        location = Path(parent_dir) / name
        project = Project(name=name, output_dir=str(location))
        try:
            loaded = self._services.repository.create(location, project)
        except ProjectAlreadyExists as exc:
            logger.error("[ProjectController][create] Already exists | location={}", location)
            self.errorOccurred.emit(str(exc))
            return
        self._set_loaded(loaded)
        logger.info(
            "[ProjectController][create] Created | location={} revision={}",
            location,
            loaded.revision,
        )
        self.projectOpened.emit()

    def open(self, path: str | Path) -> None:
        """Open an existing project from disk.

        Supports automatic legacy (schema 1.0 → 2.0) migration.
        Emits ``projectOpened`` on success or ``errorOccurred`` on failure.
        """
        location = Path(path)
        try:
            loaded = self._services.repository.load(location)
        except ProjectNotFound as exc:
            logger.error("[ProjectController][open] Not found | location={}", location)
            self.errorOccurred.emit(str(exc))
            return
        self._set_loaded(loaded)
        logger.info(
            "[ProjectController][open] Opened | location={} revision={} migrated={}",
            location,
            loaded.revision,
            loaded.migrated,
        )
        self.projectOpened.emit()

    def save(self) -> None:
        """Save the current project with optimistic concurrency (revision check).

        Emits ``stateChanged`` on success or ``errorOccurred`` on failure.
        """
        if self._project is None or self._revision is None:
            logger.warning("[ProjectController][save] No open project to save")
            self.errorOccurred.emit("No open project to save")
            return
        try:
            result = self._services.repository.save(
                self._project,
                Path(self._project.output_dir),
                expected_revision=self._revision,
            )
            self._revision = result.revision
            logger.info(
                "[ProjectController][save] Saved | location={} revision={}",
                self._project.output_dir,
                result.revision,
            )
            self.stateChanged.emit()
        except ProjectRevisionConflict as exc:
            logger.warning("[ProjectController][save] Reloading stale revision | error={}", exc)
            if not self.reload(emit=False):
                self.errorOccurred.emit(str(exc))

    def reload(self, *, emit: bool = True) -> bool:
        """Reload the canonical GUI snapshot and revision from repository storage."""
        if self.project_dir is None:
            return False
        try:
            loaded = self._services.repository.load(Path(self.project_dir))
        except Exception as exc:
            logger.exception("[ProjectController][reload] Reload failed")
            self.errorOccurred.emit(str(exc))
            return False
        self._set_loaded(loaded)
        if emit:
            self.stateChanged.emit()
        return True

    def close(self) -> None:
        """Close the current project and reset internal state.

        Emits ``projectClosed``.
        """
        self._project = None
        self._revision = None
        self._loaded = None
        self.projectClosed.emit()

    # -- internal helpers ---------------------------------------------------

    def _set_loaded(self, loaded) -> None:
        self._loaded = loaded
        self._project = loaded.project
        self._revision = loaded.revision
