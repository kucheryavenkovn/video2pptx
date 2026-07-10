# FILE: src/video2pptx/infrastructure/persistence/errors.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Structured persistence error hierarchy for FileProjectRepository.
#   SCOPE: ProjectRepositoryError and subclasses
#   DEPENDS: none
#   LINKS: M-PORT-REPO
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ProjectRepositoryError - base class for all persistence exceptions
#   ProjectNotFound - project directory or project.json missing
#   ProjectAlreadyExists - target directory is not empty
#   ProjectDocumentCorrupted - JSON parse failure or invalid encoding
#   ProjectSchemaUnsupported - unknown schema version
#   ProjectMigrationError - migration step failed
#   ProjectRevisionConflict - optimistic concurrency violation
#   ProjectAtomicWriteError - write/rename failure
# END_MODULE_MAP

from __future__ import annotations


class ProjectRepositoryError(Exception):
    """Base class for all persistence-layer exceptions."""

    def __init__(self, message: str, path: str = "", recoverable: bool = False) -> None:
        super().__init__(message)
        self.path = path
        self.recoverable = recoverable


class ProjectNotFound(ProjectRepositoryError):
    pass


class ProjectAlreadyExists(ProjectRepositoryError):
    pass


class ProjectDocumentCorrupted(ProjectRepositoryError):
    pass


class ProjectSchemaUnsupported(ProjectRepositoryError):
    pass


class ProjectMigrationError(ProjectRepositoryError):
    pass


class ProjectRevisionConflict(ProjectRepositoryError):
    pass


class ProjectAtomicWriteError(ProjectRepositoryError):
    pass
