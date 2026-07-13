# FILE: src/video2pptx/desktop.py
# VERSION: 1.1.1
# START_MODULE_CONTRACT
#   PURPOSE: Canonical desktop GUI entry point for packaged and source mode.
#   SCOPE: Create QApplication, build ApplicationServices, instantiate MainWindow, enter event loop.
#          No CLI argument parsing, no MCP host — those are started by MainWindow itself.
#          Supports --diagnostics for packaged runtime capability verification.
#   DEPENDS: PySide6, M-GUI-MAIN, M-APP-BOOTSTRAP
#   LINKS: M-DESKTOP-BOOTSTRAP
#   ROLE: ENTRY_POINT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   run_desktop - create app and MainWindow, return exit code
#   main - sys.argv entry point for console_scripts or packaging spec
#   _print_diagnostics - print packaged capability info and exit
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.1 - Restore pathlib.Path import used by frozen diagnostics output
# END_CHANGE_SUMMARY

from __future__ import annotations

import sys
from pathlib import Path

# Register Qt resources (branding PNGs via :/branding/ prefix)
import video2pptx.gui.resources.branding_rc  # noqa: F401


def _print_diagnostics(target=None) -> None:
    """Print packaged runtime capability info and exit.
    When frozen (GUI app), writes to diagnostics.txt in the app directory.
    """
    import platform
    import tempfile

    modules = {
        "PySide6": False,
        "cv2": False,
        "av": False,
        "pptx": False,
        "httpx": False,
        "yaml": False,
        "PIL": False,
        "numpy": False,
        "imagehash": False,
        "pysubs2": False,
        "packaging": False,
    }
    for mod_name in modules:
        try:
            __import__(mod_name)
            modules[mod_name] = True
        except ImportError:
            pass

    from video2pptx.application.identity import application_identity

    identity = application_identity()
    lines = []
    lines.append(f"Application: {identity.name}")
    lines.append(f"Version: {identity.version_str}")
    lines.append(f"Build: {identity.build.commit_sha or 'unknown'}")
    lines.append(f"Build type: {identity.build.build_type.value}")
    if identity.build.packaging_tool:
        lines.append(f"Packaging: {identity.build.packaging_tool}")
    if identity.build.build_time:
        lines.append(f"Built: {identity.build.build_time.isoformat()}")
    lines.append(f"OS: {platform.system()} {platform.release()} ({platform.machine()})")
    lines.append(f"Python: {platform.python_version()}")
    lines.append(f"Frozen: {getattr(sys, 'frozen', False)}")
    lines.append("")
    lines.append("Capabilities:")
    for mod_name, available in modules.items():
        status = "available" if available else "MISSING"
        lines.append(f"  {mod_name}: {status}")
    output = "\n".join(lines)
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).parent
        (exe_dir / "diagnostics.txt").write_text(output, encoding="utf-8")
        import tempfile
        (Path(tempfile.gettempdir()) / "video2pptx_diagnostics.txt").write_text(output, encoding="utf-8")
    print(output)
    sys.exit(0 if all(modules.values()) else 1)


def run_desktop() -> int:
    """Create QApplication, build MainWindow, enter Qt event loop.

    Returns exit code suitable for sys.exit().
    """
    # Must come before any Qt import to avoid importing PySide6 for diagnostics
    if "--diagnostics" in sys.argv or "--diag" in sys.argv:
        _print_diagnostics()

    from PySide6.QtWidgets import QApplication

    from video2pptx.application.identity import application_identity

    identity = application_identity()
    app = QApplication(sys.argv)
    app.setApplicationName(identity.name)
    app.setApplicationVersion(identity.version_str)
    app.setOrganizationName(identity.author)
    from PySide6.QtGui import QIcon
    win_icon = QIcon(":/branding/Video2PPTX-icon.png")
    if not win_icon.isNull():
        app.setWindowIcon(win_icon)

    # Lazy import to keep desktop.py light
    from video2pptx.gui.main_window import MainWindow

    window = MainWindow()
    window.show()

    logger = __import__("loguru").logger
    logger.info("[Desktop] Started | version={} frozen={}", identity.version_str, identity.is_frozen)

    # Schedule startup update check (non-blocking, after GUI visible)
    from video2pptx.gui.update_controller import UpdateController

    ctrl = UpdateController()
    ctrl.schedule_startup_check(window)

    return app.exec()


def main() -> None:
    """Console_scripts entry point for desktop application."""
    sys.exit(run_desktop())
