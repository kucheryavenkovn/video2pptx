# FILE: src/video2pptx/domain/project.py
# VERSION: 1.3.0
# START_MODULE_CONTRACT
#   PURPOSE: Project aggregate root — owns slides, enforces invariants, manages pipeline state.
#   SCOPE: add_slide, remove_slide, move_slide, resize_slide, replace_detected_slides,
#          invalidate_downstream_from, set_image, clear_image, to_slides_dict, from_slides_dict,
#          validate, _validate_candidate_slides, DetectionConfig
#   DEPENDS: video2pptx.domain.slide, video2pptx.domain.identifiers, video2pptx.domain.time,
#            video2pptx.domain.pipeline_state, video2pptx.domain.artifacts, video2pptx.domain.errors
#   LINKS: M-DOMAIN-PROJECT
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   Project - aggregate root controlling slide lifecycle and pipeline state
#   DetectionConfig - typed detection settings for Project
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.4.0 - Add DetectionConfig with typed detection settings
# END_CHANGE_SUMMARY

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from video2pptx.domain.artifacts import ArtifactRef
from video2pptx.domain.errors import (
    DomainError,
    DuplicateSlideId,
    InvalidRepresentativeTimestamp,
    OverlappingSlides,
    SlideNotFound,
    ValidationError,
)
from video2pptx.domain.identifiers import SlideId
from video2pptx.domain.pipeline_state import PipelineState, StageStatus
from video2pptx.domain.slide import Slide, SlideView
from video2pptx.domain.time import TimeInterval


def _detection_config_equal(a: DetectionConfig, b: DetectionConfig) -> bool:
    """Structural equality for DetectionConfig (no-op detection)."""
    return (
        a.sample_fps == b.sample_fps
        and a.decoder_backend == b.decoder_backend
        and a.slide_roi == b.slide_roi
        and list(a.ignore_rois) == list(b.ignore_rois)
        and a.threshold == b.threshold
        and a.min_slide_duration == b.min_slide_duration
        and a.min_stable_duration == b.min_stable_duration
        and a.dedupe_enabled == b.dedupe_enabled
        and a.analysis_max_side == b.analysis_max_side
    )


@dataclass
class DetectionConfig:
    """Canonical detection settings for a Project. Replaces legacy extensions.detection.

    analysis_max_side semantics (Phase 20):
    - Domain default is None (safe / does not invent FAST for accidental constructs).
    - New projects must set NEW_PROJECT_ANALYSIS_MAX_SIDE (480) explicitly at create time.
    - Legacy documents missing the field load as None via DTO default None.
    """
    sample_fps: float = 2.0
    decoder_backend: str = "auto"
    slide_roi: str = "auto"
    ignore_rois: list[str] = field(default_factory=list)
    threshold: float | str = "auto"
    min_slide_duration: float = 2.0
    min_stable_duration: float = 2.0
    dedupe_enabled: bool = True
    # Pass1 analysis max side only; None = native. Screenshots remain full-res.
    analysis_max_side: int | None = None


class Project:
    """Domain aggregate root for a video2pptx project.

    Enforces slide interval invariants (no overlaps, valid intervals).
    Manages pipeline state transitions and downstream invalidation.
    Does NOT own persistence — that is the repository's job (Step 4).
    Does NOT import PySide6, cv2, or any infrastructure.
    """

    def __init__(
        self,
        name: str = "Untitled",
        video_path: str = "",
        subtitle_path: str = "",
        output_dir: str = "",
        artifacts: dict[str, ArtifactRef] | None = None,
        extensions: dict[str, Any] | None = None,
    ) -> None:
        self.name: str = name
        self.video_path: str = video_path
        self.subtitle_path: str = subtitle_path
        self.output_dir: str = output_dir
        self._slides: list[Slide] = []
        self.pipeline: PipelineState = PipelineState()
        self.score_timestamps: list[float] = []
        self.score_values: list[float] = []
        self.artifacts: dict[str, ArtifactRef] = dict(artifacts or {})
        self.extensions: dict[str, Any] = dict(extensions or {})
        self.detection: DetectionConfig = DetectionConfig()

    @classmethod
    def create_new(
        cls,
        name: str = "Untitled",
        video_path: str = "",
        subtitle_path: str = "",
        output_dir: str = "",
    ) -> Project:
        """Factory for new projects: explicit FAST analysis_max_side=480."""
        from video2pptx.analysis_quality import NEW_PROJECT_ANALYSIS_MAX_SIDE

        project = cls(
            name=name,
            video_path=video_path,
            subtitle_path=subtitle_path,
            output_dir=output_dir,
        )
        project.detection.analysis_max_side = NEW_PROJECT_ANALYSIS_MAX_SIDE
        return project

    def apply_detection_config(self, new_config: DetectionConfig) -> bool:
        # START_CONTRACT: apply_detection_config
        #   PURPOSE: Apply detection settings; no-op if equal; invalidate detect+downstream if changed
        #   INPUTS: { new_config: DetectionConfig }
        #   OUTPUTS: { bool — True if applied and pipeline invalidated, False if no-op }
        #   SIDE_EFFECTS: mutates detection and pipeline stage statuses when changed
        # END_CONTRACT: apply_detection_config
        if _detection_config_equal(self.detection, new_config):
            return False
        self.detection = DetectionConfig(
            sample_fps=new_config.sample_fps,
            decoder_backend=new_config.decoder_backend,
            slide_roi=new_config.slide_roi,
            ignore_rois=list(new_config.ignore_rois),
            threshold=new_config.threshold,
            min_slide_duration=new_config.min_slide_duration,
            min_stable_duration=new_config.min_stable_duration,
            dedupe_enabled=new_config.dedupe_enabled,
            analysis_max_side=new_config.analysis_max_side,
        )
        # Mark detect itself STALE when it had succeeded (canonical: results obsolete).
        detect_state = self.pipeline.get("detect")
        if detect_state.status == StageStatus.SUCCEEDED:
            detect_state.status = StageStatus.STALE
        self.invalidate_downstream_from("detect")
        return True

    @property
    def slides(self) -> tuple[SlideView, ...]:
        """Read-only immutable view of slides."""
        return tuple(SlideView.from_slide(s) for s in self._slides)

    @property
    def slide_count(self) -> int:
        return len(self._slides)

    def get_slide(self, slide_id: SlideId | str) -> SlideView | None:
        """Find a slide by SlideId or string value. Returns immutable view."""
        target = str(slide_id) if isinstance(slide_id, SlideId) else slide_id
        for slide in self._slides:
            if str(slide.slide_id) == target:
                return SlideView.from_slide(slide)
        return None

    def _require_slide(self, slide_id: SlideId | str) -> Slide:
        """Internal: find mutable Slide entity or raise SlideNotFound."""
        target = str(slide_id) if isinstance(slide_id, SlideId) else slide_id
        for slide in self._slides:
            if str(slide.slide_id) == target:
                return slide
        raise SlideNotFound(f"Slide not found: {slide_id}")

    def add_slide(self, timestamp: float) -> SlideId:
        """Add a manual slide at *timestamp*.

        If the timestamp falls inside an existing slide interval, that slide
        is split: the existing slide's end is moved to *timestamp*, and a new
        slide spans from *timestamp* to the old end.

        Returns the SlideId of the new slide.

        Raises DomainError if no interval is available (timestamp is between
        two adjacent slides with no gap).
        """
        if timestamp < 0:
            raise ValidationError("Slide timestamp must be non-negative")

        containing = None
        for slide in self._slides:
            if slide.interval.contains(timestamp) and not (
                slide.interval.start == timestamp or slide.interval.end == timestamp
            ):
                containing = slide
                break

        if containing is not None:
            old_end = containing.interval.end
            containing.interval = TimeInterval(containing.interval.start, timestamp)
            if not containing.start <= containing.representative_timestamp <= containing.end:
                containing.representative_timestamp = (containing.interval.start + timestamp) / 2
            new_slide = Slide(
                slide_id=SlideId.new(),
                interval=TimeInterval(timestamp, old_end),
                index=0,
                manual=True,
                representative_timestamp=(timestamp + old_end) / 2,
            )
        else:
            next_start = min(
                (s.interval.start for s in self._slides if s.interval.start > timestamp),
                default=timestamp + 5.0,
            )
            if next_start <= timestamp:
                raise DomainError(
                    f"No interval available for manual slide at {timestamp}"
                )
            new_interval = TimeInterval(timestamp, next_start)
            new_slide = Slide(
                slide_id=SlideId.new(),
                interval=new_interval,
                index=0,
                manual=True,
                representative_timestamp=(timestamp + next_start) / 2,
            )
            self._validate_no_overlap(new_slide)

        self._slides.append(new_slide)
        self._reindex()
        self.invalidate_downstream_from("detect")
        return new_slide.slide_id

    def remove_slide(self, slide_id: SlideId | str) -> None:
        """Remove a slide by SlideId. Other SlideIds are preserved."""
        target = self._require_slide(slide_id)
        self._slides.remove(target)
        self._reindex()
        self.invalidate_downstream_from("detect")

    def move_slide(
        self,
        slide_id: SlideId | str,
        start: float,
        end: float,
    ) -> None:
        """Move a slide to a new [start, end] interval.

        Raises OverlappingSlides if the new interval overlaps any other slide.
        Raises ValidationError if start/end are invalid.
        """
        slide = self._require_slide(slide_id)

        new_interval = TimeInterval(start, end)
        self._validate_no_overlap_excluding(new_interval, slide)
        slide.interval = new_interval
        if not start <= slide.representative_timestamp <= end:
            slide.representative_timestamp = (start + end) / 2
        self._reindex()
        self.invalidate_downstream_from("detect")

    def resize_slide(
        self,
        slide_id: SlideId | str,
        end: float,
    ) -> None:
        """Resize a slide by changing its end boundary."""
        slide = self._require_slide(slide_id)
        self.move_slide(slide_id, slide.interval.start, end)

    def clear_image(self, slide_id: SlideId | str) -> None:
        """Clear the representative image for a slide and invalidate exports."""
        slide = self._require_slide(slide_id)
        slide.image = None
        self.pipeline.invalidate_from("notes")

    def set_image(self, slide_id: SlideId | str, image: ArtifactRef) -> None:
        """Assign a portable representative image and invalidate downstream output."""
        if not isinstance(image, ArtifactRef):
            raise TypeError("image must be an ArtifactRef")
        slide = self._require_slide(slide_id)
        slide.image = image
        self.pipeline.invalidate_from("notes")

    def replace_detected_slides(self, slides: Sequence[Slide]) -> None:
        """Replace all detected slides with a new set of domain Slide objects.

        Validates the complete candidate collection before committing.
        All existing slides are removed. Pipeline state is invalidated downstream.
        """
        candidate = list(slides)
        self._validate_candidate_slides(candidate)
        candidate.sort(key=lambda s: (s.interval.start, s.interval.end))
        for i, slide in enumerate(candidate, start=1):
            slide.index = i
        self._slides = candidate
        self.invalidate_downstream_from("detect")

    def invalidate_downstream_from(self, stage: str) -> list[str]:
        """Mark all downstream pipeline stages as stale."""
        return self.pipeline.invalidate_from(stage)

    def to_slides_dict(self) -> list[dict[str, Any]]:
        """Serialize slides to a list of dicts for persistence."""
        return [slide.to_dict() for slide in self._slides]

    # START_CONTRACT: validate
    #   PURPOSE: Check complete aggregate invariants without changing domain or pipeline state.
    #   INPUTS: none
    #   OUTPUTS: { None - returns only when all invariants hold }
    #   SIDE_EFFECTS: none
    #   LINKS: M-DOMAIN-PROJECT, V-REF-PERSISTENCE-STABILIZATION
    # END_CONTRACT: validate
    def validate(self) -> None:
        """Raise ValidationError or a specialized domain error on invalid state."""
        if not self.name or not self.name.strip():
            raise ValidationError("Project name must be non-empty")
        self._validate_candidate_slides(self._slides)
        if len(self.score_timestamps) != len(self.score_values):
            raise ValidationError("Score timestamps and values must have equal lengths")
        if not all(
            math.isfinite(value)
            for value in self.score_timestamps + self.score_values
        ):
            raise ValidationError("Score timestamps and values must be finite")
        if any(value < 0 for value in self.score_timestamps):
            raise ValidationError("Score timestamps must be non-negative")
        if any(
            current < previous
            for previous, current in zip(
                self.score_timestamps,
                self.score_timestamps[1:],
                strict=False,
            )
        ):
            raise ValidationError("Score timestamps must be monotonic")
        if not all(isinstance(ref, ArtifactRef) for ref in self.artifacts.values()):
            raise ValidationError("Project artifacts must be ArtifactRef values")

    @classmethod
    def from_slides_dict(
        cls,
        slides_data: list[dict[str, Any]],
        name: str = "Untitled",
        video_path: str = "",
        subtitle_path: str = "",
        output_dir: str = "",
    ) -> Project:
        """Construct a Project from persisted slide data."""
        project = cls(
            name=name,
            video_path=video_path,
            subtitle_path=subtitle_path,
            output_dir=output_dir,
        )
        for data in slides_data:
            slide = Slide.from_dict(data)
            project._slides.append(slide)
        project._slides.sort(key=lambda s: (s.interval.start, s.interval.end))
        for i, slide in enumerate(project._slides, start=1):
            slide.index = i
        return project

    def _reindex(self) -> None:
        """Sort slides by start time and reassign 1-based indices."""
        self._slides.sort(key=lambda s: (s.interval.start, s.interval.end))
        for i, slide in enumerate(self._slides, start=1):
            slide.index = i

    def _validate_candidate_slides(
        self,
        slides: list[Slide],
        video_duration: float | None = None,
    ) -> None:
        """Validate a complete candidate slide collection before committing.

        Checks uniqueness, sort order, overlap, interval validity,
        representative timestamp placement, and optional video bounds.
        """
        seen_ids: set[str] = set()
        prev_end: float | None = None
        for slide in slides:
            sid = str(slide.slide_id)
            if sid in seen_ids:
                raise DuplicateSlideId(f"Duplicate SlideId: {sid}")
            seen_ids.add(sid)
            if prev_end is not None and slide.interval.start < prev_end:
                raise OverlappingSlides(
                    f"Slide {sid} starts at {slide.interval.start} "
                    f"before previous end {prev_end}"
                )
            prev_end = slide.interval.end
            if video_duration is not None and slide.interval.end > video_duration:
                raise ValidationError(
                    f"Slide {sid} extends beyond video duration {video_duration}"
                )
            if not slide.interval.start <= slide.representative_timestamp <= slide.interval.end:
                raise InvalidRepresentativeTimestamp(
                    f"Slide {sid} representative_timestamp {slide.representative_timestamp} "
                    f"outside [{slide.interval.start}, {slide.interval.end}]"
                )
            if math.isnan(slide.confidence) or not (0.0 <= slide.confidence <= 1.0):
                raise ValidationError(
                    f"Slide {sid} confidence out of range: {slide.confidence}"
                )

    def _validate_no_overlap(self, slide: Slide) -> None:
        """Ensure the slide does not overlap any existing slide."""
        for existing in self._slides:
            if existing is slide:
                continue
            if slide.interval.overlaps(existing.interval):
                raise OverlappingSlides(
                    f"Slide {slide.slide_id} overlaps slide {existing.slide_id}"
                )

    def _validate_no_overlap_excluding(
        self,
        interval: TimeInterval,
        excluded: Slide,
    ) -> None:
        """Ensure *interval* does not overlap any slide except *excluded*."""
        for existing in self._slides:
            if existing is excluded:
                continue
            if interval.overlaps(existing.interval):
                raise OverlappingSlides(
                    f"Interval [{interval.start}, {interval.end}) overlaps "
                    f"slide {existing.slide_id}"
                )
