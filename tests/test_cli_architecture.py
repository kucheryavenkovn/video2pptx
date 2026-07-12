# FILE: tests/test_cli_architecture.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Enforce architectural boundary — new CLI adapter code must not import
#            legacy pipeline modules or bypass Application Services.
#   SCOPE: All files in src/video2pptx/adapters/cli/ and src/video2pptx/bootstrap/
#   DEPENDS: ast, pathlib
#   LINKS: M-CLI-ADAPTER, M-APP-BOOTSTRAP, V-REF-CLI-ADAPTER
#   ROLE: TEST
#   MAP_MODE: LOCALS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ForbiddenImportTest - static AST analysis of banned imports
# END_MODULE_MAP

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Modules that new CLI/bootstrap code must NOT import
FORBIDDEN_IMPORTS: list[str] = [
    "video2pptx.cli",
    "video2pptx.detect_slides",
    "video2pptx.markdown_export",
    "video2pptx.notes_pipeline",
    "video2pptx.pptx_export",
    "video2pptx.models",
    "video2pptx.project_manager",
    "video2pptx.llm_orchestrator",
    "video2pptx.debug_export",
    "video2pptx.subtitles",
    "video2pptx.video_decode",
    "video2pptx.roi_tool",
]

# Files to scan (relative to src/video2pptx)
TARGET_PACKAGES = [
    "src/video2pptx/adapters/cli",
    "src/video2pptx/bootstrap",
]


def _collect_source_files() -> list[Path]:
    files: list[Path] = []
    for pkg in TARGET_PACKAGES:
        pkg_path = PROJECT_ROOT / pkg
        if pkg_path.is_dir():
            files.extend(sorted(pkg_path.rglob("*.py")))
    return files


@pytest.mark.parametrize("source_file", _collect_source_files())
def test_no_forbidden_legacy_imports(source_file: Path) -> None:
    """Check that new CLI/bootstrap code does not import legacy pipeline modules."""
    source = source_file.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_file))

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check_alias(alias.name, source_file)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                _check_alias(node.module, source_file)


def _check_alias(module_name: str, source_file: Path) -> None:
    """Fail if module_name matches a forbidden import."""
    for forbidden in FORBIDDEN_IMPORTS:
        if module_name == forbidden or module_name.startswith(forbidden + "."):
            rel = source_file.relative_to(PROJECT_ROOT)
            pytest.fail(f"{rel}: forbidden import '{module_name}' (matches '{forbidden}')")
