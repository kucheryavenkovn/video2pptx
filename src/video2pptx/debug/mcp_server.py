# FILE: src/video2pptx/debug/mcp_server.py
# VERSION: 0.3.0
# START_MODULE_CONTRACT
#   PURPOSE: MCP HTTP server with SSE transport on 9812..9816 — exposes full app state, operation lifecycle, read/write tools
#   SCOPE: SSE at /sse, JSON-RPC at /messages. Operation lifecycle via M-OPERATION-REGISTRY + M-MCP-OPERATIONS.
#          Read tools via M-MCP-READ-TOOLS. Write tools via M-MCP-WRITE-TOOLS (Qt-affine via _CMD_QUEUE,
#          app_service ops via OpRunnerThread). Port fallback, stale file cleanup, versioned serverInfo.
#   DEPENDS: M-PROJECT-MODEL, M-TIMELINE-MODEL, M-GUI-LOG-BRIDGE, M-MCP-OPERATIONS, M-MCP-READ-TOOLS, M-MCP-WRITE-TOOLS
#   LINKS: M-DEBUG-MCP, M-MCP-RELIABILITY
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   McpServer - lifecycle (start/stop), port fallback, stale .mcp_port cleanup, SSE transport
#   mcp_process_queue - Qt main-thread drain for Qt-affine commands
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v0.3.0 - Wire OperationRegistry, full read/write tools, lifecycle tools, port hardening
#   v0.2.0 - Added SSE transport for OpenCode compatibility
#   v0.1.0 - Initial implementation
# END_CHANGE_SUMMARY

from __future__ import annotations

import json
import os
import uuid
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from queue import Queue
from socketserver import TCPServer, ThreadingMixIn
from threading import Thread
from typing import Any

from loguru import logger

from video2pptx.debug.action_registry import ActionRegistry
from video2pptx.debug.confirm import require_confirm
from video2pptx.debug.mcp_operations import (
    AppServiceRunner,
    OpRunnerThread,
    clear_registry,
    get_operation,
    get_registry,
    health,
    list_operations,
    submit,
    wait_operation,
)
from video2pptx.debug.mcp_write_tools import (
    dispatch_write,
    get_write_tool_defs,
    is_sync_tool,
)
from video2pptx.gui.log_bridge import LogBridge
from video2pptx.timeline_model import (
    MarkerClip,
    ScoreClip,
    ScoreTrack,
    SlideClip,
    SubtitleClip,
    Timeline,
)

_PACKAGE_VERSION = "0.6.0"


def _serialize_timeline(timeline: Timeline) -> dict:
    if timeline is None:
        return {"duration": 0, "tracks": {}}
    tracks = {}
    for name in timeline.track_names():
        track = timeline.track(name)
        if track is None:
            continue
        clips = []
        for clip in track.clips():
            base = {
                "uid": clip.uid, "start_sec": clip.start_sec,
                "end_sec": clip.end_sec, "duration": clip.duration,
            }
            if isinstance(clip, SlideClip):
                base["type"] = "slide"
                base["index"] = clip.index
                base["image_path"] = clip.image_path
                base["transcript_len"] = len(clip.transcript)
                base["notes_len"] = len(clip.notes)
                base["manual"] = clip.manual
            elif isinstance(clip, SubtitleClip):
                base["type"] = "subtitle"
                base["text"] = clip.plaintext[:80]
            elif isinstance(clip, MarkerClip):
                base["type"] = "marker"
                base["snapped_ts"] = clip.snapped_ts
                base["snap_mode"] = clip.snap_mode
            elif isinstance(clip, ScoreClip):
                base["type"] = "score"
                base["value"] = clip.value
                base["method"] = clip.method
            clips.append(base)
        track_info = {"name": name, "clip_count": len(clips), "clips": clips}
        if isinstance(track, ScoreTrack):
            track_info["min_value"] = track.min_value
            track_info["max_value"] = track.max_value
            track_info["method"] = track.method
        tracks[name] = track_info
    return {"duration": timeline.duration, "px_per_sec": timeline.px_per_sec, "tracks": tracks}


_QT_WRITE_CMDS: dict[str, tuple] = {
    "project_open": ("open", "path", ""),
    "project_close": ("close", None, None),
    "project_create": ("create", "path", ""),
    "project_save": ("save", None, None),
    "video_import": ("import_video", "path", ""),
    "subtitle_load": ("load_subtitles", "path", ""),
    "subtitle_import": ("load_subtitles", "path", ""),
    "slide_add": ("add_slide", "ts", 0.0),
    "slide_delete": ("delete_slide", "index", 1),
    "slide_move": ("move_slide", None, None),
    "video_seek": ("seek", "position", 0.0),
    "video_play": ("play", None, None),
    "video_pause": ("pause", None, None),
}

_QT_DESTRUCTIVE = {"project_close", "slide_delete", "slide_move"}


def _is_qt_affine(tool: str) -> bool:
    return tool in _QT_WRITE_CMDS


def _is_action_registry_tool(tool: str) -> bool:
    global ACTION_REGISTRY
    return ACTION_REGISTRY is not None and ACTION_REGISTRY.has(tool)


def _handle_rpc(method: str, params: dict, model, timeline: Timeline, main_window=None) -> Any:
    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "video2pptx", "version": _PACKAGE_VERSION},
        }
    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        tools = [
            # -- legacy read tools --
            {"name": "get_state", "description": "Full timeline dump: tracks, clips, counts", "inputSchema": {"type": "object"}},
            {"name": "get_project", "description": "Project metadata and state", "inputSchema": {"type": "object"}},
            {"name": "get_logs", "description": "Recent N log entries (default 50)", "inputSchema": {"type": "object", "properties": {"n": {"type": "integer"}}}},
            {"name": "get_clip", "description": "Details of one clip by track+index or track+uid", "inputSchema": {"type": "object", "properties": {"track": {"type": "string"}, "index": {"type": "integer"}, "uid": {"type": "string"}}}},
            # -- lifecycle tools --
            {"name": "health", "description": "MCP server health check", "inputSchema": {"type": "object"}},
            {"name": "get_capabilities", "description": "MCP protocol capabilities", "inputSchema": {"type": "object"}},
            {"name": "get_operation", "description": "Get operation status by ID", "inputSchema": {"type": "object", "properties": {"operation_id": {"type": "string"}}}},
            {"name": "wait_operation", "description": "Wait for operation to reach terminal status", "inputSchema": {"type": "object", "properties": {"operation_id": {"type": "string"}, "timeout": {"type": "number"}}}},
            {"name": "cancel_operation", "description": "Cancel a running operation", "inputSchema": {"type": "object", "properties": {"operation_id": {"type": "string"}, "confirm": {"type": "boolean"}}}},
            {"name": "list_operations", "description": "List recent operations", "inputSchema": {"type": "object", "properties": {"limit": {"type": "integer"}}}},
            # -- modern read tools --
            {"name": "get_app_state", "description": "Application state: version, backend, project", "inputSchema": {"type": "object"}},
            {"name": "get_ui_state", "description": "UI state: buttons, title, status, busy", "inputSchema": {"type": "object"}},
            {"name": "get_timeline", "description": "Full timeline with slide/subtitle/score tracks", "inputSchema": {"type": "object"}},
            {"name": "get_slide", "description": "Single slide by UID or 1-based index", "inputSchema": {"type": "object", "properties": {"uid": {"type": "string"}, "index": {"type": "integer"}}}},
            {"name": "get_subtitle_clip", "description": "Single subtitle clip by UID or index", "inputSchema": {"type": "object", "properties": {"uid": {"type": "string"}, "index": {"type": "integer"}}}},
            {"name": "list_artifacts", "description": "List project directory artifacts", "inputSchema": {"type": "object"}},
            {"name": "capture_screenshot", "description": "Capture MainWindow screenshot as base64 PNG", "inputSchema": {"type": "object"}},
        ]
        # Add modern write tools
        tools.extend(get_write_tool_defs())
        # Add legacy Qt-affine write tools (to keep backward compat)
        for name in _QT_WRITE_CMDS:
            if name not in {d["name"] for d in tools}:
                tools.append({
                    "name": name,
                    "description": f"(legacy) {name}",
                    "inputSchema": {"type": "object"},
                })
        # Add action registry tools
        if ACTION_REGISTRY is not None:
            tools.extend(ACTION_REGISTRY.tools())
        return {"tools": tools}

    if method == "tools/call":
        tool = params.get("name", "")
        args = params.get("arguments", {}) or {}

        # -- synchronous read tools --
        sync_handlers = {
            "get_state": lambda: _serialize_timeline(timeline),
            "get_project": lambda: _serialize_project(model),
            "get_logs": lambda: LogBridge.instance().recent(args.get("n", 50)),
            "get_clip": lambda: _handle_get_clip(args, timeline),
            "health": lambda: health(version=_PACKAGE_VERSION),
            "get_capabilities": lambda: _handle_get_capabilities(),
            "get_operation": lambda: get_operation(args.get("operation_id", "")),
            "wait_operation": lambda: wait_operation(args.get("operation_id", ""), args.get("timeout", 120.0)),
            "list_operations": lambda: list_operations(limit=args.get("limit", 20)),
            "get_app_state": lambda: _read_app_state(model, timeline),
            "get_ui_state": lambda: _read_ui_state(main_window),
            "get_timeline": lambda: _read_timeline(timeline),
            "list_artifacts": lambda: _read_artifacts(model),
        }

        if tool in sync_handlers:
            data = sync_handlers[tool]()
            return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, default=str, indent=2)}]}

        if tool in {"get_slide", "get_subtitle_clip", "capture_screenshot"}:
            return _handle_special_read(tool, args, timeline, main_window)

        # -- write tools (Qt-affine) --
        if _is_qt_affine(tool):
            require_confirm(tool, args)  # check confirm for destructive Qt ops
            info = _QT_WRITE_CMDS[tool]
            cmd_name = info[0]
            arg_name = info[1]
            default_val = info[2]
            if arg_name is not None and arg_name in args:
                cargs = (args[arg_name],)
            elif arg_name is not None and default_val is not None:
                cargs = (default_val,)
            else:
                cargs = ()
            _CMD_QUEUE.put((tool, cmd_name, cargs, {}))
            return {"content": [{"type": "text", "text": json.dumps({"status": "queued", "tool": tool, "op_type": "qt"})}]}

        # -- write tools (app_service via OpRunnerThread) --
        if not is_sync_tool(tool) and tool not in _QT_WRITE_CMDS:
            result = dispatch_write(tool, args, trace_id="")
            return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, default=str)}]}

        # -- action registry --
        if _is_action_registry_tool(tool):
            _ACTION_QUEUE.put(("__action__", (tool, args), {}))
            return {"content": [{"type": "text", "text": json.dumps({"status": "queued", "tool": tool, "op_type": "action"})}]}

        return {"content": [{"type": "text", "text": json.dumps({"error": f"unknown tool: {tool}"})}]}

    return {"error": f"unknown method: {method}"}


def _serialize_project(model) -> dict:
    if model is None or model.project_data is None:
        return {"error": "no project"}
    try:
        from video2pptx.debug.mcp_read_tools import get_project
        return get_project(model)
    except Exception as e:
        logger.warning(f"[McpServer] get_project fallback: {e}")
        proj = model.project_data
        return {
            "name": getattr(proj, "name", ""),
            "video": getattr(proj, "video", None),
            "has_subtitles": bool(getattr(proj, "subtitles", None)),
            "slides_count": len(getattr(proj, "slides", [])),
            "state": dict(getattr(getattr(proj, "state", None), "__dict__", {})),
        }


def _handle_get_clip(args: dict, timeline) -> dict:
    track_name = args.get("track", "slides")
    uid = args.get("uid")
    index = args.get("index")
    track = timeline.track(track_name) if timeline else None
    if track is None:
        return {"error": f"track '{track_name}' not found"}
    clips = track.clips()
    clip = None
    if uid is not None:
        clip = next((c for c in clips if c.uid == uid), None)
    elif index is not None and 0 <= index < len(clips):
        clip = clips[index]
    if clip is None:
        return {"error": "clip not found"}
    return {"uid": clip.uid, "type": type(clip).__name__, "start_sec": clip.start_sec, "end_sec": clip.end_sec}


def _handle_get_capabilities() -> dict:
    return {
        "protocol_version": "2024-11-05",
        "server_info": {"name": "video2pptx", "version": _PACKAGE_VERSION},
        "features": {
            "operation_lifecycle": True,
            "confirm_policy": True,
            "structured_errors": True,
            "atomic_writes": True,
        },
    }


def _read_app_state(model, timeline) -> dict:
    state = {"version": _PACKAGE_VERSION, "has_project": False, "project_path": None}
    if model and model.project_path:
        state["has_project"] = True
        state["project_path"] = str(model.project_path)
    return state


def _read_ui_state(main_window) -> dict:
    from video2pptx.gui.ui_state import read_ui_state
    return read_ui_state(main_window)


def _read_timeline(timeline) -> dict:
    from video2pptx.debug.mcp_read_tools import get_timeline as read_tl
    return read_tl(timeline)


def _read_artifacts(model) -> list:
    if model is None or model.project_path is None:
        return []
    from video2pptx.debug.mcp_read_tools import list_artifacts
    return list_artifacts(model.project_path)


def _handle_special_read(tool: str, args: dict, timeline, main_window) -> dict:
    from video2pptx.debug.mcp_read_tools import get_slide, get_subtitle_clip, capture_screenshot
    if tool == "get_slide":
        return {"content": [{"type": "text", "text": json.dumps(get_slide(timeline, uid=args.get("uid"), index=args.get("index")), ensure_ascii=False, default=str, indent=2)}]}
    if tool == "get_subtitle_clip":
        return {"content": [{"type": "text", "text": json.dumps(get_subtitle_clip(timeline, uid=args.get("uid"), index=args.get("index")), ensure_ascii=False, default=str, indent=2)}]}
    if tool == "capture_screenshot":
        return {"content": [{"type": "text", "text": json.dumps(capture_screenshot(main_window), ensure_ascii=False, default=str, indent=2)}]}
    return {"content": [{"type": "text", "text": json.dumps({"error": f"unknown read tool: {tool}"})}]}


class _Handler(BaseHTTPRequestHandler):
    model = None
    timeline = None
    main_window = None
    _sse_clients: dict[str, Any] = {}
    _running = True

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(health(version=_PACKAGE_VERSION))
            return
        self._handle_sse()

    def do_POST(self) -> None:
        if self.path.startswith("/messages"):
            self._handle_message()
        else:
            self._handle_rpc_direct()

    def _handle_sse(self) -> None:
        session_id = uuid.uuid4().hex[:12]
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        self.wfile.write(f"event: endpoint\ndata: /messages?sessionId={session_id}\n\n".encode())
        self.wfile.flush()

        self.__class__._sse_clients[session_id] = self.wfile
        try:
            while self.__class__._running:
                self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()
                import time
                time.sleep(15)
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            self.__class__._sse_clients.pop(session_id, None)

    def _handle_message(self) -> None:
        import re
        m = re.search(r"sessionId=([a-f0-9]+)", self.path)
        session_id = m.group(1) if m else None
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            req = json.loads(body)
        except json.JSONDecodeError:
            self._send_json({"jsonrpc": "2.0", "id": 0, "error": {"code": -32700, "message": "Parse error"}})
            return

        method = req.get("method", "")
        params = req.get("params", {})
        req_id = req.get("id", 1)
        try:
            result = _handle_rpc(method, params, self.model, self.timeline, self.main_window)
            resp = {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as e:
            resp = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32603, "message": str(e)}}

        if session_id and session_id in self.__class__._sse_clients:
            w = self.__class__._sse_clients[session_id]
            try:
                payload = json.dumps(resp, ensure_ascii=False, default=str)
                w.write(f"event: message\ndata: {payload}\n\n".encode())
                w.flush()
            except Exception:
                self.__class__._sse_clients.pop(session_id, None)
        self._send_json({"jsonrpc": "2.0", "id": req_id, "result": None})

    def _handle_rpc_direct(self) -> None:
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            req = json.loads(body)
        except json.JSONDecodeError:
            self._send_json({"jsonrpc": "2.0", "id": 0, "error": {"code": -32700, "message": "Parse error"}})
            return
        method = req.get("method", "")
        params = req.get("params", {})
        req_id = req.get("id", 1)
        try:
            result = _handle_rpc(method, params, self.model, self.timeline, self.main_window)
            self._send_json({"jsonrpc": "2.0", "id": req_id, "result": result})
        except Exception as e:
            self._send_json({"jsonrpc": "2.0", "id": req_id, "error": {"code": -32603, "message": str(e)}})

    def _send_json(self, data: dict) -> None:
        payload = json.dumps(data, ensure_ascii=False, default=str)
        payload_bytes = payload.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(payload_bytes)
        self.close_connection = True

    def log_message(self, fmt, *args) -> None:
        logger.debug(f"[McpServer] {fmt % args}")


class _ThreadedServer(ThreadingMixIn, TCPServer):
    allow_reuse_address = True
    daemon_threads = True


_CMD_QUEUE: Queue[tuple[str, str, tuple, dict]] = Queue()
_ACTION_QUEUE: Queue[tuple[str, tuple, dict]] = Queue()
ACTION_REGISTRY: ActionRegistry | None = None
_OP_RUNNER_THREAD: OpRunnerThread | None = None


def mcp_process_queue(model) -> None:
    while not _CMD_QUEUE.empty():
        tool_name, cmd_name, args, kwargs = _CMD_QUEUE.get_nowait()
        fn = getattr(model, cmd_name, None)
        if fn:
            fn(*args, **kwargs)
            logger.debug(f"[McpServer] Qt command processed | tool={tool_name} cmd={cmd_name}")
    while not _ACTION_QUEUE.empty():
        name, args, kwargs = _ACTION_QUEUE.get_nowait()
        if name == "__action__" and ACTION_REGISTRY is not None:
            ACTION_REGISTRY.call(args[0], args[1] if len(args) > 1 else None)

    # Drain completed app_service operations and refresh GUI (F-0043 fix)
    from video2pptx.debug.mcp_operations import drain_completed_ops
    completed = drain_completed_ops()
    if completed and model is not None and model.project_path:
        try:
            model.refresh_from_disk()
        except Exception as e:
            logger.error(f"[McpServer] refresh_from_disk failed: {e}")


class McpServer:
    def __init__(
        self,
        model,
        timeline: Timeline,
        port: int = 9812,
        action_registry: ActionRegistry | None = None,
        main_window=None,
    ) -> None:
        self._model = model
        self._timeline = timeline
        self._port = port
        self._server: _ThreadedServer | None = None
        self._thread: Thread | None = None
        self._main_window = main_window
        global ACTION_REGISTRY
        ACTION_REGISTRY = action_registry

    def start(self) -> None:
        # Clean stale .mcp_port
        self._clean_stale_port_file()

        # Clear registry from any previous session
        clear_registry()

        _Handler.model = self._model
        _Handler.timeline = self._timeline
        _Handler.main_window = self._main_window
        _Handler._running = True
        _Handler._sse_clients.clear()

        port = self._port
        for attempt in range(5):
            try:
                self._server = _ThreadedServer(("127.0.0.1", port), _Handler)
                self._port = port
                break
            except OSError:
                port = self._port + 1 + attempt
        if self._server is None:
            logger.warning("[McpServer] Failed to start — no free port in range 9812-9816")
            return

        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

        # Start OpRunnerThread
        global _OP_RUNNER_THREAD
        runner = AppServiceRunner(project_model=self._model)
        _OP_RUNNER_THREAD = OpRunnerThread(runner=runner)
        _OP_RUNNER_THREAD.start()

        self._write_port_file()
        logger.info(f"[McpServer] Started on http://127.0.0.1:{self._port} | v{_PACKAGE_VERSION}")

    def _clean_stale_port_file(self) -> None:
        try:
            port_path = Path(os.getcwd()) / ".mcp_port"
            if port_path.is_file():
                port_path.unlink()
                logger.info("[McpServer] Removed stale .mcp_port")
        except Exception as e:
            logger.warning(f"[McpServer] Failed to clean stale port file: {e}")

    def _write_port_file(self) -> None:
        try:
            port_path = Path(os.getcwd()) / ".mcp_port"
            port_path.write_text(str(self._port), encoding="utf-8")
            logger.info(f"[McpServer] Port file written: {port_path}")
        except Exception as e:
            logger.warning(f"[McpServer] Failed to write port file: {e}")

    def stop(self) -> None:
        _Handler._running = False

        global _OP_RUNNER_THREAD
        if _OP_RUNNER_THREAD is not None:
            _OP_RUNNER_THREAD.stop()
            _OP_RUNNER_THREAD = None

        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None

        # Clean port file
        try:
            port_path = Path(os.getcwd()) / ".mcp_port"
            if port_path.is_file():
                port_path.unlink()
        except Exception:
            pass

        clear_registry()
        logger.info("[McpServer] Stopped")
