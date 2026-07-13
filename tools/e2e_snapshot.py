# FILE: tools/e2e_snapshot.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Capture full state snapshot: app/ui/project/timeline/artifacts/logs/screenshot + copy
#            project.json/slides.json for diff.
#   SCOPE: capture_snapshot() — collects data via MCP client, writes to snapshot dir
#   DEPENDS: M-MCP-READ-TOOLS
#   LINKS: M-E2E-SNAPSHOT
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   capture_snapshot - call MCP tools, collect state, copy files, write to snapshot dir
# END_MODULE_MAP

from __future__ import annotations

import json
import shutil
from pathlib import Path


def capture_snapshot(mcp_client, snapshot_dir: str | Path, label: str = "") -> Path:
    """Capture full state snapshot via MCP client.
    Returns path to snapshot directory.
    """
    base = Path(snapshot_dir)
    if label:
        base = base / label
    base.mkdir(parents=True, exist_ok=True)

    reads = {
        "app_state": ("get_app_state", {}),
        "ui_state": ("get_ui_state", {}),
        "project": ("get_project", {}),
        "timeline": ("get_timeline", {}),
        "artifacts": ("list_artifacts", {}),
        "logs": ("get_logs", {"n": 100}),
    }

    for name, (tool, args) in reads.items():
        try:
            resp = mcp_client.tool_call(tool, args)
            content = resp.get("content", [{}])
            text = content[0].get("text", "{}") if content else "{}"
            data = json.loads(text) if isinstance(text, str) else text
            (base / f"{name}.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2, default=str),
                encoding="utf-8",
            )
        except Exception as e:
            (base / f"{name}.error").write_text(str(e), encoding="utf-8")

    # Try screenshot
    try:
        resp = mcp_client.tool_call("capture_screenshot", {})
        content = resp.get("content", [{}])
        text = content[0].get("text", "{}") if content else "{}"
        data = json.loads(text) if isinstance(text, str) else text
        if "data" in data and "mime" in data:
            import base64
            img_data = base64.b64decode(data["data"])
            (base / "screenshot.png").write_bytes(img_data)
    except Exception:
        pass

    # Try to copy project.json and slides.json if they exist
    for fname in ("project.json", "slides.json"):
        try:
            resp = mcp_client.tool_call("get_project", {})
            content = resp.get("content", [{}])
            text = content[0].get("text", "{}") if content else "{}"
            data = json.loads(text) if isinstance(text, str) else text
            project_dir = data.get("project_dir")
            if project_dir:
                src = Path(project_dir) / fname
                if src.is_file():
                    shutil.copy2(src, base / fname)
        except Exception:
            pass

    return base
