# FILE: tests/test_gui_marker_manager.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for M-GUI-MARKER-MANAGER — add, delete, get, resnap markers
#   SCOPE: Deterministic tests for marker CRUD with mocked smart snap
#   DEPENDS: pytest, pathlib
#   LINKS: M-GUI-MARKER-MANAGER
#   ROLE: TEST
#   MAP_MODE: NONE
# END_MODULE_CONTRACT

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from video2pptx.gui.marker_manager import (
    add_marker,
    delete_marker,
    get_markers,
)
from video2pptx.project_manager import Project, save_project


@pytest.fixture
def project(tmp_path: Path) -> Project:
    proj = Project(
        name="test",
        video=str(tmp_path / "test.mp4"),
        output_dir=str(tmp_path),
    )
    save_project(proj, tmp_path)
    return proj


class TestAddMarker:
    # START_CONTRACT: TestAddMarker
    #   PURPOSE: Verify marker creation and persistence
    #   LINKS: M-GUI-MARKER-MANAGER
    # END_CONTRACT: TestAddMarker

    def test_adds_marker_with_snapped_timestamp(self, project: Project) -> None:
        with patch("video2pptx.gui.marker_manager.smart_snap", return_value=11.0):
            entry = add_marker(project, 12.0, snap_mode="diff_only")

        assert entry["original_ts"] == 12.0
        assert entry["snapped_ts"] == 11.0
        assert entry["snap_mode"] == "diff_only"

    def test_marker_appended_to_project(self, project: Project) -> None:
        with patch("video2pptx.gui.marker_manager.smart_snap", return_value=15.0):
            add_marker(project, 14.0)

        assert len(project.markers) == 1
        assert project.markers[0]["original_ts"] == 14.0
        assert project.markers[0]["snapped_ts"] == 15.0

    def test_multiple_markers(self, project: Project) -> None:
        with patch("video2pptx.gui.marker_manager.smart_snap") as mock_snap:
            mock_snap.side_effect = [5.0, 15.0, 25.0]
            add_marker(project, 4.0)
            add_marker(project, 14.0)
            add_marker(project, 24.0)

        assert len(project.markers) == 3


class TestGetMarkers:
    # START_CONTRACT: TestGetMarkers
    #   PURPOSE: Verify marker retrieval
    #   LINKS: M-GUI-MARKER-MANAGER
    # END_CONTRACT: TestGetMarkers

    def test_returns_list_of_marker_dicts(self, project: Project) -> None:
        with patch("video2pptx.gui.marker_manager.smart_snap", return_value=11.0):
            add_marker(project, 12.0)

        markers = get_markers(project)
        assert len(markers) == 1
        assert markers[0]["original_ts"] == 12.0
        assert markers[0]["snapped_ts"] == 11.0

    def test_empty_if_no_markers(self, project: Project) -> None:
        markers = get_markers(project)
        assert markers == []


class TestDeleteMarker:
    # START_CONTRACT: TestDeleteMarker
    #   PURPOSE: Verify marker deletion
    #   LINKS: M-GUI-MARKER-MANAGER
    # END_CONTRACT: TestDeleteMarker

    def test_deletes_existing_marker(self, project: Project) -> None:
        with patch("video2pptx.gui.marker_manager.smart_snap", return_value=11.0):
            add_marker(project, 12.0)
            add_marker(project, 20.0)

        assert len(project.markers) == 2

        result = delete_marker(project, 12.0)
        assert result is True
        assert len(project.markers) == 1
        assert project.markers[0]["original_ts"] == 20.0

    def test_returns_false_if_not_found(self, project: Project) -> None:
        result = delete_marker(project, 99.0)
        assert result is False

    def test_persists_after_delete(self, project: Project, tmp_path: Path) -> None:
        with patch("video2pptx.gui.marker_manager.smart_snap", return_value=11.0):
            add_marker(project, 12.0)
            add_marker(project, 20.0)

        delete_marker(project, 12.0)

        # Reload from file
        loaded = Project.model_validate_json(
            (tmp_path / "project.json").read_text(encoding="utf-8")
        )
        assert len(loaded.markers) == 1
        assert loaded.markers[0]["original_ts"] == 20.0


class TestResnapMarker:
    # START_CONTRACT: TestResnapMarker
    #   PURPOSE: Verify marker re-snapping
    #   LINKS: M-GUI-MARKER-MANAGER
    # END_CONTRACT: TestResnapMarker

    def test_resnap_updates_timestamp(self, project: Project) -> None:
        from video2pptx.gui.marker_manager import resnap_marker

        with patch("video2pptx.gui.marker_manager.smart_snap") as mock_snap:
            mock_snap.return_value = 11.0
            add_marker(project, 12.0)

            mock_snap.return_value = 10.5
            updated = resnap_marker(project, 12.0, snap_mode="hybrid")

        assert updated is not None
        assert updated["snapped_ts"] == 10.5
        assert updated["snap_mode"] == "hybrid"

    def test_resnap_nonexistent_returns_none(self, project: Project) -> None:
        from video2pptx.gui.marker_manager import resnap_marker

        result = resnap_marker(project, 99.0)
        assert result is None
