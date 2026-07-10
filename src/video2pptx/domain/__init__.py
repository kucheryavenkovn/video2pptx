# FILE: src/video2pptx/domain/__init__.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Domain layer package — PySide6-free value objects, entities, and aggregate root.
#   SCOPE: SlideId, TimeInterval, ArtifactRef, PipelineState, Slide, Project, domain errors
#   DEPENDS: none (pure Python)
#   LINKS: M-DOMAIN-VALUE, M-DOMAIN-SLIDE, M-DOMAIN-PROJECT
#   ROLE: BARREL
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   SlideId - stable slide identifier
#   TimeInterval - validated immutable time interval
#   ArtifactRef - portable relative artifact path
#   Slide - domain slide entity
#   Project - aggregate root controlling slide lifecycle and pipeline state
#   PipelineState - pipeline stage state machine
#   StageStatus - enum of stage statuses
#   ValidationError - invalid value object construction
#   IllegalStateTransition - invalid pipeline transition
# END_MODULE_MAP

from video2pptx.domain.artifacts import ArtifactRef, migrate_legacy_artifact
from video2pptx.domain.errors import (
    DomainError,
    DuplicateSlideId,
    IllegalStateTransition,
    InvalidRepresentativeTimestamp,
    InvalidSlideConfidence,
    InvalidSlideOrder,
    OverlappingSlides,
    ProjectInvariantError,
    SlideNotFound,
    TimestampOutsideVideo,
    ValidationError,
)
from video2pptx.domain.identifiers import SlideId
from video2pptx.domain.pipeline_state import (
    DOWNSTREAM,
    PIPELINE_STAGES,
    VALID_TRANSITIONS,
    PipelineState,
    StageState,
    StageStatus,
)
from video2pptx.domain.project import Project
from video2pptx.domain.slide import Slide, SlideView
from video2pptx.domain.time import TIME_EPSILON, TimeInterval

__all__ = [
    "ArtifactRef",
    "DomainError",
    "DOWNSTREAM",
    "DuplicateSlideId",
    "IllegalStateTransition",
    "InvalidRepresentativeTimestamp",
    "InvalidSlideConfidence",
    "InvalidSlideOrder",
    "migrate_legacy_artifact",
    "OverlappingSlides",
    "PIPELINE_STAGES",
    "PipelineState",
    "Project",
    "ProjectInvariantError",
    "Slide",
    "SlideId",
    "SlideNotFound",
    "SlideView",
    "StageState",
    "StageStatus",
    "TIME_EPSILON",
    "TimestampOutsideVideo",
    "TimeInterval",
    "VALID_TRANSITIONS",
    "ValidationError",
]
