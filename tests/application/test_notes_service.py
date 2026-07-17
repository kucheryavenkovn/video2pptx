# FILE: tests/application/test_notes_service.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Verify NotesService basic mode, LLM failure, raw cue preservation, and cancellation.
#   SCOPE: Basic mode, adapter failure, cancellation, no subtitles, raw cues preserved.
#   DEPENDS: pytest, video2pptx.application, video2pptx.domain
#   LINKS: M-APP-NOTES, V-M-APP-NOTES
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Add notes service tests with fake processor
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path

import pytest

from video2pptx.application.base import ServiceContext
from video2pptx.application.cancellation import CancellationToken
from video2pptx.application.errors import StageFailureError
from video2pptx.application.ports.notes_processor import NotesOutput
from video2pptx.application.services.notes_service import NotesService
from video2pptx.domain import Project, Slide, StageStatus
from video2pptx.infrastructure.persistence.file_project_repository import FileProjectRepository


class FakeProcessor:
    def __init__(self, output: NotesOutput | None = None, error: Exception | None = None):
        self._output = output or NotesOutput(
            notes_by_uid={"s1": "cleaned notes", "s2": "other notes"},
            llm_descriptions_by_uid={"s1": None, "s2": None},
            raw_cues_preserved=True,
        )
        self._error = error

    def process(self, slides_data, subtitles_path, *, mode="basic"):
        if self._error:
            raise self._error
        return self._output


def _make_project(tmp_path, subtitle_path="subs.srt") -> tuple[FileProjectRepository, Path]:
    repo = FileProjectRepository()
    project = Project(name="notes-test", video_path="vid.mp4", subtitle_path=subtitle_path)
    project.replace_detected_slides([
        Slide.from_dict({"uid": "s1", "start": 0.0, "end": 5.0, "transcript": "raw"}),
        Slide.from_dict({"uid": "s2", "start": 5.0, "end": 10.0, "transcript": "raw2"}),
    ])
    project.pipeline.start("detect")
    project.pipeline.succeed("detect")
    location = tmp_path / "proj"
    repo.create(location, project)
    return repo, location


class TestNotesService:
    def test_basic_mode_enriches_transcript(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        service = NotesService(FakeProcessor(), ctx)

        result = service.execute(location, mode="basic")

        assert result.success is True
        assert result.data["mode"] == "basic"

        loaded = repo.load(location)
        assert loaded.project.get_slide("s1").notes == "cleaned notes"
        assert loaded.project.pipeline.status("notes") is StageStatus.SUCCEEDED

    def test_llm_failure_raises_stage_failure(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        processor = FakeProcessor(error=RuntimeError("LLM gateway unavailable"))
        service = NotesService(processor, ctx)

        with pytest.raises(StageFailureError, match="LLM gateway"):
            service.execute(location, mode="llm")

        loaded = repo.load(location)
        assert loaded.project.get_slide("s1").notes == ""

    def test_raw_cues_preserved(self, tmp_path):
        repo, location = _make_project(tmp_path)
        ctx = ServiceContext(repository=repo)
        service = NotesService(FakeProcessor(), ctx)

        result = service.execute(location)

        assert result.data["raw_cues_preserved"] is True
        loaded = repo.load(location)
        assert loaded.project.get_slide("s1").transcript == "raw"

    def test_no_subtitles_returns_failure(self, tmp_path):
        repo, location = _make_project(tmp_path, subtitle_path="")
        ctx = ServiceContext(repository=repo)
        service = NotesService(FakeProcessor(), ctx)

        result = service.execute(location)

        assert result.success is False
        assert "Subtitles" in result.error

    def test_cancellation_before_processing(self, tmp_path):
        repo, location = _make_project(tmp_path)
        token = CancellationToken()
        token.trigger()
        ctx = ServiceContext(repository=repo, cancellation=token)
        service = NotesService(FakeProcessor(), ctx)

        with pytest.raises(StageFailureError, match="cancel"):
            service.execute(location)

        loaded = repo.load(location)
        assert loaded.project.get_slide("s1").notes == ""
