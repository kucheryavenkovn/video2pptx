# FILE: src/video2pptx/gui/ui_state.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Read-only snapshot of MainWindow — button visibility/enabled/text, title, status, busy, current_operation.
#            No business logic. Safe to call without GUI (returns defaults).
#   SCOPE: read_ui_state()
#   DEPENDS: M-GUI-MAIN, PySide6.QtWidgets (optional)
#   LINKS: M-UI-STATE-READER
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   read_ui_state - return dict of button states + window metadata from MainWindow
# END_MODULE_MAP

from __future__ import annotations

from typing import Any


_BUTTON_NAMES = [
    "quick_preview",
    "detect",
    "auto_align",
    "process_notes",
    "auto",
    "export_md",
    "export_pptx",
    "save",
]


def _safe_button_state(btn) -> dict[str, Any]:
    try:
        return {
            "visible": btn.isVisible(),
            "enabled": btn.isEnabled(),
            "text": btn.text(),
        }
    except Exception:
        return {"visible": False, "enabled": False, "text": ""}


def read_ui_state(main_window=None) -> dict[str, Any]:
    """Return UI state snapshot from MainWindow or default empty state."""
    state: dict[str, Any] = {
        "window_title": "",
        "status_text": "",
        "busy": False,
        "current_operation": None,
        "buttons": {name: {"visible": False, "enabled": False, "text": ""} for name in _BUTTON_NAMES},
    }

    if main_window is None:
        return state

    try:
        state["window_title"] = main_window.windowTitle()
    except Exception:
        pass

    try:
        sb = main_window.statusBar()
        if sb:
            state["status_text"] = sb.currentMessage()
    except Exception:
        pass

    for name in _BUTTON_NAMES:
        attr = f"_btn_{name}"
        btn = getattr(main_window, attr, None)
        if btn:
            state["buttons"][name] = _safe_button_state(btn)

    return state
