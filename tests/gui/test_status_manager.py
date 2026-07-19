# FILE: tests/gui/test_status_manager.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Phase 21 Wave 3 — StatusBarManager monotonic percent and ETA policy
#   ROLE: TEST
#   LINKS: M-GUI-STATUS, Phase-21
# END_MODULE_CONTRACT

from __future__ import annotations

import time

import pytest
from PySide6.QtWidgets import QApplication, QMainWindow

from video2pptx.gui.status_manager import StatusBarManager


@pytest.fixture(scope="module")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def status(qapp):
    win = QMainWindow()
    mgr = StatusBarManager(win)
    yield mgr, win
    win.close()


def test_progress_is_monotonic(status):
    mgr, win = status
    mgr.start("detect", "Detect")
    mgr.update(10, "a", operation_key="detect")
    mgr.update(40, "b", operation_key="detect")
    mgr.update(20, "c", operation_key="detect")  # must not decrease
    assert mgr.last_percent() == 40
    text = win.statusBar().currentMessage()
    assert "40%" in text
    assert "20%" not in text


def test_progress_never_returns_100_to_70(status):
    mgr, win = status
    mgr.start("detect", "Detect")
    mgr.update(100, "done", operation_key="detect")
    mgr.update(70, "pass2", operation_key="detect")
    assert mgr.last_percent() == 100
    assert "100%" in win.statusBar().currentMessage()


def test_eta_hidden_during_initial_seconds(status, monkeypatch):
    mgr, win = status
    mgr.start("detect", "Detect")
    # Force elapsed ~0 by patching start time to now
    mgr._start_time = time.monotonic()
    mgr.update(50, "fast", operation_key="detect")
    text = win.statusBar().currentMessage()
    assert "left" not in text


def test_eta_shown_after_threshold(status):
    mgr, win = status
    mgr.start("detect", "Detect")
    mgr._start_time = time.monotonic() - 5.0
    mgr.update(50, "mid", operation_key="detect")
    text = win.statusBar().currentMessage()
    assert "left" in text


def test_stale_operation_progress_rejected(status):
    mgr, win = status
    mgr.start("detect", "Detect")
    mgr.update(30, "ok", operation_key="detect")
    mgr.update(90, "stale", operation_key="export")
    assert mgr.last_percent() == 30
    assert "30%" in win.statusBar().currentMessage()


def test_clamp_out_of_range(status):
    mgr, win = status
    mgr.start("detect", "Detect")
    mgr.update(-10, "", operation_key="detect")
    assert mgr.last_percent() == 0
    mgr.update(150, "", operation_key="detect")
    assert mgr.last_percent() == 100
