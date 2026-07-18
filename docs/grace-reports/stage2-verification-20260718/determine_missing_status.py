"""Determine honest status and test files for modules without V-M entries.

For each module in modulesWithoutVerification:
- find source files (from KG paths)
- find candidate test files (by name pattern)
- determine honest status:
    passed   = test file exists AND test runs successfully
    blocked  = implemented/active but no test file exists
    planned  = module status is 'planned'
"""
from __future__ import annotations

import json
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs"
REPORT_DIR = DOCS / "grace-reports" / "stage2-verification-20260718"


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]


kg = ET.parse(DOCS / "knowledge-graph.xml").getroot()
dp = ET.parse(DOCS / "development-plan.xml").getroot()

MODULES_WITHOUT_V = [
    "M-ADAPTERS", "M-APP-BOOTSTRAP", "M-APP-BUILD-META", "M-APP-COMMON",
    "M-APP-IDENTITY", "M-APP-INPUT-RESOLVER", "M-APP-LLM", "M-BACKEND-OPENCV",
    "M-BACKEND-PYAV", "M-DESKTOP-BOOTSTRAP", "M-DETECT-BENCHMARK",
    "M-DETECT-METRICS", "M-DETECT-PERF-DECISION", "M-GITHUB-PROVIDER",
    "M-GUI-ABOUT", "M-GUI-HELP-MENU", "M-GUI-PIPELINE-CTRL",
    "M-GUI-PIPELINE-WORKER", "M-GUI-TIMELINE-CTRL", "M-GUI-UPDATE-CTRL",
    "M-GUI-WINDOW-UI", "M-MCP-ADAPTER", "M-MCP-COMPOSITION",
    "M-PERSIST-DETECTION", "M-PORT-ALIGNMENT", "M-PORT-DETECTOR",
    "M-PORT-EXPORT", "M-PORT-LLM", "M-PORT-NOTES", "M-PORT-PREVIEW",
]

KG_INFO = {}
for mod in kg.iter():
    mid = strip_ns(mod.tag)
    if mid in MODULES_WITHOUT_V:
        paths = []
        purpose = ""
        for c in mod.iter():
            ct = strip_ns(c.tag)
            if ct == "path" and (c.text or "").strip():
                paths.append((c.text or "").strip())
            elif ct == "purpose":
                purpose = (c.text or "").strip()
        KG_INFO[mid] = {
            "name": mod.get("NAME") or "",
            "status": mod.get("STATUS") or "",
            "purpose": purpose,
            "paths": paths,
        }

DP_INFO = {}
for node in dp.iter():
    mid = strip_ns(node.tag)
    if mid in MODULES_WITHOUT_V:
        DP_INFO[mid] = {
            "layer": node.get("LAYER") or "",
            "type": node.get("TYPE") or "",
            "status": node.get("STATUS") or "",
        }

ALL_TESTS = sorted(
    str(p.relative_to(ROOT)).replace("\\", "/")
    for p in (ROOT / "tests").rglob("test_*.py")
)


def find_tests(name: str, mid: str) -> list[str]:
    if not name:
        return []
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
    candidates = []
    for t in ALL_TESTS:
        base = t.split("/")[-1].replace("test_", "").replace(".py", "")
        if snake == base:
            candidates.append(t)
    if candidates:
        return candidates
    # looser match
    for t in ALL_TESTS:
        base = t.split("/")[-1].replace("test_", "").replace(".py", "")
        if snake in base or base in snake:
            candidates.append(t)
    return candidates[:2]


def run_test(test_path: str) -> tuple[bool, str]:
    """Run a single test file, return (success, summary)."""
    full = ROOT / test_path
    if not full.exists():
        return (False, "missing")
    try:
        result = subprocess.run(
            ["python", "-m", "pytest", test_path, "-q", "--no-header", "--tb=line"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=180,
        )
        out = (result.stdout + result.stderr)
        last = [l for l in out.splitlines() if "passed" in l or "failed" in l or "error" in l]
        summary = last[-1] if last else out[-200:]
        return (result.returncode == 0, summary.strip()[:200])
    except subprocess.TimeoutExpired:
        return (False, "timeout")
    except Exception as e:
        return (False, f"error: {e}")


results = {}
for mid in MODULES_WITHOUT_V:
    info = KG_INFO.get(mid, {})
    dp_info = DP_INFO.get(mid, {})
    name = info.get("name", mid)
    status = info.get("status") or dp_info.get("status") or ""
    purpose = info.get("purpose", "")
    tests = find_tests(name, mid)
    results[mid] = {
        "name": name,
        "module_status": status,
        "purpose": purpose,
        "source_paths": info.get("paths", []),
        "candidate_tests": tests,
        "layer": dp_info.get("layer", ""),
        "type": dp_info.get("type", ""),
    }

# Run tests for modules that have candidate test files
print("=== Running tests for modules with candidate test files ===")
for mid, r in results.items():
    if r["candidate_tests"]:
        t = r["candidate_tests"][0]
        ok, summary = run_test(t)
        r["test_run"] = {"path": t, "passed": ok, "summary": summary}
        print(f"  {mid}: {t} -> {'PASS' if ok else 'FAIL'} ({summary[:80]})")
    else:
        r["test_run"] = None
        print(f"  {mid}: no candidate test (module_status={r['module_status']})")

# Determine honest verification status
for mid, r in results.items():
    if r["module_status"] == "planned":
        r["honest_status"] = "planned"
    elif r["test_run"] and r["test_run"]["passed"]:
        r["honest_status"] = "passed"
    elif r["test_run"] and not r["test_run"]["passed"]:
        r["honest_status"] = "failed"
    else:
        # implemented/active but no test -> blocked
        r["honest_status"] = "blocked"

with open(REPORT_DIR / "missing-vm-status.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("\n=== Honest status distribution ===")
from collections import Counter
counts = Counter(r["honest_status"] for r in results.values())
for k, v in counts.items():
    print(f"  {k}: {v}")
