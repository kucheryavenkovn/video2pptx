"""Augment the 24 blocked/planned V-M entries with honest follow-ups.

Rules:
- wave-follow-up and phase-follow-up are added where missing (they describe the
  intended gate, not fake evidence). STATUS stays blocked/planned.
- test-files and module-checks reference ONLY real existing test files.
  Where no related test exists, the entry keeps empty test-files and accepts the
  autonomy.verification-missing-test-files blocker as an honest signal.
- module-checks reference the real test path or its directory.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VP_PATH = ROOT / "docs" / "verification-plan.xml"
TESTS = ROOT / "tests"

# Map blocked/planned module -> (intended test file if it exists on disk, intended module-check dir)
RELATED = {
    "M-BACKEND-PYAV": ("tests/test_detection_metrics.py", "tests/test_detection_metrics.py"),
    "M-DETECT-METRICS": ("tests/test_detection_metrics.py", "tests/test_detection_metrics.py"),
    "M-DETECT-PERF-DECISION": ("", "tests/tools"),
    "M-DESKTOP-BOOTSTRAP": ("tests/test_bootstrap.py", "tests/test_bootstrap.py"),
    "M-GUI-HELP-MENU": ("tests/test_gui_menu_bar.py", "tests/test_gui_menu_bar.py"),
    "M-PERSIST-DETECTION": ("tests/infra/test_persistence_dto.py", "tests/infra/test_persistence_dto.py"),
    "M-PORT-DETECTOR": ("tests/test_slide_detector.py", "tests/test_slide_detector.py"),
    "M-PORT-NOTES": ("tests/test_notes_processor.py", "tests/test_notes_processor.py"),
    "M-PORT-ALIGNMENT": ("tests/application/test_alignment_service.py", "tests/application/test_alignment_service.py"),
    "M-PORT-EXPORT": ("tests/application/test_export_service.py", "tests/application/test_export_service.py"),
    "M-PORT-PREVIEW": ("tests/application/test_preview_service.py", "tests/application/test_preview_service.py"),
    "M-GUI-PIPELINE-WORKER": ("tests/gui/test_pipeline_controller.py", "tests/gui"),
    "M-GUI-UPDATE-CTRL": ("tests/test_update_checker.py", "tests/test_update_checker.py"),
}

# Entries to update (the 24 blocked/planned ones)
TARGETS = [
    "M-ADAPTERS", "M-APP-BUILD-META", "M-APP-IDENTITY", "M-APP-INPUT-RESOLVER",
    "M-APP-LLM", "M-BACKEND-OPENCV", "M-BACKEND-PYAV", "M-DESKTOP-BOOTSTRAP",
    "M-DETECT-METRICS", "M-DETECT-PERF-DECISION", "M-GUI-ABOUT", "M-GUI-HELP-MENU",
    "M-GUI-PIPELINE-WORKER", "M-GUI-UPDATE-CTRL", "M-GUI-WINDOW-UI", "M-MCP-ADAPTER",
    "M-MCP-COMPOSITION", "M-PERSIST-DETECTION", "M-PORT-ALIGNMENT", "M-PORT-DETECTOR",
    "M-PORT-EXPORT", "M-PORT-LLM", "M-PORT-NOTES", "M-PORT-PREVIEW",
]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def posix(p: str) -> str:
    return p.replace("\\", "/")


text = VP_PATH.read_text(encoding="utf-8")
updated = 0

for mid in TARGETS:
    # match the entry
    pat = re.compile(
        r"(<V-M-" + re.escape(mid.split("-", 1)[1]) + r"\b[^>]*>)([\s\S]*?)(</V-M-" + re.escape(mid.split("-", 1)[1]) + r">)"
    )
    m = pat.search(text)
    if not m:
        print(f"WARN: {mid} entry not found")
        continue
    open_tag, body, close_tag = m.group(1), m.group(2), m.group(3)
    additions = []

    rel_test, check_target = RELATED.get(mid, ("", ""))
    if rel_test:
        rel_path = ROOT / rel_test
        if rel_path.exists():
            if "<file>" not in body:
                additions.append(f"      <test-files><file>{rel_test}</file></test-files>")

    if not re.search(r"<module-checks>", body):
        if check_target:
            additions.append(
                f"      <module-checks><check-1>python -m pytest {check_target} -q</check-1></module-checks>"
            )

    if not re.search(r"<wave-follow-up>", body):
        # use the tests directory of the related test, else tests/
        if rel_test:
            parts = rel_test.split("/")
            wdir = "/".join(parts[:2]) if len(parts) > 2 else "tests"
        else:
            wdir = "tests"
        additions.append(f"      <wave-follow-up>python -m pytest {wdir} -q</wave-follow-up>")

    if not re.search(r"<phase-follow-up>", body):
        additions.append(f"      <phase-follow-up>python -m pytest --ignore=tests/e2e -q</phase-follow-up>")

    if not additions:
        continue

    # insert before the closing tag region: place after last existing child
    new_body = body.rstrip()
    if not new_body.endswith("\n"):
        new_body += "\n"
    new_body += "\n".join(additions) + "\n    "
    new_entry = open_tag + new_body + close_tag
    text = text[: m.start()] + new_entry + text[m.end():]
    updated += 1

VP_PATH.write_text(text, encoding="utf-8")
print(f"Updated {updated} blocked/planned entries with honest follow-ups.")
