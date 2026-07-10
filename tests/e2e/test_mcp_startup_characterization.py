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

import json

from tools.mcp_e2e_runner import GuiProcessHarness, McpClient


def _call_and_wait(client, tool, arguments, timeout=30):
    queued = McpClient.result_data(client.tool_call(tool, arguments))
    assert queued["status"] == "queued"
    completed = client.wait_operation(queued["operation_id"], timeout=timeout)
    assert completed["status"] == "succeeded", completed
    return completed


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


def test_real_gui_mcp_auto_align_dry_run_apply_and_idempotency(
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
        project_dir = project_parent / "align_characterized"
        _call_and_wait(
            client,
            "project_create",
            {"path": str(project_parent), "name": "align_characterized"},
        )
        _call_and_wait(
            client,
            "video_import",
            {"path": str(synthetic_video_path)},
        )
        _call_and_wait(
            client,
            "subtitle_import",
            {"path": str(synthetic_subtitle_path)},
        )
        _call_and_wait(client, "detect", {"confirm": True}, timeout=120)

        project_json = project_dir / "project.json"
        slides_json = project_dir / "slides.json"
        project_before = project_json.read_bytes()
        slides_before = slides_json.read_bytes()
        timeline_before = McpClient.result_data(
            client.tool_call("get_timeline")
        )

        dry_run = _call_and_wait(
            client,
            "auto_align",
            {"dry_run": True, "max_shift_sec": 3.0},
        )
        assert dry_run["result"]["dry_run"] is True
        assert project_json.read_bytes() == project_before
        assert slides_json.read_bytes() == slides_before
        assert not (project_dir / "alignment_report.json").exists()
        assert McpClient.result_data(
            client.tool_call("get_timeline")
        ) == timeline_before
        project = McpClient.result_data(client.tool_call("get_project"))
        assert project["pipeline_state"]["align_done"] is False

        _call_and_wait(
            client,
            "auto_align",
            {"dry_run": False, "max_shift_sec": 3.0, "confirm": True},
        )
        aligned_once = slides_json.read_bytes()
        document = json.loads(aligned_once)
        slides = document["slides"]
        assert slides
        assert [slide["index"] for slide in slides] == list(
            range(1, len(slides) + 1)
        )
        assert all(slide["start"] < slide["end"] for slide in slides)
        assert all(
            left["end"] <= right["start"]
            for left, right in zip(slides, slides[1:], strict=False)
        )
        assert (project_dir / "alignment_report.json").is_file()
        project = McpClient.result_data(client.tool_call("get_project"))
        assert project["pipeline_state"]["align_done"] is True
        assert project["slides_count"] == len(slides)

        _call_and_wait(
            client,
            "auto_align",
            {"dry_run": False, "max_shift_sec": 3.0, "confirm": True},
        )
        assert slides_json.read_bytes() == aligned_once
    finally:
        harness.stop()


def test_real_gui_mcp_slide_crud_keeps_four_views_consistent(
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
        project_dir = project_parent / "crud_characterized"
        _call_and_wait(
            client,
            "project_create",
            {"path": str(project_parent), "name": "crud_characterized"},
        )
        _call_and_wait(
            client,
            "video_import",
            {"path": str(synthetic_video_path)},
        )
        _call_and_wait(client, "detect", {"confirm": True}, timeout=120)

        timeline = McpClient.result_data(client.tool_call("get_timeline"))
        original = timeline["tracks"]["slides"]["clips"]
        original_count = len(original)
        first = original[0]
        split_at = (first["start_sec"] + first["end_sec"]) / 2

        added = _call_and_wait(client, "slide_add", {"ts": split_at})
        uid = added["result"]["uid"]
        created = McpClient.result_data(
            client.tool_call("get_slide", {"uid": uid})
        )
        assert created["uid"] == uid
        assert created["manual"] is True

        project = McpClient.result_data(client.tool_call("get_project"))
        timeline = McpClient.result_data(client.tool_call("get_timeline"))
        document = json.loads((project_dir / "slides.json").read_text("utf-8"))
        project_doc = json.loads((project_dir / "project.json").read_text("utf-8"))
        assert project["slides_count"] == original_count + 1
        assert timeline["tracks"]["slides"]["clip_count"] == original_count + 1
        assert len(document["slides"]) == original_count + 1
        assert len(project_doc["slides"]) == original_count + 1

        resized_end = first["start_sec"] + (
            split_at - first["start_sec"]
        ) * 0.8
        _call_and_wait(
            client,
            "slide_resize",
            {"index": 1, "end": resized_end, "confirm": True},
        )
        _call_and_wait(
            client,
            "slide_move",
            {
                "uid": uid,
                "start": resized_end,
                "end": first["end_sec"],
                "confirm": True,
            },
        )
        moved = McpClient.result_data(
            client.tool_call("get_slide", {"uid": uid})
        )
        assert moved["start_sec"] == resized_end
        assert moved["end_sec"] == first["end_sec"]
        persisted = next(
            slide
            for slide in json.loads(
                (project_dir / "slides.json").read_text("utf-8")
            )["slides"]
            if slide["uid"] == uid
        )
        assert persisted["start"] == resized_end
        assert persisted["end"] == first["end_sec"]

        _call_and_wait(client, "slide_set_frame", {"uid": uid})
        with_frame = McpClient.result_data(
            client.tool_call("get_slide", {"uid": uid})
        )
        assert with_frame["image_path"]
        assert (project_dir / "slides" / f"slide_{with_frame['index']:03d}.png").is_file()

        _call_and_wait(
            client,
            "slide_clear_image",
            {"uid": uid, "confirm": True},
        )
        cleared = McpClient.result_data(
            client.tool_call("get_slide", {"uid": uid})
        )
        assert cleared["image_path"] == ""

        _call_and_wait(
            client,
            "slide_delete",
            {"uid": uid, "confirm": True},
        )
        project = McpClient.result_data(client.tool_call("get_project"))
        timeline = McpClient.result_data(client.tool_call("get_timeline"))
        document = json.loads((project_dir / "slides.json").read_text("utf-8"))
        project_doc = json.loads((project_dir / "project.json").read_text("utf-8"))
        assert project["slides_count"] == original_count
        assert timeline["tracks"]["slides"]["clip_count"] == original_count
        assert len(document["slides"]) == original_count
        assert len(project_doc["slides"]) == original_count
        assert all(slide["uid"] != uid for slide in document["slides"])
    finally:
        harness.stop()
