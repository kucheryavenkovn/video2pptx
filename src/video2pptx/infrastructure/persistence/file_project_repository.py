# FILE: src/video2pptx/infrastructure/persistence/file_project_repository.py
# VERSION: 1.2.0
# START_MODULE_CONTRACT
#   PURPOSE: File-based ProjectRepository implementation with atomic writes, migration, and revision tracking.
#   SCOPE: create, load, save, exists, validate_storage
#   DEPENDS: repository port, persistence DTO/migrations/errors/mapper, json_io
#   LINKS: M-PORT-REPO, M-FILE-REPO, M-PERSIST-DTO, M-PERSIST-MIGRATIONS
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   FileProjectRepository - concrete repository implementing ProjectRepository protocol
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.2.0 - Revision derived slides and validate canonical/domain/derived consistency
# END_CHANGE_SUMMARY

from __future__ import annotations

import json
import uuid
from pathlib import Path

from loguru import logger
from pydantic import ValidationError as PydanticValidationError

from video2pptx.application.ports.project_repository import (
    LoadedProject,
    SaveResult,
    StorageValidationResult,
)
from video2pptx.domain.project import Project
from video2pptx.infrastructure.persistence.dto import ProjectDocumentV2
from video2pptx.infrastructure.persistence.errors import (
    ProjectAlreadyExists,
    ProjectAtomicWriteError,
    ProjectDocumentCorrupted,
    ProjectNotFound,
    ProjectRevisionConflict,
    ProjectSchemaUnsupported,
)
from video2pptx.infrastructure.persistence.mapper import ProjectMapper
from video2pptx.infrastructure.persistence.migrations import migrate_v1_to_v2
from video2pptx.utils.json_io import write_json_atomic


class FileProjectRepository:
    """File-based repository implementing the ProjectRepository protocol.

    project.json is the canonical source of truth.
    slides.json is a derived compatibility artifact regenerated on save.
    All writes are atomic (temp + rename).
    Revision tracking uses a UUID per committed save.
    """

    SCHEMA_VERSION = "2.0"

    # START_CONTRACT: create
    #   PURPOSE: Create canonical project storage and return its first LoadedProject revision unit.
    #   INPUTS: { location: Path, project: Project }
    #   OUTPUTS: { LoadedProject }
    #   SIDE_EFFECTS: creates directory; atomically writes project.json and slides.json
    #   LINKS: M-FILE-REPO, M-PORT-REPO
    # END_CONTRACT: create
    def create(self, location: Path, project: Project) -> LoadedProject:
        """Create a new canonical project and return its revision unit."""
        location = Path(location)
        if location.exists() and any(location.iterdir()):
            raise ProjectAlreadyExists(
                f"Project directory not empty: {location}",
                path=str(location),
            )
        location.mkdir(parents=True, exist_ok=True)
        project.output_dir = str(location)
        result = self.save(project, location, expected_revision=None)
        logger.info(f"[FileProjectRepository] Created | location={location}")
        return LoadedProject(
            project=project,
            location=location,
            revision=result.revision,
            warnings=tuple(result.warnings),
        )

    # START_CONTRACT: load
    #   PURPOSE: Load strict V2 storage or deterministically migrate raw legacy storage in memory.
    #   INPUTS: { location: Path }
    #   OUTPUTS: { LoadedProject }
    #   SIDE_EFFECTS: reads project.json; emits structured logs
    #   LINKS: M-FILE-REPO, M-PERSIST-DTO, M-PERSIST-MIGRATIONS
    # END_CONTRACT: load
    def load(self, location: Path) -> LoadedProject:
        """Load strict V2 data or deterministically migrate raw legacy data."""
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

        schema_version = str(data.get("schema_version", "1.0"))
        warnings: list[str] = []
        migrated = schema_version == "1.0"
        try:
            if migrated:
                document = migrate_v1_to_v2(data, location)
                warnings.append("Legacy schema migrated in memory; save to commit schema 2.0")
            elif schema_version == self.SCHEMA_VERSION:
                document = ProjectDocumentV2.model_validate_json(raw)
            else:
                raise ProjectSchemaUnsupported(
                    f"Unsupported schema_version: {schema_version}",
                    path=str(project_json),
                )
        except ProjectSchemaUnsupported:
            raise
        except (PydanticValidationError, ValueError, TypeError) as exc:
            raise ProjectDocumentCorrupted(
                f"Invalid project data: {exc}",
                path=str(project_json),
            ) from exc

        project = ProjectMapper.to_domain(document, location)
        logger.info(
            f"[FileProjectRepository] Loaded | location={location} "
            f"revision={document.revision} migrated={migrated} slides={project.slide_count}"
        )
        return LoadedProject(
            project=project,
            location=location,
            revision=document.revision,
            warnings=tuple(warnings),
            migrated=migrated,
        )

    # START_CONTRACT: save
    #   PURPOSE: Optimistically commit a strict canonical V2 document and derived compatibility data.
    #   INPUTS: { project: Project, location: Path, expected_revision: str|None }
    #   OUTPUTS: { SaveResult - new canonical revision and warnings }
    #   SIDE_EFFECTS: atomically writes project.json and slides.json
    #   LINKS: M-FILE-REPO, M-PERSIST-DTO
    # END_CONTRACT: save
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
                existing_raw = project_json.read_text(encoding="utf-8")
                existing = json.loads(existing_raw)
                existing_schema = str(existing.get("schema_version", "1.0"))
                if existing_schema == self.SCHEMA_VERSION:
                    current_revision = ProjectDocumentV2.model_validate_json(
                        existing_raw
                    ).revision
                elif existing_schema == "1.0":
                    current_revision = migrate_v1_to_v2(existing, location).revision
                else:
                    raise ProjectSchemaUnsupported(
                        f"Unsupported schema_version: {existing_schema}",
                        path=str(project_json),
                    )
            except ProjectSchemaUnsupported:
                raise
            except (json.JSONDecodeError, UnicodeDecodeError, PydanticValidationError, ValueError, TypeError) as exc:
                raise ProjectDocumentCorrupted(
                    f"Cannot verify existing project revision: {exc}",
                    path=str(project_json),
                    recoverable=False,
                ) from exc
            if current_revision != expected_revision:
                raise ProjectRevisionConflict(
                    f"Revision mismatch: expected={expected_revision} "
                    f"current={current_revision}",
                    path=str(project_json),
                    recoverable=True,
                )

        new_revision = uuid.uuid4().hex
        document = ProjectMapper.to_document(project, new_revision)

        try:
            write_json_atomic(
                project_json,
                document.model_dump(mode="json"),
                indent=2,
            )
        except Exception as exc:
            raise ProjectAtomicWriteError(
                f"Failed to write project.json: {exc}",
                path=str(project_json),
            ) from exc

        slides_doc = ProjectMapper.to_slides_document(project, new_revision)
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

    # START_CONTRACT: validate_storage
    #   PURPOSE: Validate canonical DTO/domain mapping and derived revision/content consistency.
    #   INPUTS: { location: Path }
    #   OUTPUTS: { StorageValidationResult }
    #   SIDE_EFFECTS: reads project.json and slides.json; emits load logs
    #   LINKS: M-FILE-REPO, V-FILE-REPO
    # END_CONTRACT: validate_storage
    def validate_storage(self, location: Path) -> StorageValidationResult:
        """Validate canonical storage and its revisioned derived artifact."""
        location = Path(location)
        if not (location / "project.json").is_file():
            return StorageValidationResult(
                valid=False,
                recoverable=False,
                errors=["project.json not found"],
            )

        try:
            loaded = self.load(location)
        except (ProjectDocumentCorrupted, ProjectSchemaUnsupported, ProjectNotFound) as exc:
            return StorageValidationResult(
                valid=False,
                recoverable=exc.recoverable,
                errors=[str(exc)],
            )

        if loaded.migrated:
            return StorageValidationResult(
                valid=True,
                recoverable=True,
                schema_version="1.0",
                warnings=list(loaded.warnings),
                recovery_actions=["save project to commit schema 2.0 and regenerate slides.json"],
            )

        slides_json = location / "slides.json"
        if not slides_json.is_file():
            return StorageValidationResult(
                valid=False,
                recoverable=True,
                schema_version=self.SCHEMA_VERSION,
                errors=["slides.json derived artifact not found"],
                recovery_actions=["save project to regenerate slides.json"],
            )

        try:
            derived = json.loads(slides_json.read_text(encoding="utf-8"))
            if not isinstance(derived, dict):
                raise ValueError("slides.json root must be an object")
            if derived.get("source_revision") != loaded.revision:
                raise ValueError(
                    "slides.json source_revision does not match canonical revision"
                )
            derived_slides = derived.get("slides")
            if not isinstance(derived_slides, list) or not all(
                isinstance(slide, dict) for slide in derived_slides
            ):
                raise ValueError("slides.json slides must be a list of objects")
            canonical_ids = [view.slide_id.value for view in loaded.project.slides]
            derived_ids = [str(slide.get("uid", "")) for slide in derived_slides]
            if derived_ids != canonical_ids:
                raise ValueError("slides.json slide IDs/count do not match canonical project")
            if derived.get("score_timestamps", []) != loaded.project.score_timestamps:
                raise ValueError("slides.json score timestamps do not match canonical project")
            if derived.get("score_values", []) != loaded.project.score_values:
                raise ValueError("slides.json score values do not match canonical project")
        except (json.JSONDecodeError, UnicodeDecodeError, TypeError, ValueError) as exc:
            return StorageValidationResult(
                valid=False,
                recoverable=True,
                schema_version=self.SCHEMA_VERSION,
                errors=[str(exc)],
                recovery_actions=["save project to regenerate slides.json"],
            )

        return StorageValidationResult(
            valid=True,
            recoverable=True,
            schema_version=self.SCHEMA_VERSION,
        )
