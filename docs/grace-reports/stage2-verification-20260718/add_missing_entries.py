"""Add new V-M entries for the 30 modules without verification.

HONEST STATUS ASSIGNMENT (status follows evidence):
- passed: 6 modules with a dedicated test that we ran successfully
- blocked: 22 implemented/active modules without a dedicated passing test
- planned: 2 modules whose module status is 'planned'

Evidence is recorded inline for passed entries (test name + result count).
Blocked entries cite the concrete missing-artifact reason.
Planned entries do not claim evidence.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VP_PATH = ROOT / "docs" / "verification-plan.xml"
REPORT_DIR = ROOT / "docs" / "grace-reports" / "stage2-verification-20260718"

with open(REPORT_DIR / "missing-vm-status.json", "r", encoding="utf-8") as f:
    MISSING = json.load(f)


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# Hand-curated honest classifications with concrete evidence.
# Passed entries: test was run in Stage 2 and observed passing.
DETAIL = {
    # --- PASSED (real test evidence from Stage 2 runs) ---
    "M-APP-BOOTSTRAP": {
        "status": "passed", "priority": "medium",
        "test_files": ["tests/test_bootstrap.py"],
        "module_checks": ["python -m pytest tests/test_bootstrap.py -q"],
        "wave": "python -m pytest tests/test_bootstrap.py tests/application -q",
        "phase": "python -m pytest --ignore=tests/e2e -q",
        "evidence": "tests/test_bootstrap.py: 13 passed (Stage 2 run). Application services compose without import cycles.",
        "scenarios": [
            ("success", "Application bootstrap composes the service context without import cycles."),
            ("failure", "Bootstrap surfaces missing dependency contracts as a structured error."),
        ],
        "assertions": [
            "ApplicationServicesBootstrap composes ApplicationServiceRunner deterministically.",
            "Bootstrap produces exactly one ServiceContext instance with stable service references.",
        ],
    },
    "M-APP-COMMON": {
        "status": "passed", "priority": "medium",
        "test_files": ["tests/application/test_common.py"],
        "module_checks": ["python -m pytest tests/application/test_common.py -q"],
        "wave": "python -m pytest tests/application -q",
        "phase": "python -m pytest --ignore=tests/e2e -q",
        "evidence": "tests/application/test_common.py: 19 passed (Stage 2 run). Application common helpers behave deterministically.",
        "scenarios": [
            ("success", "ApplicationCommon helpers produce deterministic outputs for canonical inputs."),
            ("failure", "Malformed input to common helpers raises a typed validation error."),
        ],
        "assertions": [
            "ApplicationCommon helpers return stable deterministic results across repeated calls.",
            "Common path and input resolution reject ambiguous inputs with a structured error.",
        ],
    },
    "M-GUI-PIPELINE-CTRL": {
        "status": "passed", "priority": "medium",
        "test_files": ["tests/gui/test_pipeline_controller.py"],
        "module_checks": ["python -m pytest tests/gui/test_pipeline_controller.py -q"],
        "wave": "python -m pytest tests/gui -q",
        "phase": "python -m pytest --ignore=tests/e2e -q",
        "evidence": "tests/gui/test_pipeline_controller.py: 12 passed (Stage 2 run). PipelineController routes commands deterministically.",
        "scenarios": [
            ("success", "PipelineController routes detect/export commands to the correct worker."),
            ("failure", "Controller suppresses duplicate commands while a pipeline is already running."),
        ],
        "assertions": [
            "PipelineController emits exactly one worker signal per accepted command.",
            "Concurrent commands are serialized, not dropped silently.",
        ],
    },
    "M-GUI-TIMELINE-CTRL": {
        "status": "passed", "priority": "medium",
        "test_files": ["tests/gui/test_timeline_controller.py"],
        "module_checks": ["python -m pytest tests/gui/test_timeline_controller.py -q"],
        "wave": "python -m pytest tests/gui -q",
        "phase": "python -m pytest --ignore=tests/e2e -q",
        "evidence": "tests/gui/test_timeline_controller.py: 14 passed (Stage 2 run). TimelineController maps model changes to view updates.",
        "scenarios": [
            ("success", "TimelineController maps slide model changes to view block updates."),
            ("failure", "Controller rejects out-of-range selection indices with a stable no-op."),
        ],
        "assertions": [
            "TimelineController produces deterministic block updates for canonical slide mutations.",
            "Selection state round-trips through the controller without drift.",
        ],
    },
    "M-DETECT-BENCHMARK": {
        "status": "passed", "priority": "medium",
        "test_files": ["tests/test_benchmark_provenance.py"],
        "module_checks": ["python -m pytest tests/test_benchmark_provenance.py -q"],
        "wave": "python -m pytest tests/test_benchmark_provenance.py tests/tools -q",
        "phase": "python -m pytest --ignore=tests/e2e -q",
        "evidence": "tests/test_benchmark_provenance.py: 14 passed (Stage 2 run). Benchmark provenance captured deterministically.",
        "scenarios": [
            ("success", "Benchmark provenance captures canonical inputs and outputs deterministically."),
            ("failure", "Benchmark with missing fixture raises a structured provenance error."),
        ],
        "assertions": [
            "Benchmark provenance round-trips canonical environment and command metadata.",
            "Benchmark output signature equals the committed accepted signature for the same inputs.",
        ],
    },
    "M-GITHUB-PROVIDER": {
        "status": "passed", "priority": "low",
        "test_files": ["tests/test_github_release_provider.py"],
        "module_checks": ["python -m pytest tests/test_github_release_provider.py -q"],
        "wave": "python -m pytest tests/test_github_release_provider.py tests/test_update_checker.py -q",
        "phase": "python -m pytest --ignore=tests/e2e -q",
        "evidence": "tests/test_github_release_provider.py: 11 passed (Stage 2 run). GitHubReleaseProvider handles mocked HTTP transport.",
        "scenarios": [
            ("success", "GitHubReleaseProvider fetches and parses release metadata over mocked HTTP."),
            ("failure", "Provider surfaces transport errors as a structured error without crashing."),
        ],
        "assertions": [
            "GitHubReleaseProvider returns deterministic release ordering for canonical responses.",
            "Network errors propagate as structured errors, not raw exceptions.",
        ],
    },
    # --- PLANNED (module status is planned; no implementation) ---
    "M-APP-LLM": {
        "status": "planned", "priority": "low",
        "test_files": [],
        "module_checks": [],
        "wave": "",
        "phase": "",
        "evidence": "",
        "scenarios": [
            ("success", "LlmEnrichmentService enriches slides via the LLM port (planned, not yet implemented)."),
            ("failure", "Service surfaces LLM port errors deterministically (planned)."),
        ],
        "assertions": [
            "LlmEnrichmentService contract is declared but not yet implemented; no test evidence claimed.",
        ],
    },
    "M-PORT-LLM": {
        "status": "planned", "priority": "low",
        "test_files": [],
        "module_checks": [],
        "wave": "",
        "phase": "",
        "evidence": "",
        "scenarios": [
            ("success", "LlmEnricherPort abstracts LLM enrichment calls (planned, not yet implemented)."),
            ("failure", "Port raises NotImplementedError for unimplemented enrichers (planned)."),
        ],
        "assertions": [
            "LlmEnricherPort is a declared abstract port; no runtime evidence claimed.",
        ],
    },
}


# Blocked modules: implemented/active without a dedicated passing test.
BLOCKED_MODULES = [
    ("M-ADAPTERS", "medium", "LegacyPortAdapters", "legacy adapter shim; no dedicated unit test isolating the adapter boundary"),
    ("M-APP-BUILD-META", "low", "BuildMeta", "build metadata module; no isolated test asserting canonical build identity fields"),
    ("M-APP-IDENTITY", "low", "ApplicationIdentity", "application identity module; no dedicated test asserting identity invariants"),
    ("M-APP-INPUT-RESOLVER", "low", "InputResolver", "input resolver on application/base; no dedicated test asserting resolution rules"),
    ("M-BACKEND-OPENCV", "medium", "OpenCVBackend", "OpenCV backend; no isolated test verifying decode contract without real video fixtures"),
    ("M-BACKEND-PYAV", "medium", "PyAVBackend", "PyAV backend; test_detection_metrics.py exercises it but 3 tests fail on codec_context (see F-0103, OPEN/NON_BLOCKING)"),
    ("M-DESKTOP-BOOTSTRAP", "low", "DesktopBootstrap", "desktop bootstrap; tests/test_bootstrap.py covers M-APP-BOOTSTRAP, not the desktop entry specifically"),
    ("M-DETECT-METRICS", "medium", "DetectMetrics", "test_detection_metrics.py has 3 pre-existing failures in the PyAV section (codec_context, F-0103); metrics core not isolated from backend failures"),
    ("M-DETECT-PERF-DECISION", "low", "BottleneckDecision", "bottleneck decision module backed by a JSON evidence artifact; no executable test asserting the decision boundary"),
    ("M-GUI-ABOUT", "low", "AboutDialog", "About dialog widget; no headless smoke test isolating dialog construction"),
    ("M-GUI-HELP-MENU", "low", "HelpMenu", "help menu is part of M-GUI-MENUBAR; no isolated test for the help submenu specifically"),
    ("M-GUI-PIPELINE-WORKER", "medium", "GuiPipelineWorker", "GUI pipeline worker; no isolated worker signal test"),
    ("M-GUI-UPDATE-CTRL", "low", "UpdateController", "update controller; no isolated test asserting update-check lifecycle"),
    ("M-GUI-WINDOW-UI", "low", "MainWindowUiBuilder", "main window UI builder; no isolated test asserting UI construction"),
    ("M-MCP-ADAPTER", "low", "McpServiceAdapter", "MCP service adapter in debug layer; no isolated test asserting adapter delegation"),
    ("M-MCP-COMPOSITION", "low", "McpComposition", "MCP composition root in debug layer; no isolated test asserting composition wiring"),
    ("M-PERSIST-DETECTION", "low", "DetectionConfigPersistence", "detection config persistence; tests/infra/test_persistence_dto.py targets M-PERSIST-DTO, not detection-config persistence specifically"),
    ("M-PORT-ALIGNMENT", "low", "AlignmentPort", "abstract alignment port; tested only transitively via concrete adapters, no port-isolated test"),
    ("M-PORT-DETECTOR", "low", "SlideDetectorPort", "abstract detector port; tested only transitively via concrete detectors, no port-isolated test"),
    ("M-PORT-EXPORT", "low", "PresentationExporterPort", "abstract exporter port; tested only transitively via concrete exporters, no port-isolated test"),
    ("M-PORT-NOTES", "low", "NotesProcessorPort", "abstract notes port; tested only transitively via notes_processor, no port-isolated test"),
    ("M-PORT-PREVIEW", "low", "PreviewAnalyzerPort", "abstract preview port; tested only transitively, no port-isolated test"),
]

for mid, prio, name, reason in BLOCKED_MODULES:
    DETAIL[mid] = {
        "status": "blocked", "priority": prio,
        "test_files": [],
        "module_checks": [],
        "wave": "",
        "phase": "",
        "evidence": "",
        "blocked_reason": reason,
        "scenarios": [
            ("success", f"{name} fulfills its declared contract when a dedicated test exists."),
            ("failure", f"{name} surfaces contract violations as structured errors."),
        ],
        "assertions": [
            f"BLOCKED: {reason}.",
            "No passed evidence claimed until a dedicated test exists and runs green.",
        ],
    }


def build_entry_xml(mid: str, d: dict) -> str:
    vid = "V-M-" + mid.split("-", 1)[1]
    status = d["status"]
    priority = d["priority"]
    lines = [f'    <{vid} MODULE="{mid}" PRIORITY="{priority}" STATUS="{status}">']

    if d["test_files"]:
        files = "".join(f"<file>{f}</file>" for f in d["test_files"])
        lines.append(f"      <test-files>{files}</test-files>")
    else:
        lines.append("      <test-files></test-files>")

    if d["module_checks"]:
        checks = "".join(f"<check-{i+1}>{c}</check-{i+1}>" for i, c in enumerate(d["module_checks"]))
        lines.append(f"      <module-checks>{checks}</module-checks>")

    if d["wave"]:
        lines.append(f"      <wave-follow-up>{esc(d['wave'])}</wave-follow-up>")
    if d["phase"]:
        lines.append(f"      <phase-follow-up>{esc(d['phase'])}</phase-follow-up>")

    if d["evidence"]:
        lines.append(f"      <evidence><result>{esc(d['evidence'])}</result></evidence>")
    elif status == "blocked":
        lines.append(f"      <blocked-reason>{esc(d.get('blocked_reason',''))}</blocked-reason>")

    # scenarios
    scen_lines = ["      <scenarios>"]
    for i, (kind, text) in enumerate(d["scenarios"], 1):
        scen_lines.append(f'        <scenario-{i} kind="{kind}">{esc(text)}</scenario-{i}>')
    scen_lines.append("      </scenarios>")
    lines.extend(scen_lines)

    # observable-evidence (trace assertions)
    asser_lines = ["      <required-trace-assertions>"]
    for i, a in enumerate(d["assertions"], 1):
        asser_lines.append(f"        <assertion>{esc(a)}</assertion>")
    asser_lines.append("      </required-trace-assertions>")
    lines.extend(asser_lines)

    lines.append(f"    </{vid}>")
    return "\n".join(lines)


entries_xml = [build_entry_xml(mid, d) for mid, d in DETAIL.items()]

text = VP_PATH.read_text(encoding="utf-8")

# Insert before </ModuleVerification>
mvm = re.search(r"</ModuleVerification>", text)
if not mvm:
    raise SystemExit("ModuleVerification close tag not found")

insert_block = "\n\n" + "\n\n".join(entries_xml) + "\n"
new_text = text[: mvm.start()] + insert_block + text[mvm.start():]
VP_PATH.write_text(new_text, encoding="utf-8")

passed = sum(1 for d in DETAIL.values() if d["status"] == "passed")
blocked = sum(1 for d in DETAIL.values() if d["status"] == "blocked")
planned = sum(1 for d in DETAIL.values() if d["status"] == "planned")
print(f"Added {len(DETAIL)} new V-M entries: {passed} passed, {blocked} blocked, {planned} planned.")
