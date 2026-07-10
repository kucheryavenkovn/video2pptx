# FILE: tests/test_project_model.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit tests for ProjectModel
#   SCOPE: Lifecycle, slide CRUD, timeline sync, signal emission
#   DEPENDS: video2pptx.project_model, video2pptx.timeline_model, pytest
#   LINKS: V-M-PROJECT-MODEL
# END_MODULE_CONTRACT

from __future__ import annotations

from video2pptx.project_model import ProjectModel
from video2pptx.timeline_model import Timeline


class TestProjectModel:
    def test_initial_state(self) -> None:
        model = ProjectModel()
        assert not model.is_open
        assert model.timeline is not None
        assert isinstance(model.timeline, Timeline)

    def test_add_slide(self) -> None:
        model = ProjectModel()
        model.add_slide(10.0)
        slides = model.slides
        assert len(slides) == 1
        assert slides[0].start_sec == 10.0
        assert slides[0].manual is True

    def test_delete_slide(self) -> None:
        model = ProjectModel()
        model.add_slide(0.0)
        model.add_slide(10.0)
        assert len(model.slides) == 2
        model.delete_slide(1)
        assert len(model.slides) == 1
        assert model.slides[0].index == 1

    def test_move_slide(self) -> None:
        model = ProjectModel()
        model.add_slide(0.0)
        model.move_slide(1, 5.0, 15.0)
        assert model.slides[0].start_sec == 5.0
        assert model.slides[0].end_sec == 15.0

    def test_close_clears_all(self) -> None:
        model = ProjectModel()
        model.add_slide(0.0)
        model.close()
        assert not model.is_open
        assert len(model.slides) == 0

    def test_set_scores(self) -> None:
        model = ProjectModel()
        model.set_scores([0.0, 1.0, 2.0], [0.1, 0.5, 0.3])
        assert model.score_timestamps == [0.0, 1.0, 2.0]
        assert model.score_values == [0.1, 0.5, 0.3]
        st = model.timeline.track("scores")
        assert st is not None
        assert len(st.clips()) == 3
