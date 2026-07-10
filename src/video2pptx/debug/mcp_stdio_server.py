# FILE: src/video2pptx/debug/mcp_stdio_server.py
# VERSION: 0.1.0
# PURPOSE: stdio-based MCP JSON-RPC server — reads requests from stdin, writes responses to stdout
from __future__ import annotations

import json
import sys

# Lazy imports — loaded on first request to avoid startup overhead
_server = None
_mcp_handler = None


def _init_handler():
    global _mcp_handler
    if _mcp_handler is not None:
        return
    from video2pptx.debug.mcp_server import _handle_rpc
    from video2pptx.gui.log_bridge import LogBridge
    from video2pptx.timeline_model import Timeline

    lb = LogBridge.instance()  # noqa: F841 — initializes singleton side-effect
    timeline = Timeline()

    class _ModelStub:
        project_data = None

    _mcp_handler = {
        "handle": _handle_rpc,
        "model": _ModelStub(),
        "timeline": timeline,
    }


def main() -> None:
    _init_handler()
    handler = _mcp_handler

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = req.get("method", "")
        params = req.get("params", {})
        req_id = req.get("id", 0)

        try:
            result = handler["handle"](method, params, handler["model"], handler["timeline"])
            resp = {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as e:
            resp = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32603, "message": str(e)}}

        sys.stdout.write(json.dumps(resp, ensure_ascii=False, default=str) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
