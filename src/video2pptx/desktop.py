# FILE: src/video2pptx/desktop.py
# VERSION: 1.1.0
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
#   LAST_CHANGE: v1.1.0 - Added --diagnostics for packaged runtime verification
# END_CHANGE_SUMMARY

from __future__ import annotations

import sys


def _print_diagnostics() -> None:
    """Print packaged runtime capability info and exit."""
    import platform

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
    print(f"Application: {identity.name}")
    print(f"Version: {identity.version_str}")
    print(f"Build: {identity.build.commit_sha or 'unknown'}")
    print(f"Build type: {identity.build.build_type.value}")
    if identity.build.packaging_tool:
        print(f"Packaging: {identity.build.packaging_tool}")
    if identity.build.build_time:
        print(f"Built: {identity.build.build_time.isoformat()}")
    print(f"OS: {platform.system()} {platform.release()} ({platform.machine()})")
    print(f"Python: {platform.python_version()}")
    print(f"Frozen: {getattr(sys, 'frozen', False)}")
    print()
    print("Capabilities:")
    for mod_name, available in modules.items():
        status = "available" if available else "MISSING"
        print(f"  {mod_name}: {status}")
    sys.exit(0 if all(modules.values()) else 1)


def run_desktop() -> int:
    """Create QApplication, build MainWindow, enter Qt event loop.

    Returns exit code suitable for sys.exit().
    """
    if "--diagnostics" in sys.argv:
        _print_diagnostics()

    from PySide6.QtWidgets import QApplication

    from video2pptx.application.identity import application_identity

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

    # Schedule startup update check (non-blocking, after GUI visible)
    from video2pptx.gui.update_controller import UpdateController

    ctrl = UpdateController()
    ctrl.schedule_startup_check(window)

    return app.exec()


def main() -> None:
    """Console_scripts entry point for desktop application."""
    sys.exit(run_desktop())
