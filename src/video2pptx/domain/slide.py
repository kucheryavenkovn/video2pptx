# FILE: src/video2pptx/domain/slide.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Slide entity and immutable SlideView projection.
#   SCOPE: Slide (mutable internal), SlideView (frozen public), from_dict/to_dict
#   DEPENDS: video2pptx.domain.identifiers, video2pptx.domain.time, video2pptx.domain.artifacts
#   LINKS: M-DOMAIN-SLIDE, M-DOMAIN-PROJECT
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   Slide - mutable entity with stable SlideId, TimeInterval, image ref, transcript
#   SlideView - immutable frozen public projection of Slide state
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Add SlideView, validate representative_timestamp, enforce confidence range
# END_CHANGE_SUMMARY

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from video2pptx.domain.artifacts import ArtifactRef
from video2pptx.domain.errors import InvalidRepresentativeTimestamp, InvalidSlideConfidence
from video2pptx.domain.identifiers import SlideId
from video2pptx.domain.time import TimeInterval


@dataclass
class Slide:
    """Domain slide entity.

    Identity is the stable SlideId. All other fields are mutable through the
    aggregate root. TimeInterval enforces interval invariants on construction
    and on any update via the aggregate.
    """

    slide_id: SlideId
    interval: TimeInterval
    index: int = 0
    image: ArtifactRef | None = None
    representative_timestamp: float = 0.0
    transcript: str = ""
    notes: str = ""
    llm_description: str | None = None
    confidence: float = 1.0
    manual: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.representative_timestamp < self.interval.start or self.representative_timestamp > self.interval.end:
            raise InvalidRepresentativeTimestamp(
                f"representative_timestamp {self.representative_timestamp} "
                f"must be within [{self.interval.start}, {self.interval.end}]"
            )
        if not (0.0 <= self.confidence <= 1.0):
            raise InvalidSlideConfidence(
                f"confidence must be in [0, 1], got {self.confidence}"
            )

    @property
    def start(self) -> float:
        return self.interval.start

    @property
    def end(self) -> float:
        return self.interval.end

    @property
    def duration(self) -> float:
        return self.interval.duration

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for persistence DTO conversion."""
        return {
            "uid": str(self.slide_id),
            "index": self.index,
            "start": self.interval.start,
            "end": self.interval.end,
            "duration": self.interval.duration,
            "image": str(self.image) if self.image else "",
            "representative_timestamp": self.representative_timestamp,
            "transcript": self.transcript,
            "notes": self.notes,
            "llm_description": self.llm_description,
            "confidence": self.confidence,
            "manual": self.manual,
            **self.extra,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Slide:
        """Reconstruct a Slide from a persistence dict (e.g. slides.json entry)."""
        uid = SlideId.parse(data.get("uid") or data.get("id") or SlideId.new().value)
        start = float(data["start"])
        end = float(data["end"])
        interval = TimeInterval(start, end)
        image_raw = data.get("image", "")
        image = ArtifactRef.parse(image_raw) if image_raw else None

        rep_ts = float(data.get("representative_timestamp", 0.0))
        if not start <= rep_ts <= end:
            rep_ts = (start + end) / 2

        return cls(
            slide_id=uid,
            interval=interval,
            index=int(data.get("index", 0)),
            image=image,
            representative_timestamp=rep_ts,
            transcript=str(data.get("transcript", "")),
            notes=str(data.get("notes", "")),
            llm_description=data.get("llm_description"),
            confidence=float(data.get("confidence", 1.0)),
            manual=bool(data.get("manual", False)),
            extra={
                k: v
                for k, v in data.items()
                if k
                not in {
                    "uid",
                    "id",
                    "index",
                    "start",
                    "end",
                    "duration",
                    "image",
                    "representative_timestamp",
                    "transcript",
                    "notes",
                    "llm_description",
                    "confidence",
                    "manual",
                }
            },
        )


@dataclass(frozen=True, slots=True)
class SlideView:
    """Immutable public projection of a Slide.

    External code receives SlideView and cannot mutate the aggregate's
    internal Slide entity. All fields are copies or immutable value objects.
    """

    slide_id: SlideId
    interval: TimeInterval
    index: int
    image: ArtifactRef | None
    representative_timestamp: float
    transcript: str
    notes: str
    llm_description: str | None
    confidence: float
    manual: bool

    @property
    def start(self) -> float:
        return self.interval.start

    @property
    def end(self) -> float:
        return self.interval.end

    @property
    def duration(self) -> float:
        return self.interval.duration

    @classmethod
    def from_slide(cls, slide: Slide) -> SlideView:
        return cls(
            slide_id=slide.slide_id,
            interval=slide.interval,
            index=slide.index,
            image=slide.image,
            representative_timestamp=slide.representative_timestamp,
            transcript=slide.transcript,
            notes=slide.notes,
            llm_description=slide.llm_description,
            confidence=slide.confidence,
            manual=slide.manual,
        )
