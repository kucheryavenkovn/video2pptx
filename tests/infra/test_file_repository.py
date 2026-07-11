# FILE: tests/infra/test_file_repository.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit tests for FileProjectRepository — create, load, save, migration, atomicity, revision.
#   SCOPE: LoadedProject, V2 round-trip, legacy migration, UID stability, revision conflict, corruption.
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
    ProjectSchemaUnsupported,
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
        assert loaded.project.name == "repo_test"
        assert loaded.project.slide_count == 2
        assert loaded.project.get_slide("s1") is not None
        assert loaded.project.get_slide("s2") is not None
        assert loaded.project.score_timestamps == [1.0, 2.0]
        assert loaded.location == location
        assert loaded.revision

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
        uids_first = [v.slide_id.value for v in loaded.project.slides]

        repo.save(loaded.project, location, expected_revision=loaded.revision)
        reloaded = repo.load(location)
        uids_second = [v.slide_id.value for v in reloaded.project.slides]

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
        assert loaded.project.slide_count == 2
        assert loaded.migrated is True
        uids = [v.slide_id.value for v in loaded.project.slides]
        assert all(uid.strip() for uid in uids)

        repo.save(loaded.project, location, expected_revision=loaded.revision)
        reloaded = repo.load(location)
        uids_after = [v.slide_id.value for v in reloaded.project.slides]
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
        assert reloaded.project.slide_count == 3


class TestCanonicalDocument:
    def test_save_writes_strict_v2_without_output_dir(self, tmp_path):
        repo = FileProjectRepository()
        project = _make_project_with_slides()
        project.pipeline = project.pipeline.from_dict(
            {
                "notes": {
                    "status": "failed",
                    "operation_id": "notes-op",
                    "error": {"message": "failure"},
                },
                "markdown_export": {"status": "stale"},
                "pptx_export": {"status": "skipped"},
            }
        )
        location = tmp_path / "canonical"

        created = repo.create(location, project)
        data = json.loads((location / "project.json").read_text(encoding="utf-8"))

        assert created.revision == data["revision"]
        assert data["schema_version"] == "2.0"
        assert "output_dir" not in data
        assert data["pipeline"]["stages"]["notes"]["status"] == "failed"
        assert data["pipeline"]["stages"]["notes"]["operation_id"] == "notes-op"
        assert data["pipeline"]["stages"]["markdown_export"]["status"] == "stale"
        assert data["pipeline"]["stages"]["pptx_export"]["status"] == "skipped"

    def test_standard_load_edit_save_uses_loaded_revision(self, tmp_path):
        repo = FileProjectRepository()
        location = tmp_path / "cycle"
        repo.create(location, _make_project_with_slides())

        loaded = repo.load(location)
        loaded.project.name = "edited"
        result = repo.save(
            loaded.project,
            loaded.location,
            expected_revision=loaded.revision,
        )
        reloaded = repo.load(location)

        assert result.revision == reloaded.revision
        assert result.revision != loaded.revision
        assert reloaded.project.name == "edited"


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

    def test_corrupt_existing_document_is_not_overwritten(self, tmp_path):
        repo = FileProjectRepository()
        project = _make_project_with_slides()
        location = tmp_path / "corrupt-save"
        location.mkdir()
        project_json = location / "project.json"
        project_json.write_text("{broken", encoding="utf-8")

        with pytest.raises(ProjectDocumentCorrupted):
            repo.save(project, location, expected_revision="expected")

        assert project_json.read_text(encoding="utf-8") == "{broken"


class TestCorruption:
    def test_corrupt_json_raises(self, tmp_path):
        location = tmp_path / "corrupt"
        location.mkdir()
        (location / "project.json").write_text("{broken", encoding="utf-8")
        repo = FileProjectRepository()
        with pytest.raises(ProjectDocumentCorrupted):
            repo.load(location)

    def test_unsupported_schema_raises_specific_error(self, tmp_path):
        location = tmp_path / "unsupported"
        location.mkdir()
        (location / "project.json").write_text(
            json.dumps({"schema_version": "99.0"}),
            encoding="utf-8",
        )

        with pytest.raises(ProjectSchemaUnsupported):
            FileProjectRepository().load(location)


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
