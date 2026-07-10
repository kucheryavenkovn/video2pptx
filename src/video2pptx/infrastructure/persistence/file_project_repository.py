# FILE: src/video2pptx/infrastructure/persistence/file_project_repository.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: File-based ProjectRepository implementation with atomic writes, migration, and revision tracking.
#   SCOPE: create, load, save, exists, validate_storage
#   DEPENDS: video2pptx.domain, video2pptx.infrastructure.persistence.errors, mapper, json_io
#   LINKS: M-PORT-REPO
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   FileProjectRepository - concrete repository implementing ProjectRepository protocol
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Initial implementation with atomic writes, legacy migration, UID persistence
# END_CHANGE_SUMMARY

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from loguru import logger

from video2pptx.application.ports.project_repository import (
    SaveResult,
    StorageValidationResult,
)
from video2pptx.domain.project import Project
from video2pptx.infrastructure.persistence.errors import (
    ProjectAlreadyExists,
    ProjectAtomicWriteError,
    ProjectDocumentCorrupted,
    ProjectNotFound,
    ProjectRevisionConflict,
)
from video2pptx.infrastructure.persistence.mapper import ProjectMapper
from video2pptx.utils.json_io import write_json_atomic


class FileProjectRepository:
    """File-based repository implementing the ProjectRepository protocol.

    project.json is the canonical source of truth.
    slides.json is a derived compatibility artifact regenerated on save.
    All writes are atomic (temp + rename).
    Revision tracking uses a UUID per committed save.
    """

    SCHEMA_VERSION = "2.0"

    def create(self, location: Path, project: Project) -> Project:
        """Create a new project at *location*. Directory must be empty or not exist."""
        location = Path(location)
        if location.exists() and any(location.iterdir()):
            raise ProjectAlreadyExists(
                f"Project directory not empty: {location}",
                path=str(location),
            )
        location.mkdir(parents=True, exist_ok=True)
        project.output_dir = str(location)
        self.save(project, location, expected_revision=None)
        logger.info(f"[FileProjectRepository] Created | location={location}")
        return project

    def load(self, location: Path) -> Project:
        """Load a project from *location* with migration and validation."""
        location = Path(location)
        project_json = location / "project.json"
        if not project_json.is_file():
            raise ProjectNotFound(
                f"project.json not found in {location}",
                path=str(location),
            )

        try:
            raw = project_json.read_text(encoding="utf-8")
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ProjectDocumentCorrupted(
                f"Cannot parse project.json: {exc}",
                path=str(project_json),
                recoverable=False,
            ) from exc

        schema_version = data.get("schema_version", "1.0")
        if schema_version not in ("1.0", "2.0"):
            raise ProjectDocumentCorrupted(
                f"Unsupported schema_version: {schema_version}",
                path=str(project_json),
            )

        from video2pptx.project_manager import Project as LegacyProject

        try:
            legacy_project = LegacyProject.model_validate_json(raw)
        except Exception as exc:
            raise ProjectDocumentCorrupted(
                f"Invalid project data: {exc}",
                path=str(project_json),
            ) from exc

        project = ProjectMapper.to_domain(legacy_project, location)

        if schema_version == "1.0":
            logger.info(
                f"[FileProjectRepository] Legacy migration | location={location}"
            )

        logger.info(
            f"[FileProjectRepository] Loaded | location={location} slides={project.slide_count}"
        )
        return project

    def save(
        self,
        project: Project,
        location: Path,
        *,
        expected_revision: str | None = None,
    ) -> SaveResult:
        """Save project atomically with revision tracking."""
        location = Path(location)
        project_json = location / "project.json"
        warnings: list[str] = []

        if expected_revision is not None and project_json.is_file():
            try:
                existing = json.loads(project_json.read_text(encoding="utf-8"))
                current_rev = existing.get("revision", "")
                if current_rev != expected_revision:
                    raise ProjectRevisionConflict(
                        f"Revision mismatch: expected={expected_revision} "
                        f"current={current_rev}",
                        path=str(project_json),
                        recoverable=True,
                    )
            except json.JSONDecodeError:
                warnings.append("Existing project.json is corrupt; overwriting")

        legacy_project = ProjectMapper.to_legacy_project(project)

        document: dict[str, Any] = json.loads(
            legacy_project.model_dump_json(indent=2, exclude_none=True)
        )
        document["schema_version"] = self.SCHEMA_VERSION
        new_revision = uuid.uuid4().hex
        document["revision"] = new_revision

        try:
            write_json_atomic(project_json, document, indent=2)
        except Exception as exc:
            raise ProjectAtomicWriteError(
                f"Failed to write project.json: {exc}",
                path=str(project_json),
            ) from exc

        slides_doc = ProjectMapper.to_slides_document(project)
        slides_json = location / "slides.json"
        try:
            write_json_atomic(slides_json, slides_doc, indent=2)
        except Exception as exc:
            raise ProjectAtomicWriteError(
                f"Failed to write slides.json: {exc}",
                path=str(slides_json),
            ) from exc

        logger.info(
            f"[FileProjectRepository] Saved | location={location} "
            f"revision={new_revision} slides={project.slide_count}"
        )
        return SaveResult(revision=new_revision, warnings=warnings)

    def exists(self, location: Path) -> bool:
        """Check if a valid project.json exists at *location*."""
        return (Path(location) / "project.json").is_file()

    def validate_storage(self, location: Path) -> StorageValidationResult:
        """Inspect storage without fully loading."""
        location = Path(location)
        project_json = location / "project.json"
        if not project_json.is_file():
            return StorageValidationResult(
                valid=False,
                recoverable=False,
                errors=["project.json not found"],
            )
        try:
            raw = project_json.read_text(encoding="utf-8")
            data = json.loads(raw)
            schema_version = data.get("schema_version", "1.0")
            errors: list[str] = []
            warnings: list[str] = []
            if schema_version == "1.0":
                warnings.append("Legacy schema; will be migrated on load")
            return StorageValidationResult(
                valid=True,
                recoverable=True,
                schema_version=schema_version,
                errors=errors,
                warnings=warnings,
            )
        except Exception as exc:
            return StorageValidationResult(
                valid=False,
                recoverable=False,
                errors=[f"Cannot parse: {exc}"],
            )
