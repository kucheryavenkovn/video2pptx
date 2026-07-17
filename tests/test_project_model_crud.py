# FILE: tests/test_project_model_crud.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Verify persisted UID-based ProjectModel slide CRUD invariants.
#   SCOPE: Add/split, resize, move, clear image, delete, disk and timeline synchronization.
#   DEPENDS: pytest-qt, M-PROJECT-MODEL, M-MODELS, M-PROJECT
#   LINKS: V-M-REF-CHAR-TESTS, E2E-011
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

from video2pptx.models import SlidesDocument, SlideSegment, VideoInfo
from video2pptx.project_manager import create_project, save_project
from video2pptx.project_model import ProjectModel


def _create_detected_project(tmp_path):
    project = create_project(tmp_path, name="crud")
    slides = [
        SlideSegment(
            index=1,
            start=0,
            end=5,
            duration=5,
            representative_timestamp=2.5,
            image="slides/slide_001.png",
        ),
        SlideSegment(
            index=2,
            start=5,
            end=10,
            duration=5,
            representative_timestamp=7.5,
            image="slides/slide_002.png",
        ),
    ]
    document = SlidesDocument(
        video=VideoInfo(
            path="fixture.mp4",
            duration=10,
            width=640,
            height=480,
            fps=30,
        ),
        slides=slides,
    )
    (tmp_path / "slides.json").write_text(
        document.model_dump_json(indent=2),
        encoding="utf-8",
    )
    project.slides_json = "slides.json"
    project.slides = slides
    project.state.detect_done = True
    project.state.detect_stale = False
    save_project(project)


def _load_document(tmp_path):
    return SlidesDocument.model_validate_json(
        (tmp_path / "slides.json").read_text(encoding="utf-8")
    )


def test_uid_survives_add_resize_move_and_reopen(qapp, tmp_path):
    _create_detected_project(tmp_path)
    model = ProjectModel()
    model.open(str(tmp_path))

    uid = model.add_slide(2.5)
    assert len(model.project_data.slides) == 3
    assert model.project_data.slides[1].uid == uid

    model.resize_slide(1, 2.0)
    model.move_slide(uid, 2.0, 5.0)
    model.clear_slide_image(uid)

    persisted = _load_document(tmp_path)
    edited = next(slide for slide in persisted.slides if slide.uid == uid)
    assert (edited.start, edited.end, edited.duration) == (2.0, 5.0, 3.0)
    assert edited.image == ""
    assert [slide.index for slide in persisted.slides] == [1, 2, 3]

    reopened = ProjectModel()
    reopened.open(str(tmp_path))
    timeline_uids = [clip.uid for clip in reopened.timeline.track("slides").clips()]
    assert uid in timeline_uids
    assert any(slide.uid == uid for slide in reopened.project_data.slides)


def test_delete_by_uid_reindexes_project_timeline_and_disk(qapp, tmp_path):
    _create_detected_project(tmp_path)
    model = ProjectModel()
    model.open(str(tmp_path))
    deleted_uid = model.project_data.slides[0].uid

    model.delete_slide(deleted_uid)

    assert len(model.project_data.slides) == 1
    assert model.project_data.slides[0].index == 1
    assert model.timeline.track("slides").clips()[0].index == 1
    persisted = _load_document(tmp_path)
    assert [slide.uid for slide in persisted.slides] == [
        model.project_data.slides[0].uid
    ]
