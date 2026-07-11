# FILE: src/video2pptx/application/ports/project_repository.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Revision-aware protocol for loading and saving Project aggregates.
#   SCOPE: ProjectRepository Protocol — create, load, save, exists, validate_storage
#   DEPENDS: video2pptx.domain (Project only)
#   LINKS: M-PORT-REPO
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ProjectRepository - Protocol defining the persistence boundary for Project aggregates
#   LoadedProject - aggregate, runtime location, canonical revision, warnings, and migration flag
#   SaveResult - dataclass returned by save with revision and warnings
#   StorageValidationResult - dataclass returned by validate_storage
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Return LoadedProject revision unit from create and load
# END_CHANGE_SUMMARY

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from video2pptx.domain.project import Project


@dataclass(frozen=True, slots=True)
class LoadedProject:
    project: Project
    location: Path
    revision: str
    warnings: tuple[str, ...] = ()
    migrated: bool = False


@dataclass
class SaveResult:
    revision: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class StorageValidationResult:
    valid: bool
    recoverable: bool = False
    schema_version: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recovery_actions: list[str] = field(default_factory=list)


class ProjectRepository(Protocol):
    """Protocol defining the persistence boundary for Project aggregates.

    Domain code never imports this protocol. Application services use it
    as a dependency injection point. The concrete implementation
    (FileProjectRepository) lives in infrastructure.
    """

    def create(self, location: Path, project: Project) -> LoadedProject:
        """Create a new project at *location*. Raises if directory is not empty."""
        ...

    def load(self, location: Path) -> LoadedProject:
        """Load a project from *location*. Performs migration and validation."""
        ...

    def save(
        self,
        project: Project,
        location: Path,
        *,
        expected_revision: str | None = None,
    ) -> SaveResult:
        """Save project atomically. Raises on revision conflict or invariant error."""
        ...

    def exists(self, location: Path) -> bool:
        """Check if a valid project exists at *location*."""
        ...

    def validate_storage(self, location: Path) -> StorageValidationResult:
        """Inspect storage without loading. Returns validation result."""
        ...
