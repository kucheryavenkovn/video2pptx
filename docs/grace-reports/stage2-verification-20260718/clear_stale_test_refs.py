"""Clear stale test-files references that point to non-existent files AND have
no real related test to repoint to. The entry keeps its honest STATUS
(blocked/planned) and accepts the autonomy.verification-missing-test-files
blocker as an honest signal rather than referencing a phantom file.

Entries handled:
- V-M-DEBUG-ACTION (blocked): no dedicated debug-action test exists
- V-M-DEBUG-MCP (blocked): no dedicated debug-mcp test exists
- V-M-GUI-CANONICAL-BUTTONS (planned): canonical-buttons test not yet written
- V-M-GUI-TIMELINE-V2 (blocked): V2 test not yet written
- V-M-GUI-WORKER (blocked): GUI worker test not yet written
- V-M-MCP-RELIABILITY (planned): reliability test not yet written
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VP_PATH = ROOT / "docs" / "verification-plan.xml"

TARGETS = [
    "V-M-DEBUG-ACTION",
    "V-M-DEBUG-MCP",
    "V-M-GUI-CANONICAL-BUTTONS",
    "V-M-GUI-TIMELINE-V2",
    "V-M-GUI-WORKER",
    "V-M-MCP-RELIABILITY",
]

text = VP_PATH.read_text(encoding="utf-8")
report = []

for vid in TARGETS:
    pat = re.compile(r"(<" + re.escape(vid) + r"\b[^>]*>)([\s\S]*?)(</" + re.escape(vid) + r">)")
    m = pat.search(text)
    if not m:
        report.append(f"WARN {vid}: not found")
        continue
    open_tag, body, close_tag = m.group(1), m.group(2), m.group(3)
    # Replace test-files block content with empty
    new_body = re.sub(
        r"<test-files>[\s\S]*?</test-files>",
        "<test-files></test-files>",
        body,
    )
    # Remove module-checks that reference the phantom test file
    # (keep module-checks block but clear phantom references)
    if new_body != body:
        new_entry = open_tag + new_body + close_tag
        text = text[: m.start()] + new_entry + text[m.end():]
        report.append(f"OK {vid}: cleared stale test-files")
    else:
        report.append(f"NOOP {vid}: no test-files block")

VP_PATH.write_text(text, encoding="utf-8")
for line in report:
    print(line)
