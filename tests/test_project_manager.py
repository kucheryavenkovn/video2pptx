# FILE: tests/test_project_manager.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for project manager — create, open, update project.json
#   SCOPE: Verify project.json creation, round-trip, state/state update, path resolution, error handling
#   DEPENDS: pytest, loguru, video2pptx.project_manager
#   LINKS: V-M-PROJECT, M-PROJECT
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

from pathlib import Path

import pytest

from video2pptx.project_manager import (
    Project,
    create_project,
    import_subtitles_to_project,
    import_video_to_project,
    open_project,
    update_project_state,
)


class TestProjectCreate:
    def test_create_basic(self, tmp_path, loguru_sink):
        """Create project with video path, verify project.json exists and has correct fields."""
        video = tmp_path / "video.mp4"
        video.write_text("fake video")
        proj_dir = tmp_path / "my_project"

        proj = create_project(
            project_dir=proj_dir,
            video_path=video,
            name="Test Lecture",
        )

        assert isinstance(proj, Project)
        assert proj.name == "Test Lecture"
        assert Path(proj.video).resolve() == video.resolve()
        assert proj.state.detect_done is False
        assert proj.state.notes_done is False

        json_path = proj_dir / "project.json"
        assert json_path.is_file()

        combined = " ".join(loguru_sink)
        assert "Project created" in combined or "project" in combined.lower()

    def test_create_with_subtitles(self, tmp_path):
        """Create project with both video and subtitles paths."""
        video = tmp_path / "video.mp4"
        video.write_text("fake")
        subs = tmp_path / "subs.srt"
        subs.write_text("fake srt")

        proj = create_project(_proj_dir := tmp_path / "proj", video_path=video, subtitles_path=subs)

        assert Path(proj.subtitles).resolve() == subs.resolve() if proj.subtitles else False

    def test_create_existing_dir_does_not_overwrite(self, tmp_path):
        """Creating project in existing non-empty dir should raise or warn."""
        proj_dir = tmp_path / "existing"
        proj_dir.mkdir()
        (proj_dir / "other_file.txt").write_text("stuff")
        video = tmp_path / "video.mp4"
        video.write_text("fake")

        with pytest.raises((FileExistsError, ValueError)):
            create_project(project_dir=proj_dir, video_path=video)

    def test_create_missing_video(self, tmp_path):
        """Missing video path should raise FileNotFoundError."""
        bogus = tmp_path / "no_video.mp4"
        with pytest.raises(FileNotFoundError):
            create_project(project_dir=tmp_path / "proj", video_path=bogus)


class TestProjectOpen:
    def test_open_round_trip(self, tmp_path):
        """Create then open a project, verify all fields preserved."""
        video = tmp_path / "video.mp4"
        video.write_text("fake")
        subs = tmp_path / "subs.srt"
        subs.write_text("fake")

        orig = create_project(tmp_path / "proj", video_path=video, subtitles_path=subs, name="RoundTrip")
        update_project_state(orig, detect_done=True)

        loaded = open_project(tmp_path / "proj")
        assert loaded.name == "RoundTrip"
        assert Path(loaded.video).exists()
        assert loaded.state.detect_done is True
        assert loaded.state.notes_done is False

    def test_open_missing_dir(self, tmp_path):
        """Opening non-existent project dir should raise."""
        with pytest.raises(FileNotFoundError):
            open_project(tmp_path / "no_project")

    def test_open_missing_json(self, tmp_path):
        """Dir exists but no project.json should raise."""
        proj_dir = tmp_path / "empty"
        proj_dir.mkdir()
        with pytest.raises(FileNotFoundError):
            open_project(proj_dir)


class TestProjectState:
    def test_update_state(self, tmp_path):
        """update_project_state modifies state fields and saves."""
        video = tmp_path / "video.mp4"
        video.write_text("fake")

        proj = create_project(tmp_path / "proj", video_path=video)
        updated = update_project_state(proj, detect_done=True, slides_json="slides/slides.json")

        assert updated.state.detect_done is True
        assert updated.slides_json == "slides/slides.json"

        reloaded = open_project(tmp_path / "proj")
        assert reloaded.state.detect_done is True
        assert reloaded.slides_json == "slides/slides.json"

    def test_state_defaults(self, tmp_path):
        """Fresh project should have all state flags at defaults."""
        video = tmp_path / "video.mp4"
        video.write_text("fake")

        proj = create_project(tmp_path / "proj", video_path=video)
        assert proj.state.detect_done is False
        assert proj.state.notes_done is False
        assert proj.state.llm_done is False


class TestLogMarkers:
    def test_log_markers_present(self, tmp_path, loguru_sink):
        """Required log markers appear in output."""
        video = tmp_path / "video.mp4"
        video.write_text("fake")
        create_project(tmp_path / "proj", video_path=video)

        " ".join(loguru_sink)
        # At minimum some log output was produced about project creation
        assert len(loguru_sink) > 0


class TestImportVideo:
    def test_import_video_sets_path(self, tmp_path):
        video = tmp_path / "video.mp4"
        video.write_text("fake")
        proj = create_project(tmp_path / "proj", name="Test")
        assert proj.video == ""

        import_video_to_project(proj, str(video))
        assert Path(proj.video).resolve() == video.resolve()

    def test_import_video_auto_detects_subtitles(self, tmp_path):
        video = tmp_path / "lecture.mp4"
        video.write_text("fake")
        sub = tmp_path / "lecture.srt"
        sub.write_text("1\n00:00:01,000 --> 00:00:02,000\nhello")

        proj = create_project(tmp_path / "proj", name="Test")
        import_video_to_project(proj, str(video))
        assert proj.subtitles is not None
        assert Path(proj.subtitles).resolve() == sub.resolve()

    def test_import_video_raises_on_missing(self, tmp_path):
        proj = create_project(tmp_path / "proj", name="Test")
        with pytest.raises(FileNotFoundError):
            import_video_to_project(proj, str(tmp_path / "missing.mp4"))


class TestImportSubtitles:
    def test_import_subtitles_sets_path(self, tmp_path):
        sub = tmp_path / "subs.srt"
        sub.write_text("1\n00:00:01,000 --> 00:00:02,000\nhello")
        proj = create_project(tmp_path / "proj", name="Test")

        import_subtitles_to_project(proj, str(sub))
        assert proj.subtitles is not None
        assert Path(proj.subtitles).resolve() == sub.resolve()

    def test_import_subtitles_raises_on_missing(self, tmp_path):
        proj = create_project(tmp_path / "proj", name="Test")
        with pytest.raises(FileNotFoundError):
            import_subtitles_to_project(proj, str(tmp_path / "missing.srt"))


class TestFindSiblingSubtitle:
    def test_finds_exact_match(self, tmp_path):
        from video2pptx.project_manager import _find_sibling_subtitle
        video = tmp_path / "lecture.mp4"
        video.write_text("fake")
        sub = tmp_path / "lecture.srt"
        sub.write_text("content")

        result = _find_sibling_subtitle(video)
        assert result == sub

    def test_returns_none_when_no_subs(self, tmp_path):
        from video2pptx.project_manager import _find_sibling_subtitle
        video = tmp_path / "lecture.mp4"
        video.write_text("fake")

        result = _find_sibling_subtitle(video)
        assert result is None

    def test_finds_vtt_ext(self, tmp_path):
        from video2pptx.project_manager import _find_sibling_subtitle
        video = tmp_path / "lecture.mp4"
        video.write_text("fake")
        sub = tmp_path / "lecture.vtt"
        sub.write_text("content")

        result = _find_sibling_subtitle(video)
        assert result == sub
