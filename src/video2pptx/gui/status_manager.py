# FILE: src/video2pptx/gui/status_manager.py
# VERSION: 0.3.0
# START_MODULE_CONTRACT
#   PURPOSE: QMainWindow status bar helper with operation identity — rejects stale/fake updates
#   SCOPE: Start/update/finish lifecycle with operation_key to prevent cross-operation corruption
#   DEPENDS: PySide6, time, loguru
#   LINKS: M-GUI-STATUS
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   StatusBarManager - manage status bar with operation-scoped progress
# END_MODULE_MAP

from __future__ import annotations

import time

from loguru import logger
from PySide6.QtWidgets import QMainWindow


class StatusBarManager:
    # START_CONTRACT: StatusBarManager
    #   PURPOSE: Manage QMainWindow status bar with operation identity
    #   INPUTS: { main_window: QMainWindow }
    #   OUTPUTS: formatted status messages via main_window.statusBar()
    #   SIDE_EFFECTS: updates status bar text (caller MUST be on main thread)
    #   LINKS: M-GUI-STATUS
    # END_CONTRACT: StatusBarManager

    def __init__(self, main_window: QMainWindow) -> None:
        self._mw = main_window
        self._start_time: float | None = None
        self._label: str = ""
        self._operation_key: str = ""

    def start(self, operation_key: str, label: str) -> None:
        self._operation_key = operation_key
        self._label = label
        self._start_time = time.monotonic()
        self._mw.statusBar().showMessage(f"{label}... 0%")
        logger.info("[GUI-Status][start] key={} label={}", operation_key, label)

    def key(self) -> str:
        return self._operation_key

    def update(self, pct: int, msg: str = "", operation_key: str = "") -> None:
        if self._start_time is None:
            return
        if operation_key and operation_key != self._operation_key:
            return  # stale update from a different operation
        elapsed = time.monotonic() - self._start_time
        elapsed_str = _fmt_duration(elapsed)
        if pct >= 10:
            remaining = elapsed * (100 - pct) / max(pct, 5)
            eta_str = _fmt_duration(remaining)
            bar_text = f"{self._label}: {pct}% | elapsed {elapsed_str} | ~{eta_str} left"
        else:
            bar_text = f"{self._label}: {pct}% | elapsed {elapsed_str}"
        if msg:
            bar_text += f" | {msg}"
        self._mw.statusBar().showMessage(bar_text)

    def finish(self, msg: str = "", operation_key: str = "") -> None:
        if operation_key and operation_key != self._operation_key:
            return
        if self._start_time is None:
            text = msg or f"{self._label} complete"
        else:
            elapsed = time.monotonic() - self._start_time
            elapsed_str = _fmt_duration(elapsed)
            text = msg or f"{self._label} complete ({elapsed_str})"
        self._mw.statusBar().showMessage(text)
        logger.info("[GUI-Status][finish] key={} msg={}", self._operation_key, text)
        self._start_time = None


def _fmt_duration(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
