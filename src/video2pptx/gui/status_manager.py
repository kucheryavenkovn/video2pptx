# FILE: src/video2pptx/gui/status_manager.py
# VERSION: 0.4.0
# START_MODULE_CONTRACT
#   PURPOSE: QMainWindow status bar helper with operation identity — rejects stale/fake updates
#   SCOPE: Start/update/finish lifecycle with operation_key; monotonic percent; ETA policy
#   DEPENDS: PySide6, time, loguru
#   LINKS: M-GUI-STATUS, Phase-21 Wave 3
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   StatusBarManager - manage status bar with operation-scoped progress
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v0.4.0 - Phase 21: monotonic _last_pct, clamp 0–100, ETA after 3s and pct>=5
# END_CHANGE_SUMMARY

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
        self._last_pct: int = 0

    def start(self, operation_key: str, label: str) -> None:
        self._operation_key = operation_key
        self._label = label
        self._start_time = time.monotonic()
        self._last_pct = 0
        self._mw.statusBar().showMessage(f"{label}... 0%")
        logger.info("[GUI-Status][start] key={} label={}", operation_key, label)

    def key(self) -> str:
        return self._operation_key

    def last_percent(self) -> int:
        return self._last_pct

    def update(self, pct: int, msg: str = "", operation_key: str = "") -> None:
        if self._start_time is None:
            return
        if operation_key and operation_key != self._operation_key:
            return  # stale update from a different operation

        # Clamp and enforce monotonic displayed percent
        clamped = max(0, min(100, int(pct)))
        if clamped < self._last_pct:
            clamped = self._last_pct
        else:
            self._last_pct = clamped

        elapsed = time.monotonic() - self._start_time
        elapsed_str = _fmt_duration(elapsed)

        # ETA only after meaningful progress and elapsed time (never "~0:00 left" at start)
        show_eta = elapsed >= 3.0 and clamped >= 5 and clamped < 100
        if show_eta:
            remaining = elapsed * (100 - clamped) / max(clamped, 1)
            eta_str = _fmt_duration(remaining)
            bar_text = f"{self._label}: {clamped}% | elapsed {elapsed_str} | ~{eta_str} left"
        else:
            bar_text = f"{self._label}: {clamped}% | elapsed {elapsed_str}"

        if msg:
            # Prefer user-facing "deduplication" wording over ambiguous "merge"
            display_msg = msg.replace("merge", "deduplication") if "merge" in msg.lower() else msg
            bar_text += f" | {display_msg}"
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
        self._last_pct = 0


def _fmt_duration(seconds: float) -> str:
    minutes, secs = divmod(int(max(0.0, seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"
