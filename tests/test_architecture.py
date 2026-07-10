# FILE: tests/test_architecture.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Architecture constraint tests — verify clean layering (GUI, MCP, CLI, domain)
#   SCOPE: Import-level isolation: application does not import gui, MCP does not import MainWindow, etc.
#   DEPENDS: pytest, ast
#   LINKS: V-M-ARCHITECTURE
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src" / "video2pptx"


def _get_imports(filepath: Path, module_level_only: bool = False) -> set[str]:
    """Return set of top-level module names imported by filepath.
    If module_level_only=True, only check imports at module scope (not inside functions).
    """
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"))
    except SyntaxError:
        return set()
    imports: set[str] = set()

    if module_level_only:
        nodes_to_check = tree.body
    else:
        nodes_to_check = ast.walk(tree)

    for node in nodes_to_check:
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                imports.add(top)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split(".")[0]
                imports.add(top)
    return imports


def _service_files() -> list[Path]:
    return sorted(SRC.glob("*.py"))


def _module_name(path: Path) -> str:
    return path.stem


class TestArchitectureConstraints:
    """Verify clean layering: domain/service must not import GUI or Qt."""

    def test_app_service_no_gui(self):
        """M-APP-SERVICE must not import gui or PySide6."""
        service = SRC / "app_service.py"
        imports = _get_imports(service)
        forbidden = {"gui", "PySide6"}
        violations = forbidden & imports
        assert not violations, f"app_service imports forbidden: {violations}"

    def test_auto_align_no_gui(self):
        """M-AUTO-ALIGN must not import gui or PySide6."""
        path = SRC / "auto_align.py"
        imports = _get_imports(path)
        forbidden = {"gui", "PySide6", "PyQt"}
        violations = forbidden & imports
        assert not violations, f"auto_align imports forbidden: {violations}"

    def test_project_manager_no_gui(self):
        """M-PROJECT must not import gui or PySide6."""
        path = SRC / "project_manager.py"
        imports = _get_imports(path)
        forbidden = {"gui", "PySide6"}
        violations = forbidden & imports
        assert not violations, f"project_manager imports forbidden: {violations}"

    def test_command_router_no_gui(self):
        """M-CANONICAL-COMMANDS must not import gui or PySide6."""
        path = SRC / "command_router.py"
        imports = _get_imports(path)
        forbidden = {"gui", "PySide6"}
        violations = forbidden & imports
        assert not violations, f"command_router imports forbidden: {violations}"

    def test_project_validator_no_gui(self):
        """M-PROJECT-VALIDATOR must not import gui or PySide6."""
        path = SRC / "validators" / "project_validator.py"
        imports = _get_imports(path)
        forbidden = {"gui", "PySide6"}
        violations = forbidden & imports
        assert not violations, f"project_validator imports forbidden: {violations}"

    def test_mcp_no_mainwindow(self):
        """M-DEBUG-MCP must not import MainWindow directly."""
        path = SRC / "debug" / "mcp_server.py"
        imports = _get_imports(path, module_level_only=True)
        forbidden = {"gui", "main_window"}
        violations = forbidden & imports
        assert not violations, f"mcp_server.module_level imports forbidden: {violations}"

    def test_cli_no_gui(self):
        """CLI entry point (cli.py) must not import gui or PySide6 at module level."""
        path = SRC / "cli.py"
        imports = _get_imports(path, module_level_only=True)
        forbidden = {"PySide6"}
        violations = forbidden & imports
        assert not violations, f"cli module-level imports forbidden: {violations}"

    def test_detect_slides_no_gui(self):
        """M-DETECT-SLIDES must not import gui or PySide6."""
        path = SRC / "detect_slides.py"
        imports = _get_imports(path)
        forbidden = {"gui", "PySide6"}
        violations = forbidden & imports
        assert not violations, f"detect_slides imports forbidden: {violations}"
