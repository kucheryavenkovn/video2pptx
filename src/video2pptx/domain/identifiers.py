# FILE: src/video2pptx/domain/identifiers.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Stable slide identifier that survives reordering, reopen, and CRUD.
#   SCOPE: SlideId value object with creation, parsing, and invariant enforcement.
#   DEPENDS: none
#   LINKS: M-DOMAIN-VALUE
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   SlideId - frozen dataclass wrapping a non-empty validated string identifier
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Initial SlideId implementation
# END_CHANGE_SUMMARY

from __future__ import annotations

import uuid
from dataclasses import dataclass

from video2pptx.domain.errors import ValidationError


@dataclass(frozen=True, slots=True)
class SlideId:
    """Immutable, hashable slide identifier.

    The value is a non-empty, non-whitespace string.
    Creating a new SlideId does not depend on index, order, or filesystem state.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value or not self.value.strip():
            raise ValidationError("SlideId value must be non-empty and non-whitespace")

    @classmethod
    def new(cls) -> SlideId:
        """Generate a new random SlideId."""
        return cls(uuid.uuid4().hex[:12])

    @classmethod
    def parse(cls, value: str) -> SlideId:
        """Reconstruct a SlideId from a persisted string.

        Raises ValidationError if the string is empty or whitespace-only.
        """
        return cls(value)

    def __str__(self) -> str:
        return self.value
