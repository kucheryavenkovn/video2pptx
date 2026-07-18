# FILE: tests/test_architecture.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Architecture constraint tests — verify clean layering (GUI, MCP, CLI, domain)
#   SCOPE: Import-level isolation: application does not import gui, MCP does not import MainWindow, etc.
#   DEPENDS: pytest, ast
#   LINKS: V-M-ARCHITECTURE, M-ARCH-OVERVIEW
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT

from __future__ import annotations

import ast
from pathlib import Path

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
                parts = node.module.split(".")
                imports.add(parts[0])
                if len(parts) > 1:
                    imports.add(parts[1])
    return imports


def _service_files() -> list[Path]:
    return sorted(SRC.glob("*.py"))


def _module_name(path: Path) -> str:
    return path.stem


class TestArchitectureConstraints:
    """Verify clean layering: domain/service must not import GUI or Qt."""

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
        forbidden = {"main_window"}
        violations = forbidden & imports
        assert not violations, f"mcp_server.module_level imports forbidden: {violations}"

    def test_cli_no_gui(self):
        """CLI entry point must not import gui or PySide6 at module level."""
        for name in ("cli.py",):
            path = SRC / name
            imports = _get_imports(path, module_level_only=True)
            forbidden = {"PySide6"}
            violations = forbidden & imports
            assert not violations, f"{name} module-level imports forbidden: {violations}"

    def test_cli_adapter_no_legacy_pipeline(self):
        """CLI adapter must not import legacy pipeline modules directly."""
        for name in ("app.py",):
            path = SRC / "adapters" / "cli" / name
            imports = _get_imports(path, module_level_only=True)
            forbidden = {"detect_slides", "notes_pipeline", "markdown_export",
                         "pptx_export", "llm_orchestrator", "project_manager"}
            violations = forbidden & imports
            assert not violations, f"{name} imports forbidden legacy: {violations}"

    def test_detect_slides_no_gui(self):
        """M-DETECT-SLIDES must not import gui or PySide6."""
        path = SRC / "detect_slides.py"
        imports = _get_imports(path)
        forbidden = {"gui", "PySide6"}
        violations = forbidden & imports
        assert not violations, f"detect_slides imports forbidden: {violations}"

    def test_gui_controllers_no_legacy_project(self):
        """gui/controllers/ must not import project_manager (use domain.Project)."""
        ctrl_dir = SRC / "gui" / "controllers"
        forbidden = {"project_manager"}
        for f in sorted(ctrl_dir.glob("*.py")):
            imports = _get_imports(f)
            violations = forbidden & imports
            assert not violations, f"{f.name} imports forbidden: {violations}"

    def test_gui_no_legacy_pipeline(self):
        """gui/ must not import legacy pipeline entry points."""
        forbidden = {"detect_slides", "notes_pipeline", "markdown_export", "pptx_export", "debug_export"}
        for f in sorted((SRC / "gui").rglob("*.py")):
            imports = _get_imports(f, module_level_only=True)
            violations = forbidden & imports
            assert not violations, f"{f.name} imports forbidden legacy pipeline: {violations}"

    def test_qt_write_cmds_only_ui_ops(self):
        """_QT_WRITE_CMDS must not contain project/slide CRUD — only UI transport ops."""
        import ast
        src = SRC / "debug" / "mcp_server.py"
        tree = ast.parse(src.read_text("utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "_QT_WRITE_CMDS":
                        keys = []
                        for k in node.value.keys:
                            if isinstance(k, ast.Constant):
                                keys.append(k.value)
                        forbidden = {"project_save", "video_import", "subtitle_load",
                                     "subtitle_import", "slide_add", "slide_delete",
                                     "slide_move", "slide_resize"}
                        violations = set(keys) & forbidden
                        assert not violations, f"_QT_WRITE_CMDS contains forbidden project/slide ops: {violations}"
                        break

    def test_mcp_no_legacy_pipeline_at_module_level(self):
        """MCP debug modules must not import legacy pipeline at module level."""
        debug_dir = SRC / "debug"
        forbidden = {"detect_slides", "notes_pipeline", "markdown_export",
                     "pptx_export", "project_manager", "workers"}
        for f in sorted(debug_dir.glob("*.py")):
            imports = _get_imports(f, module_level_only=True)
            violations = forbidden & imports
            assert not violations, f"{f.name} imports forbidden legacy: {violations}"
