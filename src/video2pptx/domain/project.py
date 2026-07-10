# FILE: src/video2pptx/domain/project.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Project aggregate root — owns slides, enforces invariants, manages pipeline state.
#   SCOPE: add_slide, remove_slide, move_slide, resize_slide, replace_detected_slides,
#          invalidate_downstream_from, clear_image, to_slides_dict, from_slides_dict
#   DEPENDS: video2pptx.domain.slide, video2pptx.domain.identifiers, video2pptx.domain.time,
#            video2pptx.domain.pipeline_state, video2pptx.domain.errors
#   LINKS: M-DOMAIN-PROJECT
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   Project - aggregate root controlling slide lifecycle and pipeline state
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Initial Project aggregate root
# END_CHANGE_SUMMARY

from __future__ import annotations

from typing import Any

from video2pptx.domain.errors import DomainError, ValidationError
from video2pptx.domain.identifiers import SlideId
from video2pptx.domain.pipeline_state import PipelineState
from video2pptx.domain.slide import Slide
from video2pptx.domain.time import TimeInterval


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
    ) -> None:
        self.name: str = name
        self.video_path: str = video_path
        self.subtitle_path: str = subtitle_path
        self.output_dir: str = output_dir
        self._slides: list[Slide] = []
        self.pipeline: PipelineState = PipelineState()
        self.score_timestamps: list[float] = []
        self.score_values: list[float] = []

    @property
    def slides(self) -> tuple[Slide, ...]:
        """Read-only view of slides."""
        return tuple(self._slides)

    @property
    def slide_count(self) -> int:
        return len(self._slides)

    def get_slide(self, slide_id: SlideId | str) -> Slide | None:
        """Find a slide by SlideId or string value."""
        target = str(slide_id) if isinstance(slide_id, SlideId) else slide_id
        for slide in self._slides:
            if str(slide.slide_id) == target:
                return slide
        return None

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
        target = self.get_slide(slide_id)
        if target is None:
            raise DomainError(f"Slide not found: {slide_id}")
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

        Raises DomainError if the new interval overlaps any other slide.
        Raises ValidationError if start/end are invalid.
        """
        slide = self.get_slide(slide_id)
        if slide is None:
            raise DomainError(f"Slide not found: {slide_id}")

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
        slide = self.get_slide(slide_id)
        if slide is None:
            raise DomainError(f"Slide not found: {slide_id}")
        self.move_slide(slide_id, slide.interval.start, end)

    def clear_image(self, slide_id: SlideId | str) -> None:
        """Clear the representative image for a slide."""
        slide = self.get_slide(slide_id)
        if slide is None:
            raise DomainError(f"Slide not found: {slide_id}")
        slide.image = None

    def replace_detected_slides(self, slides_data: list[dict[str, Any]]) -> None:
        """Replace all detected slides with a new set.

        All existing slides are removed. Pipeline state is invalidated downstream.
        """
        new_slides: list[Slide] = []
        for data in slides_data:
            slide = Slide.from_dict(data)
            new_slides.append(slide)

        new_slides.sort(key=lambda s: (s.interval.start, s.interval.end))
        for i, slide in enumerate(new_slides, start=1):
            slide.index = i

        self._slides = new_slides
        self.invalidate_downstream_from("detect")

    def invalidate_downstream_from(self, stage: str) -> list[str]:
        """Mark all downstream pipeline stages as stale."""
        return self.pipeline.invalidate_from(stage)

    def to_slides_dict(self) -> list[dict[str, Any]]:
        """Serialize slides to a list of dicts for persistence."""
        return [slide.to_dict() for slide in self._slides]

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

    def _validate_no_overlap(self, slide: Slide) -> None:
        """Ensure the slide does not overlap any existing slide."""
        for existing in self._slides:
            if existing is slide:
                continue
            if slide.interval.overlaps(existing.interval):
                raise DomainError(
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
                raise DomainError(
                    f"Interval [{interval.start}, {interval.end}) overlaps "
                    f"slide {existing.slide_id}"
                )
