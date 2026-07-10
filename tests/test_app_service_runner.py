# FILE: tests/test_app_service_runner.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Regression tests for MCP AppServiceRunner command mapping, path normalization, failure propagation, and persistence bridge.
#   SCOPE: quick_preview alias, detect persistence, false result handling.
#   DEPENDS: pytest, M-MCP-OPERATIONS, M-APP-SERVICE, M-PROJECT
#   LINKS: V-REF-CHAR-TESTS, E2E-006, E2E-007
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

from video2pptx.debug.mcp_operations import AppServiceRunner
from video2pptx.project_manager import create_project, open_project


class _Model:
    def __init__(self, project, project_path):
        self.project_data = project
        self.project_path = str(project_path)


def test_persist_detect_result_loads_slides_and_marks_state(tmp_path):
    project = create_project(tmp_path, name="characterized")
    slides_json = tmp_path / "slides.json"
    slides_json.write_text(
        """{
          "schema_version": "1.0",
          "video": {"path": "fixture.mp4", "duration": 10, "fps": 1, "width": 1, "height": 1, "frame_count": 10},
          "slides": [{"index": 1, "start": 0, "end": 10, "duration": 10, "representative_timestamp": 5}]
        }""",
        encoding="utf-8",
    )

    AppServiceRunner._persist_project_result(
        tmp_path,
        "detect",
        {"success": True},
    )

    persisted = open_project(tmp_path)
    assert persisted.slides_json == "slides.json"
    assert len(persisted.slides) == 1
    assert persisted.state.detect_done is True
    assert persisted.state.detect_stale is False
    assert persisted.state.align_stale is True


def test_persist_preview_scores_without_creating_slides(tmp_path):
    create_project(tmp_path, name="characterized")

    AppServiceRunner._persist_project_result(
        tmp_path,
        "quick_preview",
        {
            "success": True,
            "score_timestamps": [1.0, 2.0],
            "score_values": [0.1, 0.2],
        },
    )

    persisted = open_project(tmp_path)
    assert persisted.state.preview_done is True
    assert persisted.score_timestamps == [1.0, 2.0]
    assert persisted.score_values == [0.1, 0.2]
    assert persisted.slides == []
