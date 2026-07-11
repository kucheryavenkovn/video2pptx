# FILE: src/video2pptx/application/errors.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Application-layer exception hierarchy for service failures and cancellation.
#   SCOPE: ApplicationError, CancellationError, StageFailureError
#   DEPENDS: none
#   LINKS: M-APP-COMMON, V-REF-APP-SERVICES
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ApplicationError - base class for all application-layer exceptions
#   CancellationError - raised when a cancellation token is triggered
#   StageFailureError - typed failure with stage name and cause
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add common application error hierarchy
# END_CHANGE_SUMMARY

from __future__ import annotations


class ApplicationError(Exception):
    """Base class for all application-layer exceptions."""


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
