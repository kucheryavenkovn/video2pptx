"""Stage 2 cleanup decisions (per-entry).

For each V-M entry that needs special handling, this module provides:
- bounded_wave: explicit bounded wave command (when auto-derivation fails)
- remove_module_checks: True if all module-checks are non-executable
- force_blocked: True if status should become "blocked"
- blocked_reason: replacement blocked-reason text
- evidence_replacement: list of concrete observable evidence assertions
  (replaces existing <required-trace-assertions> contents)

This file is the single source of truth for the cleanup transformations.
Any V-M not listed uses defaults:
- bounded_wave auto-derived from declared tests/*.py test-files that exist on disk
- module-checks removed only if they reference missing files
- status unchanged
- evidence unchanged (handled separately by evidence module)
"""

# Explicit bounded-wave overrides for entries that have no usable test-files.
# Value is either a string pytest command or "" (no bounded surface, set entry
# to blocked/planned). When key absent, bounded wave is auto-derived.
EXPLICIT_BOUNDED_WAVE = {
    # Architecture entries (no declared test-files but real architecture tests exist)
    "V-M-ARCH-IMPORTS": "python -m pytest tests/test_architecture.py tests/test_cli_architecture.py -q",
    "V-M-REF-LEGACY": "python -m pytest tests/test_architecture.py tests/test_cli_architecture.py -q",
    "V-M-REF-CANONICAL-ROUTE": "python -m pytest tests/test_architecture.py tests/test_cli_architecture.py -q",

    # Phase-17 packaging entries — no executable pytest surface
    "V-M-REF-PACKAGING-INVENTORY": "",  # doc-only
    "V-M-REF-STANDALONE-BUILD": "",     # .spec + build.ps1
    "V-M-REF-PACKAGED-MCP": "",         # .ps1 smoke test
    "V-M-REF-WIN-RELEASE": "",          # .yml workflow definition
    "V-M-REF-CLEAN-WINDOWS": "",        # manual VM verification (already pending)

    # Phase-18 benchmark entries — evidence is committed JSON artifacts, not pytest
    "V-M-PERF-DETECT-SHORT-BENCHMARK": "",
    "V-M-PERF-DETECT-BOTTLENECK": "",

    # Phase-18 future planned steps — no implementation yet
    "V-M-PERF-DETECT-TARGETED": "",
    "V-M-PERF-DETECT-SHORT-REBENCHMARK": "",
    "V-M-PERF-DETECT-HERMES-REBENCHMARK": "",
    "V-M-PERF-DETECT-ACCEPTANCE": "",

    # Planned with no test-files
    "V-M-APP-LLM": "",
    "V-M-PORT-LLM": "",
    "V-M-GUI-CANONICAL-BUTTONS": "",
    "V-M-MCP-RELIABILITY": "",

    # Blocked modules with no test-files
    "V-M-ADAPTERS": "",
    "V-M-APP-BUILD-META": "",
    "V-M-APP-IDENTITY": "",
    "V-M-APP-INPUT-RESOLVER": "",
    "V-M-BACKEND-OPENCV": "",
    "V-M-BACKEND-PYAV": "",
    "V-M-DESKTOP-BOOTSTRAP": "",
    "V-M-DETECT-METRICS": "",
    "V-M-DETECT-PERF-DECISION": "",
    "V-M-GUI-ABOUT": "",
    "V-M-GUI-HELP-MENU": "",
    "V-M-GUI-PIPELINE-WORKER": "",
    "V-M-GUI-UPDATE-CTRL": "",
    "V-M-GUI-WINDOW-UI": "",
    "V-M-MCP-ADAPTER": "",
    "V-M-MCP-COMPOSITION": "",
    "V-M-PERSIST-DETECTION": "",
    "V-M-PORT-ALIGNMENT": "",
    "V-M-PORT-DETECTOR": "",
    "V-M-PORT-EXPORT": "",
    "V-M-PORT-NOTES": "",
    "V-M-PORT-PREVIEW": "",

    # Notebook / packaging entries
    "V-M-COLAB": "",  # colab notebook, not pytest-runnable

    # REF-CHAR-TESTS: blocked, the related characterization file is the
    # startup characterization (which exists); legacy test_characterization_adapters
    # does not exist. Bounded surface = the actual existing characterization file.
    "V-M-REF-CHAR-TESTS": "python -m pytest tests/e2e/test_mcp_startup_characterization.py -q",
}

# Entries where all module-checks must be removed because they reference
# missing/non-executable files. The blocked-reason will be set/updated too.
REMOVE_ALL_MODULE_CHECKS = {
    # Blocked entries whose module-check points at a missing test file
    "V-M-GUI-TIMELINE": (
        "No dedicated test exists for the legacy GUI timeline widget "
        "(tests/test_gui_timeline.py missing). Module check removed; "
        "STATUS stays blocked until a dedicated reproducible test is created."
    ),
    "V-M-GUI-TIMELINE-V2": (
        "No dedicated test exists for the GUI timeline v2 widget "
        "(tests/test_gui_timeline_v2.py missing). Module check removed; "
        "STATUS stays blocked until a dedicated reproducible test is created."
    ),
    "V-M-GUI-WORKER": (
        "No dedicated test exists for the GUI worker module "
        "(tests/test_gui_workers.py missing). Module check removed; "
        "STATUS stays blocked until a dedicated reproducible test is created."
    ),
    "V-M-GUI-UPDATE-CTRL": (
        "No dedicated test exists for the update controller "
        "(tests/test_update_checker.py missing; tests/test_update_service.py "
        "covers the service, not the controller). Module check removed; "
        "STATUS stays blocked until a dedicated controller test is created."
    ),
    "V-M-DEBUG-ACTION": (
        "No dedicated test exists for the @mcp_action / ActionRegistry contract "
        "(tests/test_debug_action.py missing). Module check removed; "
        "STATUS stays blocked until a dedicated test is created."
    ),
    "V-M-DEBUG-MCP": (
        "No dedicated test exists for the debug MCP server "
        "(tests/test_debug_mcp.py missing; prior module-check referenced the "
        "also-missing tests/test_debug_action.py). Module check removed; "
        "STATUS stays blocked until a dedicated test is created."
    ),
    "V-M-REF-CHAR-TESTS": (
        "No dedicated characterization-adapters test exists "
        "(tests/test_characterization_adapters.py missing; "
        "tests/test_characterization_fixtures.py + tests/e2e/test_mcp_startup_characterization.py "
        "exist but cover only fixtures/startup, not the adapter characterization contract). "
        "Module check removed; STATUS stays blocked until a dedicated test is created."
    ),
    # Planned entries whose module-check points at a not-yet-created test file
    "V-M-CANONICAL-COMMANDS": (
        "No dedicated command-router test exists yet "
        "(tests/test_command_router.py missing; tests/test_app_service_runner.py "
        "covers adjacent behavior). Module check removed until a dedicated "
        "test is created; STATUS stays planned."
    ),
    "V-M-GUI-CANONICAL-BUTTONS": (
        "No dedicated canonical-buttons test exists "
        "(tests/test_gui_canonical_buttons.py missing). Module check removed "
        "until a dedicated test is created; STATUS stays planned."
    ),
    "V-M-APP-SERVICE": (
        "No dedicated app-service test exists under that name "
        "(tests/test_app_service.py missing; tests/test_app_service_runner.py "
        "covers the runner). Module check removed until a dedicated test is "
        "created; STATUS stays planned."
    ),
    "V-M-MCP-RELIABILITY": (
        "No dedicated MCP reliability test exists "
        "(tests/test_mcp_reliability.py missing). Module check removed until "
        "a dedicated test is created; STATUS stays planned."
    ),
    "V-M-E2E-SNAPSHOT": (
        "No dedicated snapshot test exists at tests/e2e/test_snapshot.py "
        "(the snapshot helper lives in tools/e2e_snapshot.py and is exercised "
        "by tests/e2e/test_mcp_gui_workflow.py). Module check removed until a "
        "dedicated test is created; STATUS stays planned."
    ),
    # Non-executable module-checks (.ps1 / .yml / .spec / .ipynb / src files)
    "V-M-COLAB": (
        "Module check `pytest colab/video2pptx_colab.ipynb` is not executable "
        "by pytest. STATUS downgraded to blocked until an executable test is created."
    ),
    "V-M-REF-PACKAGED-MCP": (
        "Module check `pytest packaging/windows/smoke-test.ps1` is not executable "
        "by pytest. STATUS downgraded to blocked until an executable test is created."
    ),
    "V-M-REF-PACKAGING-PARITY": (
        "Module check targets src/ implementation files, not a test; pytest cannot "
        "execute it as a contract gate. STATUS downgraded to blocked until a "
        "dedicated test is created."
    ),
    "V-M-REF-STANDALONE-BUILD": (
        "Module check `pytest packaging/windows/pyinstaller/video2pptx.spec` is not "
        "executable by pytest. STATUS downgraded to blocked until an executable "
        "test is created."
    ),
    "V-M-REF-WIN-RELEASE": (
        "Module check `pytest .github/workflows/release-windows.yml` is not "
        "executable by pytest. STATUS downgraded to blocked until an executable "
        "test is created."
    ),
}

# Entries that should be downgraded to blocked (because they have no executable
# pytest evidence and previously held "passed" status). Maps vid -> new blocked-reason.
DOWNGRADE_TO_BLOCKED = {
    "V-M-COLAB": (
        "Prior 'passed' status was based on a Colab notebook that pytest cannot "
        "execute. No reproducible pytest evidence exists; STATUS downgraded to "
        "blocked until an executable test is created."
    ),
    "V-M-REF-PACKAGING-INVENTORY": (
        "Prior 'passed' status was based on documentation file existence "
        "(packaging/windows/inventory.md), not executable pytest evidence. "
        "STATUS downgraded to blocked until a dedicated test is created."
    ),
    "V-M-REF-STANDALONE-BUILD": (
        "Prior 'passed' status was based on PyInstaller spec/build.ps1 file "
        "existence, not executable pytest evidence. STATUS downgraded to blocked "
        "until a dedicated test is created."
    ),
    "V-M-REF-PACKAGED-MCP": (
        "Prior 'passed' status was based on a PowerShell smoke-test script, not "
        "executable pytest evidence. STATUS downgraded to blocked until a "
        "dedicated test is created."
    ),
    "V-M-REF-PACKAGING-PARITY": (
        "Prior 'passed' status was based on direct src/ imports, not executable "
        "pytest evidence. STATUS downgraded to blocked until a dedicated test "
        "is created."
    ),
    "V-M-REF-WIN-RELEASE": (
        "Prior 'passed' status was based on a GitHub workflow YAML file, not "
        "executable pytest evidence. STATUS downgraded to blocked until a "
        "dedicated test is created."
    ),
    # GUI widget entries whose only declared test is the MainWindow smoke test
    # (tests/test_gui_main.py) — that file does not exercise the widget contracts.
    "V-M-GUI-STATUS": (
        "Prior 'passed' status relied on tests/test_gui_main.py, which is a "
        "MainWindow smoke test (window creation, toolbar buttons, detect button) "
        "and does not assert any StatusBarManager contract. STATUS downgraded "
        "to blocked until a dedicated StatusBarManager test is created."
    ),
    "V-M-GUI-SUBTITLE-EDITOR": (
        "Prior 'passed' status relied on tests/test_gui_main.py, which is a "
        "MainWindow smoke test and does not assert any SubtitleEditorDialog "
        "contract. STATUS downgraded to blocked until a dedicated "
        "SubtitleEditorDialog test is created."
    ),
    "V-M-GUI-MARKER-PANEL": (
        "Prior 'passed' status relied on tests/test_gui_main.py, which is a "
        "MainWindow smoke test and does not assert any MarkerPanel contract. "
        "STATUS downgraded to blocked until a dedicated MarkerPanel test is "
        "created."
    ),
    "V-M-GUI-ROI-SELECTOR": (
        "Prior 'passed' status relied on tests/test_gui_main.py, which is a "
        "MainWindow smoke test and does not assert any RoiSelectorDialog "
        "contract. STATUS downgraded to blocked until a dedicated "
        "RoiSelectorDialog test is created."
    ),
}
