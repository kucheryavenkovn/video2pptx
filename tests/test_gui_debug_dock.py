# FILE: tests/test_gui_debug_dock.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Smoke tests for DebugDock, LogPanel, StatePanel
#   SCOPE: Widget creation, log append, state tree population
#   DEPENDS: video2pptx.gui.debug_dock, video2pptx.timeline_model, pytest-qt
#   LINKS: V-M-GUI-DEBUG-DOCK
# END_MODULE_CONTRACT

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from video2pptx.gui.debug_dock import DebugDock, LogPanel, StatePanel
from video2pptx.timeline_model import SlideClip, Timeline


class TestLogPanel:
    def test_append_log_entry(self, qtbot) -> None:
        panel = LogPanel()
        qtbot.addWidget(panel)
        panel.append("INFO", "12:00:00", "test message")
        text = panel._text.toPlainText()

    def test_level_colors_set(self) -> None:
        panel = LogPanel()
        assert "ERROR" in panel.LEVEL_COLORS
        assert "#ff" in panel.LEVEL_COLORS["ERROR"]

    def test_filter_combo_exists(self, qtbot) -> None:
        panel = LogPanel()
        qtbot.addWidget(panel)
        items = [panel._filter.itemText(i) for i in range(panel._filter.count())]
        assert "ALL" in items
        assert "ERROR" in items


class TestStatePanel:
    def test_refresh_empty_timeline(self, qtbot) -> None:
        panel = StatePanel()
        qtbot.addWidget(panel)
        timeline = Timeline()
        panel.set_targets(None, timeline)
        root = panel._tree.topLevelItem(0)
        assert root is not None

    def test_refresh_with_slide(self, qtbot) -> None:
        panel = StatePanel()
        qtbot.addWidget(panel)
        timeline = Timeline()
        track = timeline.create_track("slides")
        slide = SlideClip(0, 10)
        slide.index = 1
        track.add_clip(slide)
        panel.set_targets(None, timeline)
        root = panel._tree.topLevelItem(0)
        assert root.childCount() >= 1


class TestDebugDock:
    def test_create_dock(self, qtbot) -> None:
        dock = DebugDock()
        qtbot.addWidget(dock)
        assert dock.windowTitle() == "Debug"
        assert dock._tabs.count() == 2

    def test_append_log_via_dock(self, qtbot) -> None:
        dock = DebugDock()
        qtbot.addWidget(dock)
        dock.append_log("ERROR", "12:00:00", "crash!")
        text = dock._log_panel._text.toPlainText()
        assert "crash!" in text
