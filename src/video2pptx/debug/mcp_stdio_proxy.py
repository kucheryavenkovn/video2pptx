# FILE: src/video2pptx/debug/mcp_stdio_proxy.py
# PURPOSE: stdio↔HTTP MCP proxy — bridges OpenCode local MCP to video2pptx HTTP MCP on :9812
#   Handles initialize/initialized locally (no server needed). Forwards other calls with retry.
from __future__ import annotations

import json
import sys
import time
from http.client import HTTPConnection


def _forward(req: dict) -> dict:
    body = json.dumps(req, ensure_ascii=False, default=str)
    for attempt in range(5):
        try:
            c = HTTPConnection("127.0.0.1", 9812, timeout=10)
            c.request("POST", "/", body, {"Content-Type": "application/json"})
            resp = c.getresponse()
            return json.loads(resp.read().decode("utf-8"))
        except Exception:
            if attempt < 4:
                time.sleep(0.3 * (attempt + 1))
    return {"jsonrpc": "2.0", "id": req.get("id", 0),
            "error": {"code": -32603, "message": "GUI not running — start video2pptx gui first"}}


_initialized = False


def main() -> None:
    global _initialized
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = req.get("method", "")
        req_id = req.get("id", 0)

        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "video2pptx", "version": "0.1.0"},
            }
            resp = {"jsonrpc": "2.0", "id": req_id, "result": result}
            _initialized = True
        elif method == "notifications/initialized":
            continue  # No response needed for notifications
        elif not _initialized:
            resp = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32000, "message": "Not initialized"}}
        else:
            resp = _forward(req)

        sys.stdout.write(json.dumps(resp, ensure_ascii=False, default=str) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
