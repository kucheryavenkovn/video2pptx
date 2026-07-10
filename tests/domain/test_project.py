# FILE: tests/domain/test_project.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit tests for the Project aggregate root.
#   SCOPE: add_slide, remove_slide, move_slide, replace_detected_slides, invalidate_downstream.
#   DEPENDS: pytest, video2pptx.domain
#   LINKS: V-DOMAIN-PROJECT
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import pytest

from video2pptx.domain import (
    OverlappingSlides,
    Project,
    Slide,
    SlideId,
    SlideView,
    StageStatus,
    ValidationError,
)


def _make_slides_for_project() -> list[Slide]:
    """Create two non-overlapping slides: [0,5) and [5,10)."""
    return [
        Slide.from_dict({"uid": "aaa111", "start": 0.0, "end": 5.0, "index": 1, "image": "slides/slide_001.png"}),
        Slide.from_dict({"uid": "bbb222", "start": 5.0, "end": 10.0, "index": 2, "image": "slides/slide_002.png"}),
    ]


def _make_project_with_two_slides() -> Project:
    """Create a project with two non-overlapping slides: [0,5) and [5,10)."""
    project = Project(name="test", video_path="vid.mp4")
    project.replace_detected_slides(_make_slides_for_project())
    return project


class TestAddSlide:
    def test_returns_stable_slide_id(self):
        project = _make_project_with_two_slides()
        sid = project.add_slide(2.5)
        assert isinstance(sid, SlideId)
        assert project.get_slide(sid) is not None
        assert isinstance(project.get_slide(sid), SlideView)

    def test_split_containing_slide(self):
        project = _make_project_with_two_slides()
        sid = project.add_slide(2.5)
        slide = project.get_slide(sid)
        assert slide is not None
        assert slide.start == 2.5
        assert slide.end == 5.0
        assert slide.manual is True
        original = project.get_slide("aaa111")
        assert original is not None
        assert original.end == 2.5

    def test_correct_index_after_add(self):
        project = _make_project_with_two_slides()
        project.add_slide(2.5)
        indices = [s.index for s in project.slides]
        assert indices == [1, 2, 3]

    def test_add_in_gap(self):
        project = Project()
        project.replace_detected_slides([
            Slide.from_dict({"uid": "x", "start": 0.0, "end": 3.0, "index": 1}),
            Slide.from_dict({"uid": "y", "start": 7.0, "end": 10.0, "index": 2}),
        ])
        sid = project.add_slide(4.0)
        slide = project.get_slide(sid)
        assert slide is not None
        assert slide.start == 4.0
        assert slide.end == 7.0

    def test_negative_timestamp_rejected(self):
        project = _make_project_with_two_slides()
        with pytest.raises(ValidationError):
            project.add_slide(-1.0)


class TestRemoveSlide:
    def test_remove_preserves_other_ids(self):
        project = _make_project_with_two_slides()
        project.remove_slide("aaa111")
        assert project.get_slide("aaa111") is None
        assert project.get_slide("bbb222") is not None

    def test_indices_recalculated(self):
        project = _make_project_with_two_slides()
        project.remove_slide("aaa111")
        remaining = project.slides
        assert len(remaining) == 1
        assert remaining[0].index == 1

    def test_remove_nonexistent_raises(self):
        project = _make_project_with_two_slides()
        from video2pptx.domain.errors import SlideNotFound
        with pytest.raises(SlideNotFound, match="not found"):
            project.remove_slide("nonexistent")


class TestMoveSlide:
    def test_move_to_valid_interval(self):
        project = _make_project_with_two_slides()
        project.move_slide("aaa111", 0.0, 3.0)
        slide = project.get_slide("aaa111")
        assert slide.start == 0.0
        assert slide.end == 3.0

    def test_move_overlap_prevented(self):
        project = _make_project_with_two_slides()
        with pytest.raises(OverlappingSlides, match="overlap"):
            project.move_slide("aaa111", 4.0, 7.0)

    def test_move_nonexistent_raises(self):
        project = _make_project_with_two_slides()
        from video2pptx.domain.errors import SlideNotFound
        with pytest.raises(SlideNotFound, match="not found"):
            project.move_slide("nope", 0.0, 1.0)


class TestReplaceDetectedSlides:
    def test_replaces_all(self):
        project = _make_project_with_two_slides()
        project.replace_detected_slides([
            Slide.from_dict({"uid": "new1", "start": 0.0, "end": 6.0, "index": 1}),
            Slide.from_dict({"uid": "new2", "start": 6.0, "end": 12.0, "index": 2}),
            Slide.from_dict({"uid": "new3", "start": 12.0, "end": 18.0, "index": 3}),
        ])
        assert project.slide_count == 3
        assert project.get_slide("new3") is not None

    def test_invalidates_downstream(self):
        project = _make_project_with_two_slides()
        project.pipeline.start("detect")
        project.pipeline.succeed("detect")
        project.pipeline.start("align")
        project.pipeline.succeed("align")
        project.replace_detected_slides([
            Slide.from_dict({"uid": "z", "start": 0.0, "end": 10.0, "index": 1}),
        ])
        assert project.pipeline.status("align") == StageStatus.STALE


class TestInvalidateDownstream:
    def test_detect_invalidates_all_downstream(self):
        project = _make_project_with_two_slides()
        for stage in ("detect", "align", "notes", "markdown_export", "pptx_export"):
            project.pipeline.start(stage)
            project.pipeline.succeed(stage)
        invalidated = project.invalidate_downstream_from("detect")
        assert "align" in invalidated
        assert "notes" in invalidated
        assert "markdown_export" in invalidated
        assert "pptx_export" in invalidated

    def test_align_does_not_invalidate_detect(self):
        project = _make_project_with_two_slides()
        project.pipeline.start("detect")
        project.pipeline.succeed("detect")
        project.pipeline.start("align")
        project.pipeline.succeed("align")
        project.invalidate_downstream_from("align")
        assert project.pipeline.status("detect") == StageStatus.SUCCEEDED


class TestSerialization:
    def test_round_trip(self):
        project = _make_project_with_two_slides()
        data = project.to_slides_dict()
        restored = Project.from_slides_dict(
            data,
            name=project.name,
            video_path=project.video_path,
        )
        assert restored.slide_count == project.slide_count
        for orig, rest in zip(project.slides, restored.slides, strict=False):
            assert orig.slide_id == rest.slide_id
            assert orig.start == rest.start
            assert orig.end == rest.end


class TestSlideViewImmutability:
    def test_slides_returns_slideview(self):
        project = _make_project_with_two_slides()
        for view in project.slides:
            assert isinstance(view, SlideView)

    def test_get_slide_returns_slideview(self):
        project = _make_project_with_two_slides()
        view = project.get_slide("aaa111")
        assert isinstance(view, SlideView)
        assert view.slide_id.value == "aaa111"

    def test_slideview_is_frozen(self):
        project = _make_project_with_two_slides()
        view = project.get_slide("aaa111")
        with pytest.raises(Exception):
            view.transcript = "hacked"


class TestClearImageInvalidatesExports:
    def test_clear_image_invalidates_markdown_pptx_auto(self):
        project = _make_project_with_two_slides()
        for stage in ("notes", "markdown_export", "pptx_export"):
            project.pipeline.start(stage)
            project.pipeline.succeed(stage)
        project.clear_image("aaa111")
        assert project.pipeline.status("markdown_export") == StageStatus.STALE
        assert project.pipeline.status("pptx_export") == StageStatus.STALE


class TestCandidateValidation:
    def test_duplicate_slideid_rejected(self):
        from video2pptx.domain.errors import DuplicateSlideId
        project = Project()
        with pytest.raises(DuplicateSlideId):
            project.replace_detected_slides([
                Slide.from_dict({"uid": "dup", "start": 0.0, "end": 5.0, "index": 1}),
                Slide.from_dict({"uid": "dup", "start": 5.0, "end": 10.0, "index": 2}),
            ])

    def test_overlap_in_candidates_rejected(self):
        from video2pptx.domain.errors import OverlappingSlides
        project = Project()
        with pytest.raises(OverlappingSlides):
            project.replace_detected_slides([
                Slide.from_dict({"uid": "a", "start": 0.0, "end": 6.0, "index": 1}),
                Slide.from_dict({"uid": "b", "start": 5.0, "end": 10.0, "index": 2}),
            ])


class TestOverlapRejection:
    def test_move_into_occupied_interval_raises(self):
        project = _make_project_with_two_slides()
        with pytest.raises(OverlappingSlides, match="overlap"):
            project.move_slide("bbb222", 3.0, 8.0)
