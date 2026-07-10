# FILE: src/video2pptx/domain/errors.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Domain-level exceptions shared across value objects, entities, and aggregate.
#   SCOPE: DomainError hierarchy for slides, pipeline, identity, intervals, images.
#   DEPENDS: none
#   LINKS: M-DOMAIN-VALUE, M-DOMAIN-PROJECT, M-PORT-REPO
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   DomainError - base class for all domain exceptions
#   ValidationError - invalid value object construction
#   IllegalStateTransition - invalid pipeline stage transition
#   SlideNotFound - slide lookup failed
#   DuplicateSlideId - two slides share the same SlideId
#   OverlappingSlides - slide intervals overlap
#   InvalidSlideOrder - slides not sorted by start
#   TimestampOutsideVideo - timestamp beyond video duration
#   InvalidRepresentativeTimestamp - representative ts outside interval
#   InvalidSlideConfidence - confidence out of range or non-finite
#   ProjectInvariantError - aggregate-level invariant violated
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Add specialized slide and project domain errors
# END_CHANGE_SUMMARY

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain-level exceptions."""


class ValidationError(DomainError):
    """Raised when a value object invariant is violated."""


class IllegalStateTransition(DomainError):
    """Raised when a pipeline stage transition is not allowed."""


class SlideNotFound(DomainError):
    """Raised when a slide lookup by SlideId fails."""


class DuplicateSlideId(DomainError):
    """Raised when two slides in the same aggregate share a SlideId."""


class OverlappingSlides(DomainError):
    """Raised when slide intervals overlap."""


class InvalidSlideOrder(DomainError):
    """Raised when slides are not sorted by start time."""


class TimestampOutsideVideo(DomainError):
    """Raised when a timestamp falls outside video duration."""


class InvalidRepresentativeTimestamp(DomainError):
    """Raised when representative_timestamp is outside the slide interval."""


class InvalidSlideConfidence(DomainError):
    """Raised when confidence is non-finite or outside [0, 1]."""


class ProjectInvariantError(DomainError):
    """Raised when an aggregate-level invariant is violated."""
