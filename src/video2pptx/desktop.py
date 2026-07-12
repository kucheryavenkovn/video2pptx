# FILE: src/video2pptx/desktop.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Canonical desktop GUI entry point for packaged and source mode.
#   SCOPE: Create QApplication, build ApplicationServices, instantiate MainWindow, enter event loop.
#          No CLI argument parsing, no MCP host — those are started by MainWindow itself.
#   DEPENDS: PySide6, M-GUI-MAIN, M-APP-BOOTSTRAP
#   LINKS: M-DESKTOP-BOOTSTRAP
#   ROLE: ENTRY_POINT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   run_desktop - create app and MainWindow, return exit code
#   main - sys.argv entry point for console_scripts or packaging spec
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Initial desktop bootstrap
# END_CHANGE_SUMMARY

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from video2pptx.application.identity import application_identity


def run_desktop() -> int:
    """Create QApplication, build MainWindow, enter Qt event loop.

    Returns exit code suitable for sys.exit().
    """
    identity = application_identity()
    app = QApplication(sys.argv)
    app.setApplicationName(identity.name)
    app.setApplicationVersion(identity.version_str)
    app.setOrganizationName(identity.author)

    # Lazy import to keep desktop.py light
    from video2pptx.gui.main_window import MainWindow

    window = MainWindow()
    window.show()

    logger = __import__("loguru").logger
    logger.info("[Desktop] Started | version={} frozen={}", identity.version_str, identity.is_frozen)

    return app.exec()


def main() -> None:
    """Console_scripts entry point for desktop application."""
    sys.exit(run_desktop())
