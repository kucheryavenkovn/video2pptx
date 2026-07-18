"""Stage 2 cleanup XML transformation (Reqs 2, 3, 4 + legacy-tag removal).

Applies in a single deterministic pass:
- Req 2: removes module-checks that reference missing/non-executable files
- Req 3: replaces unbounded `python -m pytest tests -q` wave-follow-up with
         a bounded surface derived from declared test-files (or explicit override)
- Req 4: replaces generic `<required-trace-assertions>` with concrete observable
         evidence from _cleanup_evidence.json
- Legacy: removes old `<wave-checks>` / `<phase-checks>` blocks (the new
  `<wave-follow-up>` / `<phase-follow-up>` already carry the bounded surface)
- Status: downgrades "passed" entries that lost executable evidence to "blocked",
          adds/replaces `<blocked-reason>`

Reads docs/verification-plan.xml as text, writes back in place.
Idempotent: running twice produces identical output.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs"
REPORT_DIR = DOCS / "grace-reports" / "stage2-verification-20260718"
VP = DOCS / "verification-plan.xml"

sys.path.insert(0, str(REPORT_DIR))
from _cleanup_decisions import (  # type: ignore[import-not-found]
    DOWNGRADE_TO_BLOCKED,
    EXPLICIT_BOUNDED_WAVE,
    REMOVE_ALL_MODULE_CHECKS,
)


DISK_TESTS: set[str] = set()
for p in (ROOT / "tests").rglob("test_*.py"):
    DISK_TESTS.add(str(p.relative_to(ROOT)).replace("\\", "/"))


def _path_exists(p: str) -> bool:
    if not p:
        return False
    if p.startswith("tests/"):
        return p in DISK_TESTS or (ROOT / p).exists()
    return (ROOT / p).exists()


# Load evidence replacement map
_EVIDENCE_RAW = json.loads((REPORT_DIR / "_cleanup_evidence.json").read_text(encoding="utf-8"))
EVIDENCE_REPLACE: dict[str, list[str]] = {
    k: v["new_assertions"]
    for k, v in _EVIDENCE_RAW.items()
    if v.get("action") == "replace"
}
EVIDENCE_INSUFFICIENT: set[str] = {
    k for k, v in _EVIDENCE_RAW.items() if v.get("action") == "insufficient"
}

# Entries that should be downgraded to blocked because evidence was insufficient
# (in addition to those already in DOWNGRADE_TO_BLOCKED).
for _vid in list(EVIDENCE_INSUFFICIENT):
    DOWNGRADE_TO_BLOCKED.setdefault(
        _vid,
        (
            "Prior 'passed' status relied on a test file that does not assert "
            "the declared contract. STATUS downgraded to blocked until a "
            "dedicated reproducible test is created (NO_EXECUTABLE_EVIDENCE)."
        ),
    )


def derive_bounded_wave(vid: str, declared_test_files: list[str]) -> str:
    """Return bounded pytest command, or '' if no bounded surface exists."""
    if vid in EXPLICIT_BOUNDED_WAVE:
        return EXPLICIT_BOUNDED_WAVE[vid]
    existing = [t for t in declared_test_files if t.startswith("tests/") and _path_exists(t)]
    if existing:
        return "python -m pytest " + " ".join(existing) + " -q"
    return ""


VMBLOCK_RE = re.compile(
    r"(<V-M-[A-Z0-9-]+\b[^>]*>)(.*?)(</V-M-[A-Z0-9-]+>)",
    re.DOTALL,
)


def parse_opening_attr(opening_tag: str, attr: str) -> str:
    m = re.search(rf'\b{attr}="([^"]*)"', opening_tag)
    return m.group(1) if m else ""


def vm_name(opening_tag: str) -> str:
    m = re.match(r"<(V-M-[A-Z0-9-]+)\b", opening_tag)
    return m.group(1) if m else ""


def remove_child_block(body: str, tagname: str) -> str:
    """Remove `<tagname ...>...</tagname>` plus surrounding whitespace line."""
    pattern = re.compile(
        r"^[ \t]*<" + tagname + r"\b[^>]*>.*?</" + tagname + r">[ \t]*\r?\n?",
        re.DOTALL | re.MULTILINE,
    )
    return pattern.sub("", body, count=1)


def find_child_block(body: str, tagname: str) -> str | None:
    pattern = re.compile(
        r"^[ \t]*<" + tagname + r"\b[^>]*>.*?</" + tagname + r">[ \t]*\r?\n?",
        re.DOTALL | re.MULTILINE,
    )
    m = pattern.search(body)
    if m:
        return m.group(0)
    return None


def extract_test_files(body: str) -> list[str]:
    m = re.search(r"<test-files\b[^>]*>(.*?)</test-files>", body, re.DOTALL)
    if not m:
        return []
    files: list[str] = []
    for fm in re.finditer(r"<file>([^<]+)</file>", m.group(1)):
        files.append(fm.group(1).strip())
    return files


def replace_wave_followup(body: str, new_value: str) -> str:
    return re.sub(
        r"(<wave-follow-up>)(.*?)(</wave-follow-up>)",
        lambda m: m.group(1) + new_value + m.group(3),
        body,
        count=1,
        flags=re.DOTALL,
    )


def replace_phase_followup(body: str, new_value: str) -> str:
    return re.sub(
        r"(<phase-follow-up>)(.*?)(</phase-follow-up>)",
        lambda m: m.group(1) + new_value + m.group(3),
        body,
        count=1,
        flags=re.DOTALL,
    )


def replace_required_trace_assertions(body: str, assertions: list[str]) -> str:
    """Replace the entire <required-trace-assertions>...</required-trace-assertions>
    block content with new <assertion> children."""
    inner = "".join(f"<assertion>{a}</assertion>" for a in assertions)
    new_block = f"<required-trace-assertions>{inner}</required-trace-assertions>"
    return re.sub(
        r"<required-trace-assertions>.*?</required-trace-assertions>",
        lambda m: new_block,
        body,
        count=1,
        flags=re.DOTALL,
    )


def update_opening_status(opening_tag: str, new_status: str) -> str:
    return re.sub(
        r'\bSTATUS="[^"]*"',
        f'STATUS="{new_status}"',
        opening_tag,
        count=1,
    )


def add_or_replace_blocked_reason(body: str, reason: str, indent: str = "    ") -> str:
    if re.search(r"<blocked-reason>", body):
        return re.sub(
            r"(<blocked-reason>)(.*?)(</blocked-reason>)",
            lambda m: m.group(1) + reason + m.group(3),
            body,
            count=1,
            flags=re.DOTALL,
        )
    return body + f"\n{indent}<blocked-reason>{reason}</blocked-reason>"


def transform_block(opening_tag: str, body: str, closing_tag: str) -> tuple[str, str, str]:
    vid = vm_name(opening_tag)

    # Detect existing leading indent of children (use first non-empty line)
    base_indent = "      "
    for line in body.splitlines():
        if line.strip():
            m = re.match(r"^([ \t]+)\S", line)
            if m:
                base_indent = m.group(1)
                break

    # 1) Remove legacy <wave-checks> / <phase-checks> (single block each)
    body = remove_child_block(body, "wave-checks")
    body = remove_child_block(body, "phase-checks")

    # 2) Optionally remove all module-checks (Req 2)
    remove_module_checks_reason = REMOVE_ALL_MODULE_CHECKS.get(vid)
    if remove_module_checks_reason is not None:
        body = remove_child_block(body, "module-checks")

    # 3) Update wave-follow-up with bounded surface
    declared = extract_test_files(body)
    if "<wave-follow-up>" in body:
        new_wave = derive_bounded_wave(vid, declared)
        body = replace_wave_followup(body, new_wave)
    else:
        # Some entries (very few) might not have wave-follow-up; add it
        new_wave = derive_bounded_wave(vid, declared)
        body = body + f"\n{base_indent}<wave-follow-up>{new_wave}</wave-follow-up>"

    # Ensure phase-follow-up stays bounded to non-E2E; if it's the old
    # unbounded form replace it too (rare).
    if "<phase-follow-up>" in body:
        # Keep existing phase-follow-up unless it equals the unbounded form
        m = re.search(r"<phase-follow-up>(.*?)</phase-follow-up>", body, re.DOTALL)
        if m and m.group(1).strip() in {
            "python -m pytest tests -q",
            "pytest tests -q",
        }:
            body = replace_phase_followup(body, "python -m pytest --ignore=tests/e2e -q")

    # 4) Replace required-trace-assertions if concrete evidence is provided
    if vid in EVIDENCE_REPLACE and "<required-trace-assertions>" in body:
        body = replace_required_trace_assertions(body, EVIDENCE_REPLACE[vid])

    # 5) Status downgrade + blocked-reason
    if vid in DOWNGRADE_TO_BLOCKED:
        opening_tag = update_opening_status(opening_tag, "blocked")
        body = add_or_replace_blocked_reason(
            body, DOWNGRADE_TO_BLOCKED[vid], indent=base_indent
        )
    elif remove_module_checks_reason is not None:
        # Update existing blocked-reason or add new for entries that already had
        # STATUS=blocked (do NOT change status here).
        current_status = parse_opening_attr(opening_tag, "STATUS")
        if current_status == "blocked":
            body = add_or_replace_blocked_reason(
                body, remove_module_checks_reason, indent=base_indent
            )

    return opening_tag, body, closing_tag


def main() -> None:
    text = VP.read_text(encoding="utf-8")

    stats = {
        "blocks_processed": 0,
        "wave_bounded": 0,
        "wave_empty": 0,
        "module_checks_removed": 0,
        "downgraded": 0,
        "evidence_replaced": 0,
        "legacy_tags_removed": 0,
    }

    def repl(m: re.Match[str]) -> str:
        opening, body, closing = m.group(1), m.group(2), m.group(3)
        vid = vm_name(opening)
        if not vid:
            return m.group(0)

        # Track stats before/after
        had_module_checks = "<module-checks>" in body
        had_legacy = ("<wave-checks>" in body) or ("<phase-checks>" in body)

        prev_wave_match = re.search(
            r"<wave-follow-up>(.*?)</wave-follow-up>", body, re.DOTALL
        )
        prev_wave = prev_wave_match.group(1).strip() if prev_wave_match else ""
        prev_status = parse_opening_attr(opening, "STATUS")

        opening, body, closing = transform_block(opening, body, closing)

        stats["blocks_processed"] += 1
        if had_module_checks and "<module-checks>" not in body:
            stats["module_checks_removed"] += 1
        if had_legacy and ("<wave-checks>" not in body) and ("<phase-checks>" not in body):
            stats["legacy_tags_removed"] += 1

        new_wave_match = re.search(
            r"<wave-follow-up>(.*?)</wave-follow-up>", body, re.DOTALL
        )
        new_wave = new_wave_match.group(1).strip() if new_wave_match else ""
        if new_wave:
            stats["wave_bounded"] += 1
        else:
            stats["wave_empty"] += 1

        if vid in EVIDENCE_REPLACE:
            stats["evidence_replaced"] += 1
        if vid in DOWNGRADE_TO_BLOCKED and prev_status != "blocked":
            stats["downgraded"] += 1

        return opening + body + closing

    new_text = VMBLOCK_RE.sub(repl, text)

    VP.write_text(new_text, encoding="utf-8")
    print("Stage 2 cleanup XML transformation complete.")
    print(f"  Blocks processed:        {stats['blocks_processed']}")
    print(f"  Module-checks removed:   {stats['module_checks_removed']}")
    print(f"  Legacy tags removed:     {stats['legacy_tags_removed']}")
    print(f"  Wave bounded:            {stats['wave_bounded']}")
    print(f"  Wave empty (no surface): {stats['wave_empty']}")
    print(f"  Evidence replaced:       {stats['evidence_replaced']}")
    print(f"  Downgraded passed→blocked: {stats['downgraded']}")


if __name__ == "__main__":
    main()
