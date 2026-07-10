# FILE: tests/test_gui_log_bridge.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for LogBridge — loguru→Qt signal bridge
#   SCOPE: Singleton instantiation, sink capture, signal emission, ring buffer, recent()
#   DEPENDS: video2pptx.gui.log_bridge, pytest
#   LINKS: V-M-GUI-LOG-BRIDGE
# END_MODULE_CONTRACT

from __future__ import annotations

from loguru import logger

from video2pptx.gui.log_bridge import LogBridge


class TestLogBridge:
    def test_singleton(self) -> None:
        lb1 = LogBridge.instance()
        lb2 = LogBridge.instance()
        assert lb1 is lb2

    def test_recent_empty(self) -> None:
        lb = LogBridge.instance()
        entries = lb.recent(10)
        assert isinstance(entries, list)

    def test_log_capture(self, qtbot) -> None:
        lb = LogBridge.instance()
        with qtbot.waitSignal(lb.newLog, timeout=2000):
            logger.info("Test log message for LogBridge")

    def test_recent_after_log(self) -> None:
        lb = LogBridge.instance()
        logger.info("LogBridge test message 2")
        entries = lb.recent(5)
        assert any("LogBridge test message 2" in e["message"] for e in entries)

    def test_signal_format(self, qtbot) -> None:
        lb = LogBridge.instance()

        def _check(level: str, time_str: str, message: str) -> None:
            assert level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
            assert ":" in time_str

        lb.newLog.connect(_check)
        logger.info("Format test")
        lb.newLog.disconnect(_check)
