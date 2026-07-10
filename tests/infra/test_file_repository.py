# FILE: tests/infra/test_file_repository.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit tests for FileProjectRepository — create, load, save, migration, atomicity, revision.
#   SCOPE: Round-trip, legacy migration, UID stability, atomic write, revision conflict, corruption.
#   DEPENDS: pytest, video2pptx.infrastructure.persistence, video2pptx.domain
#   LINKS: V-PORT-REPO
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import json

import pytest

from video2pptx.domain import Project, Slide
from video2pptx.infrastructure.persistence.errors import (
    ProjectAlreadyExists,
    ProjectDocumentCorrupted,
    ProjectNotFound,
    ProjectRevisionConflict,
)
from video2pptx.infrastructure.persistence.file_project_repository import (
    FileProjectRepository,
)


def _make_project_with_slides() -> Project:
    project = Project(name="repo_test", video_path="vid.mp4")
    project.replace_detected_slides([
        Slide.from_dict({"uid": "s1", "start": 0.0, "end": 5.0}),
        Slide.from_dict({"uid": "s2", "start": 5.0, "end": 10.0}),
    ])
    project.score_timestamps = [1.0, 2.0]
    project.score_values = [0.1, 0.2]
    return project


class TestCreateAndLoad:
    def test_create_then_load_round_trip(self, tmp_path):
        repo = FileProjectRepository()
        project = _make_project_with_slides()
        location = tmp_path / "proj"
        repo.create(location, project)

        loaded = repo.load(location)
        assert loaded.name == "repo_test"
        assert loaded.slide_count == 2
        assert loaded.get_slide("s1") is not None
        assert loaded.get_slide("s2") is not None
        assert loaded.score_timestamps == [1.0, 2.0]

    def test_create_rejects_non_empty(self, tmp_path):
        repo = FileProjectRepository()
        location = tmp_path / "proj"
        location.mkdir()
        (location / "other.txt").write_text("x")
        with pytest.raises(ProjectAlreadyExists):
            repo.create(location, _make_project_with_slides())

    def test_load_missing_raises(self, tmp_path):
        repo = FileProjectRepository()
        with pytest.raises(ProjectNotFound):
            repo.load(tmp_path / "nonexistent")


class TestUidStability:
    def test_uids_preserved_across_save_load(self, tmp_path):
        repo = FileProjectRepository()
        project = _make_project_with_slides()
        location = tmp_path / "uid_proj"
        repo.create(location, project)

        loaded = repo.load(location)
        uids_first = [v.slide_id.value for v in loaded.slides]

        repo.save(loaded, location)
        reloaded = repo.load(location)
        uids_second = [v.slide_id.value for v in reloaded.slides]

        assert uids_first == uids_second

    def test_legacy_load_assigns_uids(self, tmp_path):
        location = tmp_path / "legacy_proj"
        location.mkdir()
        legacy_data = {
            "name": "legacy",
            "video": "",
            "subtitles": "",
            "output_dir": str(location),
            "state": {
                "detect_done": True,
                "align_done": False,
                "notes_done": False,
                "llm_done": False,
                "preview_done": False,
                "md_exported": False,
                "pptx_exported": False,
                "auto_done": False,
            },
            "slides_json": "slides.json",
            "slides": [
                {"index": 1, "start": 0.0, "end": 5.0, "duration": 5.0, "representative_timestamp": 2.5},
                {"index": 2, "start": 5.0, "end": 10.0, "duration": 5.0, "representative_timestamp": 7.5},
            ],
            "score_timestamps": [],
            "score_values": [],
        }
        (location / "project.json").write_text(
            json.dumps(legacy_data), encoding="utf-8"
        )

        repo = FileProjectRepository()
        loaded = repo.load(location)
        assert loaded.slide_count == 2
        uids = [v.slide_id.value for v in loaded.slides]
        assert all(uid.strip() for uid in uids)

        repo.save(loaded, location)
        reloaded = repo.load(location)
        uids_after = [v.slide_id.value for v in reloaded.slides]
        assert uids == uids_after


class TestAtomicWrite:
    def test_save_creates_project_and_slides_json(self, tmp_path):
        repo = FileProjectRepository()
        project = _make_project_with_slides()
        location = tmp_path / "atomic"
        repo.create(location, project)
        assert (location / "project.json").is_file()
        assert (location / "slides.json").is_file()

    def test_save_preserves_valid_json(self, tmp_path):
        repo = FileProjectRepository()
        project = _make_project_with_slides()
        location = tmp_path / "crash"
        repo.create(location, project)

        project.add_slide(2.5)
        repo.save(project, location)

        reloaded = repo.load(location)
        assert reloaded.slide_count == 3


class TestRevisionConflict:
    def test_correct_revision_succeeds(self, tmp_path):
        repo = FileProjectRepository()
        project = _make_project_with_slides()
        location = tmp_path / "rev"
        result = repo.save(project, location)
        repo.save(project, location, expected_revision=result.revision)

    def test_stale_revision_raises(self, tmp_path):
        repo = FileProjectRepository()
        project = _make_project_with_slides()
        location = tmp_path / "stale"
        repo.create(location, project)

        with pytest.raises(ProjectRevisionConflict):
            repo.save(project, location, expected_revision="wrong")


class TestCorruption:
    def test_corrupt_json_raises(self, tmp_path):
        location = tmp_path / "corrupt"
        location.mkdir()
        (location / "project.json").write_text("{broken", encoding="utf-8")
        repo = FileProjectRepository()
        with pytest.raises(ProjectDocumentCorrupted):
            repo.load(location)


class TestValidateStorage:
    def test_valid_project(self, tmp_path):
        repo = FileProjectRepository()
        project = _make_project_with_slides()
        location = tmp_path / "valid"
        repo.create(location, project)
        result = repo.validate_storage(location)
        assert result.valid is True

    def test_missing_project(self, tmp_path):
        repo = FileProjectRepository()
        result = repo.validate_storage(tmp_path / "missing")
        assert result.valid is False
