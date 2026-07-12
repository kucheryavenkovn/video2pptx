# FILE: src/video2pptx/application/errors.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Application-layer exception hierarchy for service failures, precondition, and cancellation.
#   SCOPE: ApplicationError, PreconditionError, CancellationError, StageFailureError
#   DEPENDS: none
#   LINKS: M-APP-COMMON, M-APP-INPUT-RESOLVER, V-REF-DETECTION-INPUT
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ApplicationError - base class for all application-layer exceptions
#   PreconditionError - raised when required input or project state is missing/invalid
#   CancellationError - raised when a cancellation token is triggered
#   StageFailureError - typed failure with stage name and cause
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Add PreconditionError for input resolution
# END_CHANGE_SUMMARY

from __future__ import annotations


class ApplicationError(Exception):
    """Base class for all application-layer exceptions."""


class PreconditionError(ApplicationError):
    """Raised when required input or project state is missing/invalid.

    Used by resolve_project_input/resolve_project_path when canonical Project
    value is absent and no override is provided. Not wrapped in StageFailureError
    because the error belongs to the caller's contract, not the service execution.
    """


class CancellationError(ApplicationError):
    """Raised when a cooperative cancellation token is triggered."""

    def __init__(self, stage: str = "", message: str = "Operation cancelled") -> None:
        self.stage = stage
        super().__init__(message)


class StageFailureError(ApplicationError):
    """Typed failure raised by a stage service with stage name and cause."""

    def __init__(
        self,
        stage: str,
        message: str,
        *,
        cause: Exception | None = None,
    ) -> None:
        self.stage = stage
        self.cause = cause
        super().__init__(f"[{stage}] {message}")
