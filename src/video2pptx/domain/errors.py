# FILE: src/video2pptx/domain/errors.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Domain-level exceptions shared across value objects and aggregate.
#   SCOPE: DomainError, ValidationError, IllegalStateTransition
#   DEPENDS: none
#   LINKS: M-DOMAIN-VALUE, M-DOMAIN-PROJECT
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   DomainError - base class for all domain exceptions
#   ValidationError - invalid value object construction
#   IllegalStateTransition - invalid pipeline stage transition
# END_MODULE_MAP

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain-level exceptions."""


class ValidationError(DomainError):
    """Raised when a value object invariant is violated."""


class IllegalStateTransition(DomainError):
    """Raised when a pipeline stage transition is not allowed."""
