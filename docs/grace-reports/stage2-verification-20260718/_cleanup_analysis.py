"""Stage 2 cleanup analysis (read-only).

Parses docs/verification-plan.xml and emits per-entry structured data:
- status, declared test-files + existence on disk
- declared module-checks + extracted pytest paths + which don't exist
- wave-follow-up + whether it equals the unbounded `python -m pytest tests -q`
- phase-follow-up
- whether entry uses legacy <wave-checks>/<phase-checks>

Outputs:
- _cleanup_analysis.json (full per-entry data)
- _cleanup_broken_module_checks.json
- _cleanup_unbounded_wave.json
- _cleanup_legacy_tags.json
"""
from __future__ import annotations

import json
import re
import shlex
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs"
REPORT_DIR = DOCS / "grace-reports" / "stage2-verification-20260718"
VP = DOCS / "verification-plan.xml"


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]


def collect_disk_tests() -> set[str]:
    s: set[str] = set()
    for p in (ROOT / "tests").rglob("test_*.py"):
        s.add(str(p.relative_to(ROOT)).replace("\\", "/"))
    return s


DISK_TESTS = collect_disk_tests()


def path_exists(p: str) -> bool:
    if not p:
        return False
    if p.startswith("tests/"):
        return p in DISK_TESTS or (ROOT / p).exists()
    return (ROOT / p).exists()


def extract_pytest_paths(command: str) -> list[str]:
    """Extract file/dir arguments from a pytest command line."""
    if not command:
        return []
    # strip env prefixes / && chains — focus on the pytest half
    parts = re.split(r"(?:&&|\|\||;)", command)
    paths: list[str] = []
    for part in parts:
        part = part.strip()
        # find 'pytest' or 'python -m pytest' start
        m = re.search(r"(?:python\s+-m\s+)?pytest\s+(.*)", part)
        if not m:
            continue
        rest = m.group(1).strip()
        try:
            tokens = shlex.split(rest, posix=True)
        except ValueError:
            tokens = rest.split()
        for t in tokens:
            if t.startswith("-"):
                continue
            # strip trailing quotes
            t = t.strip("'\"")
            if not t:
                continue
            # ignore pytest options with values like --ignore=...
            if "=" in t and t.startswith("--"):
                continue
            paths.append(t)
    return paths


def classify_wave(cmd: str) -> str:
    if not cmd:
        return "empty"
    s = cmd.strip()
    if s == "python -m pytest tests -q":
        return "unbounded_tests"
    if s == "pytest tests -q":
        return "unbounded_tests"
    return "bounded"


def main() -> None:
    root = ET.parse(VP).getroot()
    entries: list[dict] = []
    legacy_tag_entries: list[str] = []
    broken_module_checks: list[dict] = []
    unbounded_wave: list[dict] = []

    # iterate over <V-M-...> elements anywhere under root
    for node in root.iter():
        tag = strip_ns(node.tag)
        if not (tag.startswith("V-M-") and len(tag) > 4 and tag[4] != "-"):
            # still accept V-M-... even if pattern stricter
            pass
        if not tag.startswith("V-M-"):
            continue
        vid = tag
        module = node.get("MODULE") or ""
        status = node.get("STATUS") or ""
        priority = node.get("PRIORITY") or ""

        test_files: list[str] = []
        module_checks: list[str] = []
        wave_checks: list[str] = []
        phase_checks: list[str] = []
        wave_follow_up = ""
        phase_follow_up = ""
        trace_assertions: list[str] = []
        blocked_reason = ""
        has_wave_checks_tag = False
        has_phase_checks_tag = False
        has_module_checks_tag = False

        for child in node:
            ctag = strip_ns(child.tag)
            if ctag == "test-files":
                for f in child:
                    if (f.text or "").strip():
                        test_files.append((f.text or "").strip())
            elif ctag == "module-checks":
                has_module_checks_tag = True
                for c in child:
                    if (c.text or "").strip():
                        module_checks.append((c.text or "").strip())
            elif ctag == "wave-checks":
                has_wave_checks_tag = True
                for c in child:
                    if (c.text or "").strip():
                        wave_checks.append((c.text or "").strip())
            elif ctag == "phase-checks":
                has_phase_checks_tag = True
                for c in child:
                    if (c.text or "").strip():
                        phase_checks.append((c.text or "").strip())
            elif ctag == "wave-follow-up":
                wave_follow_up = (child.text or "").strip()
            elif ctag == "phase-follow-up":
                phase_follow_up = (child.text or "").strip()
            elif ctag == "required-trace-assertions":
                for a in child:
                    if (a.text or "").strip():
                        trace_assertions.append((a.text or "").strip())
            elif ctag == "blocked-reason":
                blocked_reason = (child.text or "").strip()

        if has_wave_checks_tag or has_phase_checks_tag:
            legacy_tag_entries.append(vid)

        # check module-check paths
        broken_checks: list[dict] = []
        for idx, cmd in enumerate(module_checks, 1):
            paths = extract_pytest_paths(cmd)
            missing = [p for p in paths if not path_exists(p)]
            if missing:
                broken_checks.append({"index": idx, "command": cmd, "missing": missing})
                broken_module_checks.append({
                    "vid": vid,
                    "module": module,
                    "status": status,
                    "index": idx,
                    "command": cmd,
                    "missing": missing,
                })

        # check declared test-files existence
        test_files_missing = [t for t in test_files if not path_exists(t)]

        wcls = classify_wave(wave_follow_up)
        if wcls == "unbounded_tests":
            unbounded_wave.append({
                "vid": vid,
                "module": module,
                "status": status,
                "test_files": test_files,
                "test_files_existing": [t for t in test_files if t not in test_files_missing],
                "test_files_missing": test_files_missing,
                "module_checks": module_checks,
                "current_wave": wave_follow_up,
            })

        entries.append({
            "vid": vid,
            "module": module,
            "status": status,
            "priority": priority,
            "test_files": test_files,
            "test_files_missing": test_files_missing,
            "module_checks": module_checks,
            "module_checks_broken": broken_checks,
            "wave_checks_legacy": wave_checks,
            "phase_checks_legacy": phase_checks,
            "has_wave_checks_tag": has_wave_checks_tag,
            "has_phase_checks_tag": has_phase_checks_tag,
            "has_module_checks_tag": has_module_checks_tag,
            "wave_follow_up": wave_follow_up,
            "wave_follow_up_class": wcls,
            "phase_follow_up": phase_follow_up,
            "trace_assertions": trace_assertions,
            "blocked_reason": blocked_reason,
        })

    out = {
        "total_entries": len(entries),
        "status_counts": {
            "passed": sum(1 for e in entries if e["status"] == "passed"),
            "blocked": sum(1 for e in entries if e["status"] == "blocked"),
            "planned": sum(1 for e in entries if e["status"] == "planned"),
            "failed": sum(1 for e in entries if e["status"] == "failed"),
            "in_progress": sum(1 for e in entries if e["status"] == "in_progress"),
        },
        "legacy_tag_entry_count": len(legacy_tag_entries),
        "legacy_tag_entries": legacy_tag_entries,
        "broken_module_check_count": len(broken_module_checks),
        "unbounded_wave_count": len(unbounded_wave),
        "entries": entries,
    }
    (REPORT_DIR / "_cleanup_analysis.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (REPORT_DIR / "_cleanup_broken_module_checks.json").write_text(
        json.dumps(broken_module_checks, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (REPORT_DIR / "_cleanup_unbounded_wave.json").write_text(
        json.dumps(unbounded_wave, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (REPORT_DIR / "_cleanup_legacy_tags.json").write_text(
        json.dumps({
            "count": len(legacy_tag_entries),
            "entries": legacy_tag_entries,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Total entries: {out['total_entries']}")
    print(f"Status counts: {out['status_counts']}")
    print(f"Legacy tag entries: {out['legacy_tag_entry_count']}")
    print(f"Broken module-checks: {out['broken_module_check_count']}")
    print(f"Unbounded wave-follow-up: {out['unbounded_wave_count']}")


if __name__ == "__main__":
    main()
