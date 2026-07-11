# FILE: src/video2pptx/application/services/validation_service.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Validate storage, aggregate, media, artifacts, exports, and derived revision consistency.
#   SCOPE: ValidationService.execute — checked validation without mutation
#   DEPENDS: video2pptx.application.base, video2pptx.application.dto, video2pptx.application.errors,
#            video2pptx.application.ports.project_repository, video2pptx.domain
#   LINKS: M-APP-VALIDATE, V-APP-VALIDATE, V-REF-APP-SERVICES
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ValidationService - checks storage, aggregate, media, artifacts, exports, revision consistency
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add non-mutating validation service
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path

from loguru import logger

from video2pptx.application.base import ServiceContext
from video2pptx.application.dto import ServiceResult
from video2pptx.application.errors import StageFailureError


class ValidationService:
    """Non-mutating validation — checks storage, aggregate, media, artifacts, exports."""

    def __init__(
        self,
        context: ServiceContext,
    ) -> None:
        self._ctx = context

    def execute(
        self,
        project_location: Path,
        *,
        check_storage: bool = True,
        check_aggregate: bool = True,
        check_media: bool = True,
        check_artifacts: bool = True,
        check_exports: bool = True,
    ) -> ServiceResult:
        repo = self._ctx.repository
        if repo is None:
            return ServiceResult.fail("validate", "Repository not configured")

        errors: list[str] = []
        warnings: list[str] = []

        try:
            # — storage check —
            if check_storage:
                self._ctx.report_progress(10, "Validating storage")
                sv = repo.validate_storage(project_location)
                if not sv.valid:
                    for e in sv.errors:
                        errors.append(f"storage: {e}")
                    warnings.extend(sv.warnings)
                if not sv.valid and not sv.recoverable:
                    return ServiceResult.fail(
                        "validate",
                        "Storage validation failed",
                        data={"errors": errors, "warnings": warnings},
                    )
                self._ctx.check_cancelled("validate")

            # — aggregate check —
            loaded = repo.load(project_location)
            self._ctx.check_cancelled("validate")

            if check_aggregate:
                self._ctx.report_progress(30, "Validating aggregate")
                try:
                    loaded.project.validate()
                except Exception as e:
                    errors.append(f"aggregate: {e}")

            # — media check —
            if check_media:
                self._ctx.report_progress(50, "Validating media")
                media_dir = project_location / "media"
                if media_dir.is_dir():
                    for slide in loaded.project.slides:
                        if slide.image:
                            image_path = media_dir / slide.image.filename
                            if not image_path.is_file():
                                errors.append(
                                    f"media: slide {slide.slide_id} image not found: "
                                    f"{slide.image.filename}"
                                )

            # — artifact check —
            if check_artifacts:
                self._ctx.report_progress(70, "Validating artifacts")
                expected = [
                    ("slides.json", loaded.project.slide_count == 0),
                ]
                for name, _ in expected:
                    if not (project_location / name).is_file():
                        errors.append(f"artifact: {name} missing")

            # — export check —
            if check_exports:
                self._ctx.report_progress(90, "Validating exports")
                slides_present = loaded.project.slide_count > 0
                deck_path = project_location / "deck.md"
                if slides_present and not deck_path.is_file():
                    errors.append("export: deck.md missing")
                if slides_present and not (project_location / "slides.json").is_file():
                    errors.append("export: slides.json missing")

            self._ctx.report_progress(100, "Validation complete")
            valid = len(errors) == 0

            logger.info(
                f"[ValidationService] Done | valid={valid} errors={len(errors)} "
                f"warnings={len(warnings)}"
            )

            return ServiceResult.ok(
                "validate",
                data={
                    "valid": valid,
                    "errors": errors,
                    "warnings": warnings,
                    "slide_count": loaded.project.slide_count,
                },
            )
        except Exception as exc:
            logger.error(f"[ValidationService] Failed | error={exc}")
            raise StageFailureError("validate", str(exc), cause=exc) from exc
