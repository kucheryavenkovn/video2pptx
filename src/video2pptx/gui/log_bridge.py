# FILE: src/video2pptx/gui/log_bridge.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Loguru sink that captures log entries + emits Qt signal for live MCP log streaming
#   SCOPE: Singleton LogBridge with newLog Signal(Qt), recent(n) method, auto-installed Loguru sink
#   DEPENDS: PySide6.QtCore, loguru
#   LINKS: M-GUI-LOG-BRIDGE
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   LogBridge - Singleton capturing Loguru entries as structured dicts with Qt signal
# END_MODULE_MAP

from __future__ import annotations

from datetime import datetime
from typing import Any

from loguru import logger
from PySide6.QtCore import QObject, Signal


class LogBridge(QObject):
    """Singleton capturing Loguru entries for MCP live streaming."""

    newLog = Signal(str, str, str)  # level, time, message

    _instance: LogBridge | None = None

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[dict[str, Any]] = []
        self._max_entries: int = 500
        self._sink_id: int | None = None
        self._install_sink()

    def _sink(self, message: Any) -> None:
        record = message.record
        entry = {
            "level": record["level"].name,
            "time": record["time"].strftime("%H:%M:%S.%f")[:-3],
            "message": record["message"],
            "file": record["file"].name if record.get("file") else "",
            "line": record["line"],
            "function": record["function"],
        }
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
        self.newLog.emit(entry["level"], entry["time"], entry["message"])

    def recent(self, n: int = 50) -> list[dict[str, Any]]:
        return self._entries[-n:]

    def close(self) -> None:
        if self._sink_id is not None:
            try:
                logger.remove(self._sink_id)
            except ValueError:
                pass
            self._sink_id = None

    @classmethod
    def instance(cls) -> LogBridge:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _install_sink(self) -> None:
        self._sink_id = logger.add(
            self._sink,
            level="DEBUG",
            format="{message}",
            catch=True,
        )
