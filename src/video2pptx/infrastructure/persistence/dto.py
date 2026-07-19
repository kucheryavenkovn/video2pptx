# FILE: src/video2pptx/infrastructure/persistence/dto.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Strict schema 2.0 persistence DTOs for the canonical Project aggregate document.
#   SCOPE: Project, slide, pipeline, score, artifact, and extension document validation.
#   DEPENDS: pydantic, video2pptx.domain.artifacts, video2pptx.domain.errors, video2pptx.domain.pipeline_state
#   LINKS: M-PERSIST-DTO, V-PERSIST-DTO
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   StageStateDocument - complete persisted state for one pipeline stage
#   PipelineDocument - exact persisted state for every canonical pipeline stage
#   SlideDocument - strict persisted slide entity data
#   ScoreDocument - validated score waveform with paired timestamps and values
#   ArtifactDocument - named portable generated artifact references
#   ProjectDocumentV2 - canonical schema 2.0 project document
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Introduce strict schema 2.0 canonical persistence DTOs
# END_CHANGE_SUMMARY

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from video2pptx.domain.artifacts import ArtifactRef
from video2pptx.domain.errors import ValidationError as DomainValidationError
from video2pptx.domain.pipeline_state import PIPELINE_STAGES, StageStatus


class _StrictDocument(BaseModel):
    """Base configuration shared by canonical persistence DTOs."""

    model_config = ConfigDict(extra="forbid", strict=True)


class StageStateDocument(_StrictDocument):
    """Complete serializable state of one pipeline stage."""

    status: StageStatus = StageStatus.NOT_STARTED
    operation_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: dict[str, Any] | None = None


class PipelineDocument(_StrictDocument):
    """Pipeline state with exactly the canonical stage names."""

    stages: dict[str, StageStateDocument]

    @field_validator("stages")
    @classmethod
    def validate_stage_names(
        cls,
        value: dict[str, StageStateDocument],
    ) -> dict[str, StageStateDocument]:
        expected = set(PIPELINE_STAGES)
        actual = set(value)
        if actual != expected:
            missing = sorted(expected - actual)
            unknown = sorted(actual - expected)
            raise ValueError(
                f"pipeline stages must match canonical set; missing={missing}, unknown={unknown}"
            )
        return value


class SlideDocument(_StrictDocument):
    """Strict persisted representation of a domain slide."""

    uid: str = Field(min_length=1)
    index: int = Field(ge=1)
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    image: str | None = None
    representative_timestamp: float = Field(ge=0)
    transcript: str = ""
    notes: str = ""
    llm_description: str | None = None
    confidence: float = Field(default=1.0, ge=0, le=1)
    manual: bool = False
    extra: dict[str, Any] = Field(default_factory=dict)


    @field_validator("uid")
    @classmethod
    def validate_uid(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("uid must not be blank")
        return value

    @field_validator("image")
    @classmethod
    def validate_image(cls, value: str | None) -> str | None:
        if value is not None:
            try:
                ArtifactRef.parse(value)
            except DomainValidationError as exc:
                raise ValueError(str(exc)) from exc
        return value

    @model_validator(mode="after")
    def validate_interval(self) -> SlideDocument:
        numbers = (self.start, self.end, self.representative_timestamp, self.confidence)
        if not all(math.isfinite(number) for number in numbers):
            raise ValueError("slide numeric fields must be finite")
        if self.end <= self.start:
            raise ValueError("slide end must be greater than start")
        if not self.start <= self.representative_timestamp <= self.end:
            raise ValueError("representative_timestamp must be inside slide interval")
        return self


class ScoreDocument(_StrictDocument):
    """Persisted preview waveform with paired finite values."""

    timestamps: list[float] = Field(default_factory=list)
    values: list[float] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_pairs(self) -> ScoreDocument:
        if len(self.timestamps) != len(self.values):
            raise ValueError("score timestamps and values must have equal lengths")
        if not all(math.isfinite(value) for value in self.timestamps + self.values):
            raise ValueError("score timestamps and values must be finite")
        if any(value < 0 for value in self.timestamps):
            raise ValueError("score timestamps must be non-negative")
        if any(current < previous for previous, current in zip(self.timestamps, self.timestamps[1:], strict=False)):
            raise ValueError("score timestamps must be monotonic")
        return self


class ArtifactDocument(_StrictDocument):
    """Named portable generated artifact references."""

    items: dict[str, str] = Field(default_factory=dict)

    @field_validator("items")
    @classmethod
    def validate_items(cls, value: dict[str, str]) -> dict[str, str]:
        for name, path in value.items():
            if not name.strip():
                raise ValueError("artifact name must not be blank")
            try:
                ArtifactRef.parse(path)
            except DomainValidationError as exc:
                raise ValueError(str(exc)) from exc
        return value


class DetectionConfigDocument(BaseModel):
    """Canonical typed detection settings for schema 2.0."""
    sample_fps: float = 2.0
    decoder_backend: str = "auto"
    slide_roi: str = "auto"
    ignore_rois: list[str] = Field(default_factory=list)
    threshold: float | str = "auto"
    min_slide_duration: float = Field(default=2.0, ge=0.5)
    # 0.0 disables debounce; wall-clock seconds (Phase 21 Wave 5)
    min_stable_duration: float = Field(default=2.0, ge=0.0)
    dedupe_enabled: bool = True
    # Default None = legacy missing field loads as native (Phase 20).
    # New projects write explicit 480 via Project.create_new().
    analysis_max_side: int | None = None

    @field_validator("analysis_max_side", mode="before")
    @classmethod
    def _validate_analysis_max_side(cls, value: object) -> int | None:
        """Product range only: null or int in [240, 2160]. No silent clamp/480."""
        from video2pptx.analysis_quality import validate_analysis_max_side

        return validate_analysis_max_side(value, allow_none=True)


class ProjectDocumentV2(_StrictDocument):
    """Canonical schema 2.0 project document.

    Project location is runtime context and is intentionally not represented.
    Unknown canonical fields are rejected; explicit compatibility data belongs
    under ``extensions``.
    """

    schema_version: Literal["2.0"] = "2.0"
    revision: str = Field(min_length=1)
    name: str = Field(min_length=1)
    video_path: str = ""
    subtitle_path: str | None = None
    slides: list[SlideDocument] = Field(default_factory=list)
    pipeline: PipelineDocument
    scores: ScoreDocument = Field(default_factory=ScoreDocument)
    artifacts: ArtifactDocument = Field(default_factory=ArtifactDocument)
    detection: DetectionConfigDocument = Field(default_factory=DetectionConfigDocument)
    extensions: dict[str, Any] = Field(default_factory=dict)

    @field_validator("revision", "name")
    @classmethod
    def validate_non_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value

    @model_validator(mode="after")
    def validate_slides(self) -> ProjectDocumentV2:
        ids = [slide.uid for slide in self.slides]
        if len(ids) != len(set(ids)):
            raise ValueError("slide UIDs must be unique")
        expected_indices = list(range(1, len(self.slides) + 1))
        actual_indices = [slide.index for slide in self.slides]
        if actual_indices != expected_indices:
            raise ValueError("slide indices must be contiguous and 1-based")
        for previous, current in zip(self.slides, self.slides[1:], strict=False):
            if current.start < previous.end:
                raise ValueError("slide intervals must not overlap")
        return self
