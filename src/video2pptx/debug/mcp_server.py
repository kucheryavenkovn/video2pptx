# FILE: src/video2pptx/debug/mcp_server.py
# VERSION: 0.2.0
# START_MODULE_CONTRACT
#   PURPOSE: MCP HTTP server with SSE transport on :9812 — exposes app state for AI debugging
#   SCOPE: SSE at /sse, JSON-RPC at /messages. Tools: get_state, get_project, get_logs, get_clip
#   DEPENDS: M-PROJECT-MODEL, M-TIMELINE-MODEL, M-GUI-LOG-BRIDGE
#   LINKS: M-DEBUG-MCP
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   McpServer -
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v0.2.0 - Added SSE transport for OpenCode compatibility
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
from video2pptx.gui.log_bridge import LogBridge
from video2pptx.timeline_model import (
    MarkerClip,
    ScoreClip,
    ScoreTrack,
    SlideClip,
    SubtitleClip,
    Timeline,
)


def _serialize_timeline(timeline: Timeline) -> dict:
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


def _serialize_project(project) -> dict:
    if project is None:
        return {"error": "no project"}
    return {
        "name": project.name, "video": project.video,
        "has_subtitles": bool(project.subtitles),
        "slides_count": len(project.slides),
        "markers_count": len(project.markers),
        "state": {"detect_done": project.state.detect_done,
                   "notes_done": project.state.notes_done,
                   "llm_done": project.state.llm_done},
    }


def _handle_rpc(method: str, params: dict, model, timeline: Timeline) -> Any:
    global _SEQ
    if method == "tools/list":
        tools = [
            {"name": "get_state", "description": "Full timeline dump: tracks, clips, counts", "inputSchema": {"type": "object"}},
            {"name": "get_project", "description": "Project metadata and state", "inputSchema": {"type": "object"}},
            {"name": "get_logs", "description": "Recent N log entries (default 50)", "inputSchema": {"type": "object", "properties": {"n": {"type": "integer"}}}},
            {"name": "get_clip", "description": "Details of one clip by track+index or track+uid", "inputSchema": {"type": "object", "properties": {"track": {"type": "string"}, "index": {"type": "integer"}, "uid": {"type": "string"}}}},
            {"name": "project_open", "description": "Open existing project by directory path", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}}},
            {"name": "project_close", "description": "Close current project", "inputSchema": {"type": "object"}},
            {"name": "project_create", "description": "Create new project at directory", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "name": {"type": "string"}}}},
            {"name": "project_save", "description": "Save current project to disk", "inputSchema": {"type": "object"}},
            {"name": "slide_add", "description": "Add manual slide at timestamp", "inputSchema": {"type": "object", "properties": {"ts": {"type": "number"}}}},
            {"name": "slide_delete", "description": "Delete slide by 1-based index", "inputSchema": {"type": "object", "properties": {"index": {"type": "integer"}}}},
            {"name": "slide_move", "description": "Move slide to new start/end times", "inputSchema": {"type": "object", "properties": {"index": {"type": "integer"}, "start": {"type": "number"}, "end": {"type": "number"}}}},
            {"name": "video_import", "description": "Import video file into current project", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}}},
            {"name": "subtitle_load", "description": "Load subtitle file into current project", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}}},
        ]
        if ACTION_REGISTRY is not None:
            tools.extend(ACTION_REGISTRY.tools())
        return {"tools": tools}
    if method == "tools/call":
        tool = params.get("name", "")
        args = params.get("arguments", {})
        if tool == "get_state":
            data = _serialize_timeline(timeline)
            return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, default=str, indent=2)}]}
        if tool == "get_project":
            data = _serialize_project(model.project_data if model else None)
            return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, default=str, indent=2)}]}
        if tool == "get_logs":
            data = LogBridge.instance().recent(args.get("n", 50))
            return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, default=str, indent=2)}]}
        if tool == "get_clip":
            track_name = args.get("track", "slides")
            index = args.get("index")
            uid = args.get("uid")
            track = timeline.track(track_name) if timeline else None
            if track is None:
                return {"content": [{"type": "text", "text": json.dumps({"error": f"track '{track_name}' not found"})}]}
            clips = track.clips()
            clip = None
            if uid is not None:
                clip = next((c for c in clips if c.uid == uid), None)
            elif index is not None and 0 <= index < len(clips):
                clip = clips[index]
            if clip is None:
                return {"content": [{"type": "text", "text": json.dumps({"error": "clip not found"})}]}
            data = {"uid": clip.uid, "type": type(clip).__name__, "start_sec": clip.start_sec, "end_sec": clip.end_sec}
            return {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, default=str, indent=2)}]}
        # -- write tools (via command queue) --
        write_cmds = {
            "project_open": ("open", (args.get("path", ""),), {}),
            "project_close": ("close", (), {}),
            "project_create": ("create", (args.get("path", ""),), {"name": args.get("name", "Untitled")}),
            "project_save": ("save", (), {}),
            "slide_add": ("add_slide", (args.get("ts", 0.0),), {}),
            "slide_delete": ("delete_slide", (args.get("index", 1),), {}),
            "slide_move": ("move_slide", (args.get("index", 1), args.get("start", 0.0), args.get("end", 5.0)), {}),
            "video_import": ("import_video", (args.get("path", ""),), {}),
            "subtitle_load": ("load_subtitles", (args.get("path", ""),), {}),
        }
        if tool in write_cmds:
            cmd, cargs, ckwargs = write_cmds[tool]
            _CMD_QUEUE.put((cmd, cargs, ckwargs))
            _SEQ += 1
            return {"content": [{"type": "text", "text": json.dumps({"status": "queued", "seq": _SEQ, "tool": tool})}]}
        if ACTION_REGISTRY is not None and ACTION_REGISTRY.has(tool):
            _ACTION_QUEUE.put(("__action__", (tool, args), {}))
            _SEQ += 1
            return {"content": [{"type": "text", "text": json.dumps({"status": "queued", "seq": _SEQ, "tool": tool})}]}

        return {"content": [{"type": "text", "text": json.dumps({"error": f"unknown tool: {tool}"})}]}
    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "video2pptx", "version": "0.1.0"},
        }

    if method == "notifications/initialized":
        return None

    return {"error": f"unknown method: {method}"}


class _Handler(BaseHTTPRequestHandler):
    model = None
    timeline = None
    _sse_clients: dict[str, Any] = {}
    _running = True

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json({"status": "ok", "port": self.server.server_address[1]})
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
            result = _handle_rpc(method, params, self.model, self.timeline)
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
        # Return ack to HTTP request
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
            result = _handle_rpc(method, params, self.model, self.timeline)
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


_CMD_QUEUE: Queue[tuple[str, tuple, dict]] = Queue()
_ACTION_QUEUE: Queue[tuple[str, tuple, dict]] = Queue()
_SEQ = 0
ACTION_REGISTRY: ActionRegistry | None = None


def mcp_process_queue(model) -> None:
    while not _CMD_QUEUE.empty():
        cmd, args, kwargs = _CMD_QUEUE.get_nowait()
        fn = getattr(model, cmd, None)
        if fn:
            fn(*args, **kwargs)
    while not _ACTION_QUEUE.empty():
        name, args, kwargs = _ACTION_QUEUE.get_nowait()
        if name == "__action__" and ACTION_REGISTRY is not None:
            ACTION_REGISTRY.call(args[0], args[1] if len(args) > 1 else None)


class McpServer:
    def __init__(self, model, timeline: Timeline, port: int = 9812, action_registry: ActionRegistry | None = None) -> None:
        self._model = model
        self._timeline = timeline
        self._port = port
        self._server: _ThreadedServer | None = None
        self._thread: Thread | None = None
        global ACTION_REGISTRY
        ACTION_REGISTRY = action_registry

    def start(self) -> None:
        _Handler.model = self._model
        _Handler.timeline = self._timeline
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
        self._write_port_file()
        logger.info(f"[McpServer] Started on http://127.0.0.1:{self._port} — state is LIVE (each tool call reads current model/timeline)")

    def _write_port_file(self) -> None:
        try:
            port_path = Path(os.getcwd()) / ".mcp_port"
            port_path.write_text(str(self._port), encoding="utf-8")
            logger.info(f"[McpServer] Port file written: {port_path}")
        except Exception as e:
            logger.warning(f"[McpServer] Failed to write port file: {e}")

    def stop(self) -> None:
        _Handler._running = False
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
            logger.info("[McpServer] Stopped")
