# FILE: src/video2pptx/domain/__init__.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Domain layer package — PySide6-free value objects and pipeline state.
#   SCOPE: SlideId, TimeInterval, ArtifactRef, PipelineState, StageStatus, domain errors
#   DEPENDS: none (pure Python)
#   LINKS: M-DOMAIN-VALUE
#   ROLE: BARREL
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   SlideId - stable slide identifier
#   TimeInterval - validated immutable time interval
#   ArtifactRef - portable relative artifact path
#   PipelineState - pipeline stage state machine
#   StageStatus - enum of stage statuses
#   ValidationError - invalid value object construction
#   IllegalStateTransition - invalid pipeline transition
# END_MODULE_MAP

from video2pptx.domain.artifacts import ArtifactRef, migrate_legacy_artifact
from video2pptx.domain.errors import (
    DomainError,
    IllegalStateTransition,
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
from video2pptx.domain.time import TIME_EPSILON, TimeInterval

__all__ = [
    "ArtifactRef",
    "DomainError",
    "DOWNSTREAM",
    "IllegalStateTransition",
    "migrate_legacy_artifact",
    "PIPELINE_STAGES",
    "PipelineState",
    "SlideId",
    "StageState",
    "StageStatus",
    "TIME_EPSILON",
    "TimeInterval",
    "VALID_TRANSITIONS",
    "ValidationError",
]
