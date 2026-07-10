# FILE: tests/e2e/test_mcp_startup_characterization.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Characterize real GUI subprocess startup and MCP transport without mocks.
#   SCOPE: Process lifecycle, fresh port discovery, health, initialize, tools/list, initial UI state.
#   DEPENDS: pytest, tools/mcp_e2e_runner.py, PySide6
#   LINKS: V-REF-CHAR-TESTS, E2E-001
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

from tools.mcp_e2e_runner import GuiProcessHarness, McpClient


def test_real_gui_mcp_startup(repo_dir, tmp_path):
    harness = GuiProcessHarness(
        repo=repo_dir,
        run_dir=tmp_path / "run",
        startup_timeout=30.0,
        qt_platform="offscreen",
    )
    try:
        client = harness.start()
        assert harness.process is not None
        assert harness.process.poll() is None
        assert harness.port_record is not None
        assert harness.port_record.pid == harness.process.pid
        assert harness.port_record.instance_id

        health = client.health()
        assert health["status"] == "ok"
        assert health["pid"] == harness.process.pid
        assert health["instance_id"] == harness.port_record.instance_id

        initialized = client.initialize()
        info = initialized["result"]["serverInfo"]
        assert info["name"] == "video2pptx"

        listed = client.tools_list()
        tool_names = {
            tool["name"] for tool in listed["result"]["tools"]
        }
        assert {
            "health",
            "get_ui_state",
            "get_project",
            "get_timeline",
            "project_create",
            "detect",
            "wait_operation",
        } <= tool_names

        ui = McpClient.result_data(client.tool_call("get_ui_state"))
        assert ui["window_title"].startswith("video2pptx")
        assert ui["busy"] is False
        assert ui["buttons"]["detect"]["enabled"] is False
        assert ui["buttons"]["auto_align"]["enabled"] is False
    finally:
        harness.stop()

    assert harness.process is not None
    assert harness.process.poll() is not None
    assert not harness.port_file.exists()


def test_real_gui_project_create_updates_model_and_window(repo_dir, tmp_path):
    harness = GuiProcessHarness(
        repo=repo_dir,
        run_dir=tmp_path / "run",
        startup_timeout=30.0,
        qt_platform="offscreen",
    )
    try:
        client = harness.start()
        project_parent = tmp_path / "projects"
        queued = McpClient.result_data(
            client.tool_call(
                "project_create",
                {"path": str(project_parent), "name": "characterized"},
            )
        )
        assert queued["status"] == "queued"
        assert queued["operation_id"]

        completed = client.wait_operation(queued["operation_id"], timeout=10)
        assert completed["status"] == "succeeded"

        project = McpClient.result_data(client.tool_call("get_project"))
        assert project["name"] == "characterized"
        assert project["project_dir"] == str(project_parent / "characterized")
        assert project["slides_count"] == 0

        ui = McpClient.result_data(client.tool_call("get_ui_state"))
        assert "characterized" in ui["window_title"]
        assert ui["buttons"]["save"]["enabled"] is True
        assert (project_parent / "characterized" / "project.json").is_file()
    finally:
        harness.stop()


def test_real_gui_mcp_detect_updates_project_timeline_and_disk(
    repo_dir,
    tmp_path,
    synthetic_video_path,
    synthetic_subtitle_path,
):
    harness = GuiProcessHarness(
        repo=repo_dir,
        run_dir=tmp_path / "run",
        startup_timeout=30.0,
        qt_platform="offscreen",
    )
    try:
        client = harness.start()
        project_parent = tmp_path / "projects"

        for tool, arguments in (
            (
                "project_create",
                {"path": str(project_parent), "name": "detect_characterized"},
            ),
            ("video_import", {"path": str(synthetic_video_path)}),
            ("subtitle_import", {"path": str(synthetic_subtitle_path)}),
        ):
            queued = McpClient.result_data(client.tool_call(tool, arguments))
            completed = client.wait_operation(queued["operation_id"], timeout=10)
            assert completed["status"] == "succeeded"

        queued = McpClient.result_data(
            client.tool_call("detect", {"confirm": True})
        )
        completed = client.wait_operation(queued["operation_id"], timeout=120)
        assert completed["status"] == "succeeded", completed

        project = McpClient.result_data(client.tool_call("get_project"))
        timeline = McpClient.result_data(client.tool_call("get_timeline"))
        project_dir = project_parent / "detect_characterized"

        assert project["pipeline_state"]["detect_done"] is True
        assert project["pipeline_state"]["align_done"] is False
        assert project["pipeline_state"]["notes_done"] is False
        assert project["slides_count"] > 0
        assert timeline["tracks"]["slides"]["clip_count"] == project["slides_count"]
        assert timeline["tracks"]["subtitles"]["clip_count"] == 4
        assert timeline["tracks"]["scores"]["clip_count"] > 0
        assert (project_dir / "project.json").is_file()
        assert (project_dir / "slides.json").is_file()
        assert not (project_dir / "deck.md").exists()
        assert not (project_dir / "deck.pptx").exists()

        ui = McpClient.result_data(client.tool_call("get_ui_state"))
        assert ui["buttons"]["auto_align"]["enabled"] is True
    finally:
        harness.stop()


def test_real_gui_mcp_quick_preview_is_idempotent_and_side_effect_free(
    repo_dir,
    tmp_path,
    synthetic_video_path,
):
    harness = GuiProcessHarness(
        repo=repo_dir,
        run_dir=tmp_path / "run",
        startup_timeout=30.0,
        qt_platform="offscreen",
    )
    try:
        client = harness.start()
        project_parent = tmp_path / "projects"
        for tool, arguments in (
            (
                "project_create",
                {"path": str(project_parent), "name": "preview_characterized"},
            ),
            ("video_import", {"path": str(synthetic_video_path)}),
        ):
            queued = McpClient.result_data(client.tool_call(tool, arguments))
            completed = client.wait_operation(queued["operation_id"], timeout=10)
            assert completed["status"] == "succeeded"

        score_counts = []
        for _ in range(2):
            queued = McpClient.result_data(
                client.tool_call("quick_preview", {})
            )
            completed = client.wait_operation(queued["operation_id"], timeout=60)
            assert completed["status"] == "succeeded", completed
            timeline = McpClient.result_data(client.tool_call("get_timeline"))
            score_counts.append(timeline["tracks"]["scores"]["clip_count"])

        project = McpClient.result_data(client.tool_call("get_project"))
        project_dir = project_parent / "preview_characterized"
        assert project["pipeline_state"]["preview_done"] is True
        assert project["pipeline_state"]["detect_done"] is False
        assert project["slides_count"] == 0
        assert score_counts[0] > 0
        assert score_counts[1] == score_counts[0]
        assert not (project_dir / "slides.json").exists()
        assert not (project_dir / "slides").exists()
        assert not (project_dir / "deck.md").exists()
        assert not (project_dir / "deck.pptx").exists()
    finally:
        harness.stop()
