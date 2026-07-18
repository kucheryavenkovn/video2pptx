"""Fix 11 verification entries that reference test files missing on disk.

HONESTY FIX:
- Entries with STATUS="passed" referencing missing tests: downgrade to
  STATUS="blocked" because the passed evidence is not reproducible. The
  acceptance criteria require that 'passed' only be assigned after a real
  successful run, and that all test file paths exist or the entry is honestly
  marked planned/blocked.
- Entries with STATUS="planned": update to point at a real related test file
  where one exists; otherwise keep the planned reference and let the linter
  flag it as an honest planned signal.

This does NOT fabricate test files. It only aligns STATUS with reproducible
evidence, per the Stage 2 core principle: STATUS follows evidence.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VP_PATH = ROOT / "docs" / "verification-plan.xml"

# (vid, action, new_test_files_or_None, blocked_reason_or_None)
FIXES = [
    # --- passed -> blocked (test file missing, evidence not reproducible) ---
    ("V-M-DEBUG-ACTION", "block", None,
     "Referenced test tests/test_debug_action.py does not exist on disk; prior 'passed' status was not reproducible. Module needs a dedicated debug-action test."),
    ("V-M-DEBUG-MCP", "block", None,
     "Referenced test tests/test_debug_action.py does not exist on disk; prior 'passed' status was not reproducible. Module needs a dedicated debug-mcp test."),
    ("V-M-GUI-TIMELINE", "block", ["tests/test_timeline_model.py"],
     "Referenced test tests/test_gui_timeline.py does not exist; prior 'passed' status was not reproducible. Related timeline_model test exists but does not isolate the GUI timeline widget contract."),
    ("V-M-GUI-TIMELINE-V2", "block", None,
     "Referenced test tests/test_gui_timeline_v2.py does not exist on disk; prior 'passed' status was not reproducible. V2 widget needs a dedicated test."),
    ("V-M-GUI-WORKER", "block", None,
     "Referenced test tests/test_gui_workers.py does not exist on disk; prior 'passed' status was not reproducible. GUI workers need a dedicated signal-emission test."),
    ("V-M-REF-CHAR-TESTS", "block", ["tests/test_cli_characterization.py", "tests/test_characterization_fixtures.py"],
     "Referenced test tests/test_characterization_adapters.py does not exist; prior 'passed' status was not reproducible. Related characterization tests exist but do not cover the adapters characterization contract."),
    # --- planned: point at real related test where one exists ---
    ("V-M-APP-SERVICE", "repoint", ["tests/test_app_service_runner.py"], None),
    ("V-M-CANONICAL-COMMANDS", "repoint", ["tests/test_app_service_runner.py"], None),
    ("V-M-E2E-SNAPSHOT", "repoint", ["tests/e2e/test_mcp_gui_workflow.py"], None),
    # planned entries with no related test: leave reference, status stays planned.
    ("V-M-GUI-CANONICAL-BUTTONS", "noop", None, None),
    ("V-M-MCP-RELIABILITY", "noop", None, None),
]


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


text = VP_PATH.read_text(encoding="utf-8")
report = []

for vid, action, new_tests, reason in FIXES:
    # match entry
    suffix = vid.split("-", 2)[2]
    pat = re.compile(r"(<" + re.escape(vid) + r"\b)([^>]*)(>)([\s\S]*?)(</" + re.escape(vid) + r">)")
    m = pat.search(text)
    if not m:
        report.append(f"WARN {vid}: not found")
        continue
    attrs = m.group(2)
    body = m.group(4)
    new_attrs = attrs
    new_body = body

    if action == "block":
        # change STATUS to blocked
        if 'STATUS="passed"' in new_attrs:
            new_attrs = new_attrs.replace('STATUS="passed"', 'STATUS="blocked"')
        elif 'STATUS="' in new_attrs:
            new_attrs = re.sub(r'STATUS="[^"]*"', 'STATUS="blocked"', new_attrs)
        # remove stale test-files block, replace with real ones if provided
        if new_tests:
            files_xml = "".join(f"<file>{t}</file>" for t in new_tests)
            new_body = re.sub(
                r"<test-files>[\s\S]*?</test-files>",
                f"<test-files>{files_xml}</test-files>",
                new_body,
            )
        # add/replace blocked-reason
        blocked_xml = f"<blocked-reason>{esc(reason)}</blocked-reason>"
        if "<blocked-reason>" in new_body:
            new_body = re.sub(r"<blocked-reason>[\s\S]*?</blocked-reason>", blocked_xml, new_body)
        else:
            # insert after open
            new_body = "\n      " + blocked_xml + new_body
    elif action == "repoint":
        if new_tests:
            files_xml = "".join(f"<file>{t}</file>" for t in new_tests)
            if "<test-files>" in new_body:
                new_body = re.sub(
                    r"<test-files>[\s\S]*?</test-files>",
                    f"<test-files>{files_xml}</test-files>",
                    new_body,
                )
            else:
                new_body = "\n      <test-files>" + files_xml + "</test-files>" + new_body
    elif action == "noop":
        pass

    new_entry = m.group(1) + new_attrs + m.group(3) + new_body + m.group(5)
    text = text[: m.start()] + new_entry + text[m.end():]
    report.append(f"OK {vid}: action={action}")

VP_PATH.write_text(text, encoding="utf-8")
for line in report:
    print(line)
