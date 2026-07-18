"""Build module coverage map for Stage 2 verification coverage analysis.

Reads:
- docs/knowledge-graph.xml
- docs/development-plan.xml
- docs/verification-plan.xml (current tags: module-checks, wave-follow-up,
  phase-follow-up, required-trace-assertions, test-files)
- final-autonomy.json (NOT baseline)
- final-status.json (NOT baseline)
- tests/ directory

Writes:
- module-coverage.json
- module-coverage.md

Output metrics are computed dynamically from the actual verification plan +
final autonomy/status reports, never from baseline. No hardcoding.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs"
REPORT_DIR = DOCS / "grace-reports" / "stage2-verification-20260718"


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]


def load_xml(path: Path) -> ET.Element:
    return ET.parse(path).getroot()


# --- Load knowledge graph modules ---
kg = load_xml(DOCS / "knowledge-graph.xml")
kg_modules: dict[str, dict] = {}
for mod in kg.iter():
    if not (strip_ns(mod.tag).startswith("M-")):
        continue
    mid = strip_ns(mod.tag)
    if not re.fullmatch(r"M-[A-Z0-9-]+", mid):
        continue
    kg_modules[mid] = {
        "id": mid,
        "name": mod.get("NAME") or mod.get("name") or "",
        "status": mod.get("STATUS") or mod.get("status") or "",
        "type": mod.get("TYPE") or "",
        "paths": [],
    }
    for child in mod.iter():
        ctag = strip_ns(child.tag)
        if ctag in {"path", "Path"}:
            txt = (child.text or "").strip()
            if txt:
                kg_modules[mid]["paths"].append(txt)


# --- Load development plan modules ---
dp = load_xml(DOCS / "development-plan.xml")
dp_modules: dict[str, dict] = {}
for node in dp.iter():
    mid = strip_ns(node.tag)
    if not (mid.startswith("M-") and re.fullmatch(r"M-[A-Z0-9-]+", mid)):
        continue
    dp_modules[mid] = {
        "status": node.get("STATUS") or "",
        "layer": node.get("LAYER") or "",
        "type": node.get("TYPE") or "",
        "order": node.get("ORDER") or "",
    }


# --- Load verification plan V-M entries (current canonical tags only) ---
vp = load_xml(DOCS / "verification-plan.xml")
vm_entries: dict[str, dict] = {}
for node in vp.iter():
    tag = strip_ns(node.tag)
    if not tag.startswith("V-M-"):
        continue
    vid = tag
    mid = node.get("MODULE") or ""
    entry = {
        "id": vid,
        "module": mid,
        "priority": node.get("PRIORITY") or "",
        "status": node.get("STATUS") or "",
        "has_test_files": False,
        "has_module_checks": False,
        "has_wave_follow_up": False,
        "has_phase_follow_up": False,
        "has_scenarios": False,
        "has_required_trace_assertions": False,
        "has_blocked_reason": False,
        "test_files": [],
        "module_checks": [],
        "wave_follow_up": [],
        "phase_follow_up": [],
        "scenarios": [],
        "required_trace_assertions": [],
        "blocked_reason": "",
    }
    for child in node:
        ctag = strip_ns(child.tag)
        if ctag == "test-files":
            entry["has_test_files"] = True
            for f in child:
                if (f.text or "").strip():
                    entry["test_files"].append((f.text or "").strip())
        elif ctag == "module-checks":
            entry["has_module_checks"] = True
            for c in child:
                if (c.text or "").strip():
                    entry["module_checks"].append((c.text or "").strip())
        elif ctag == "wave-follow-up":
            entry["has_wave_follow_up"] = True
            if (child.text or "").strip():
                entry["wave_follow_up"].append((child.text or "").strip())
        elif ctag == "phase-follow-up":
            entry["has_phase_follow_up"] = True
            if (child.text or "").strip():
                entry["phase_follow_up"].append((child.text or "").strip())
        elif ctag == "scenarios":
            entry["has_scenarios"] = True
            for s in child:
                if (s.text or "").strip():
                    entry["scenarios"].append((s.text or "").strip())
        elif ctag == "required-trace-assertions":
            entry["has_required_trace_assertions"] = True
            for a in child:
                if (a.text or "").strip():
                    entry["required_trace_assertions"].append((a.text or "").strip())
        elif ctag == "blocked-reason":
            entry["has_blocked_reason"] = True
            entry["blocked_reason"] = (child.text or "").strip()
    vm_entries[vid] = entry


# --- Map module -> V-M entry ---
module_to_vm: dict[str, str] = {}
for vid, entry in vm_entries.items():
    module_to_vm[entry["module"]] = vid


# --- Load final autonomy lint issues for per-module/per-entry signals ---
with open(REPORT_DIR / "final-autonomy.json", "r", encoding="utf-8") as f:
    auto = json.load(f)

autonomy_by_code: dict[str, list] = {}
for issue in auto.get("issues", []):
    code = issue.get("code", "")
    autonomy_by_code.setdefault(code, []).append(issue)


def extract_module_from_msg(msg: str) -> str | None:
    m = re.search(r"Module\s+`(M-[A-Z0-9-]+)`", msg)
    return m.group(1) if m else None


def extract_vm_from_msg(msg: str) -> str | None:
    m = re.search(r"`(V-M-[A-Z0-9-]+)`", msg)
    return m.group(1) if m else None


# --- Collect test files on disk ---
test_files_on_disk: set[str] = set()
for p in (ROOT / "tests").rglob("test_*.py"):
    test_files_on_disk.add(str(p.relative_to(ROOT)).replace("\\", "/"))


# --- Build per-module coverage records ---
all_module_ids = sorted(set(kg_modules.keys()) | set(dp_modules.keys()))
coverage = []
for mid in all_module_ids:
    kgm = kg_modules.get(mid, {})
    dpm = dp_modules.get(mid, {})
    vid = module_to_vm.get(mid, "")
    vm = vm_entries.get(vid, None)
    status = kgm.get("status") or dpm.get("status") or ""
    paths = kgm.get("paths", [])
    source_paths = [p for p in paths if "test" not in p.lower().split("/")[-1]]
    test_paths_decl = list(vm["test_files"]) if vm else []
    test_paths_existing = [
        t for t in test_paths_decl if (ROOT / t).exists() or t in test_files_on_disk
    ]
    test_paths_missing = [t for t in test_paths_decl if t not in test_paths_existing]

    obs_evidence = bool(
        vm and vm["has_required_trace_assertions"] and vm["required_trace_assertions"]
    )

    # autonomy signals for this module
    mod_missing_verif = any(
        extract_module_from_msg(i.get("message", "")) == mid
        for i in autonomy_by_code.get("autonomy.module-missing-verification", [])
    )

    vm_missing_wave = False
    vm_missing_phase = False
    vm_missing_obs = False
    vm_missing_scen = False
    vm_missing_mod_checks = False
    vm_test_missing_disk = False
    vm_mod_check_no_ref = False
    if vm:
        vm_missing_wave = any(
            extract_vm_from_msg(i.get("message", "")) == vid
            for i in autonomy_by_code.get("autonomy.verification-missing-wave-follow-up", [])
        )
        vm_missing_phase = any(
            extract_vm_from_msg(i.get("message", "")) == vid
            for i in autonomy_by_code.get("autonomy.verification-missing-phase-follow-up", [])
        )
        vm_missing_obs = any(
            extract_vm_from_msg(i.get("message", "")) == vid
            for i in autonomy_by_code.get("autonomy.verification-missing-observable-evidence", [])
        )
        vm_missing_scen = any(
            extract_vm_from_msg(i.get("message", "")) == vid
            for i in autonomy_by_code.get("autonomy.verification-missing-scenarios", [])
        )
        vm_missing_mod_checks = any(
            extract_vm_from_msg(i.get("message", "")) == vid
            for i in autonomy_by_code.get("autonomy.verification-missing-module-checks", [])
        )
        vm_test_missing_disk = any(
            extract_vm_from_msg(i.get("message", "")) == vid
            for i in autonomy_by_code.get("autonomy.verification-test-file-missing-on-disk", [])
        )
        vm_mod_check_no_ref = any(
            extract_vm_from_msg(i.get("message", "")) == vid
            for i in autonomy_by_code.get("autonomy.verification-module-check-does-not-reference-test-file", [])
        )

    # classification
    if not vm:
        classification = "MISSING_VERIFICATION_ENTRY"
    elif vm["status"] == "passed":
        classification = "VERIFIED_PASSED"
    elif vm["status"] == "failed":
        classification = "VERIFIED_FAILED"
    elif vm["status"] == "blocked":
        classification = "VERIFICATION_BLOCKED"
    elif vm["status"] == "planned":
        classification = "VERIFICATION_PLANNED"
    elif vm["status"] == "in_progress":
        classification = "VERIFICATION_IN_PROGRESS"
    else:
        classification = "NO_EXECUTABLE_EVIDENCE"

    coverage.append({
        "module-id": mid,
        "module-status": status,
        "module-name": kgm.get("name", ""),
        "phase": dpm.get("layer", ""),
        "source-paths": source_paths,
        "test-paths": test_paths_decl,
        "test-paths-existing": test_paths_existing,
        "test-paths-missing": test_paths_missing,
        "verification-id": vid,
        "verification-entry-exists": bool(vm),
        "verification-status": vm["status"] if vm else "",
        "verification-priority": vm["priority"] if vm else "",
        "has-module-checks": bool(vm and vm["has_module_checks"]) if vm else False,
        "has-wave-follow-up": bool(vm and vm["has_wave_follow_up"] and vm["wave_follow_up"]) if vm else False,
        "has-phase-follow-up": bool(vm and vm["has_phase_follow_up"] and vm["phase_follow_up"]) if vm else False,
        "has-scenarios": bool(vm and vm["has_scenarios"]) if vm else False,
        "observable-evidence-defined": obs_evidence,
        "has-blocked-reason": bool(vm and vm["has_blocked_reason"]) if vm else False,
        "autonomy_signals": {
            "module-missing-verification": mod_missing_verif,
            "vm-missing-wave-follow-up": vm_missing_wave,
            "vm-missing-phase-follow-up": vm_missing_phase,
            "vm-missing-observable-evidence": vm_missing_obs,
            "vm-missing-scenarios": vm_missing_scen,
            "vm-missing-module-checks": vm_missing_mod_checks,
            "vm-test-file-missing-on-disk": vm_test_missing_disk,
            "vm-module-check-no-test-ref": vm_mod_check_no_ref,
        },
        "coverage-classification": classification,
    })


# --- Aggregate metrics ---
cls_counts = Counter(c["coverage-classification"] for c in coverage)
status_counts = Counter(c["verification-status"] for c in coverage if c["verification-entry-exists"])

ent = [c for c in coverage if c["verification-entry-exists"]]
metrics = {
    "total-modules": len(all_module_ids),
    "total-vm-entries": len(vm_entries),
    "modules-without-verification": sum(1 for c in coverage if not c["verification-entry-exists"]),
    "passed": status_counts.get("passed", 0),
    "blocked": status_counts.get("blocked", 0),
    "planned": status_counts.get("planned", 0),
    "failed": status_counts.get("failed", 0),
    "in_progress": status_counts.get("in_progress", 0),
    "entries-missing-module-checks": sum(1 for c in ent if not c["has-module-checks"]),
    "entries-missing-wave-follow-up": sum(1 for c in ent if not c["has-wave-follow-up"]),
    "entries-missing-phase-follow-up": sum(1 for c in ent if not c["has-phase-follow-up"]),
    "entries-missing-observable-evidence": sum(1 for c in ent if not c["observable-evidence-defined"]),
    "entries-missing-scenarios": sum(1 for c in ent if not c["has-scenarios"]),
    "entries-with-test-files-missing-on-disk": sum(1 for c in ent if c["test-paths-missing"]),
}


# --- Write JSON ---
out = {
    "generated_at": REPORT_DIR.name,
    "source_of_truth": {
        "verification_plan": "docs/verification-plan.xml",
        "knowledge_graph": "docs/knowledge-graph.xml",
        "development_plan": "docs/development-plan.xml",
        "autonomy_lint": "final-autonomy.json",
        "status": "final-status.json",
    },
    "metrics": metrics,
    "coverage": coverage,
}
with open(REPORT_DIR / "module-coverage.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)


# --- Write Markdown summary ---
lines = []
lines.append("# Stage 2 — Module Coverage Map")
lines.append("")
lines.append(f"- Total modules: {metrics['total-modules']}")
lines.append(f"- Total V-M entries: {metrics['total-vm-entries']}")
lines.append(f"- Modules without verification entry: {metrics['modules-without-verification']}")
lines.append("")
lines.append("## Verification status counts")
for k in ("passed", "blocked", "planned", "in_progress", "failed"):
    lines.append(f"- {k}: {metrics[k]}")
lines.append("")
lines.append("## Coverage classification")
for k in ["VERIFIED_PASSED", "VERIFICATION_BLOCKED", "VERIFICATION_PLANNED",
          "VERIFICATION_IN_PROGRESS", "VERIFIED_FAILED",
          "MISSING_VERIFICATION_ENTRY", "NO_EXECUTABLE_EVIDENCE"]:
    lines.append(f"- {k}: {cls_counts.get(k, 0)}")
lines.append("")
lines.append("## Existing V-M entries missing follow-up structure")
lines.append(f"- entries missing module-checks: {metrics['entries-missing-module-checks']}")
lines.append(f"- entries missing wave-follow-up: {metrics['entries-missing-wave-follow-up']}")
lines.append(f"- entries missing phase-follow-up: {metrics['entries-missing-phase-follow-up']}")
lines.append(f"- entries missing observable-evidence: {metrics['entries-missing-observable-evidence']}")
lines.append(f"- entries missing scenarios: {metrics['entries-missing-scenarios']}")
lines.append(f"- entries with test files missing on disk: {metrics['entries-with-test-files-missing-on-disk']}")
lines.append("")
lines.append("## Modules without verification entry")
for c in coverage:
    if not c["verification-entry-exists"]:
        lines.append(
            f"- **{c['module-id']}** ({c['module-name']}) — "
            f"status={c['module-status'] or 'n/a'}, phase={c['phase'] or 'n/a'}"
        )
lines.append("")
lines.append("## Full coverage table")
lines.append("")
lines.append("| Module | Status | V-M | V-Status | Module-chk | Wave | Phase | Obs | Scen | Test-missing | Classification |")
lines.append("|--------|--------|-----|----------|-----------|------|-------|-----|------|--------------|----------------|")
for c in sorted(coverage, key=lambda x: x["module-id"]):
    lines.append(
        "| {mid} | {st} | {vid} | {vst} | {mc} | {w} | {p} | {o} | {s} | {tm} | {cl} |".format(
            mid=c["module-id"], st=c["module-status"] or "n/a", vid=c["verification-id"] or "—",
            vst=c["verification-status"] or "—",
            mc="yes" if c["has-module-checks"] else "NO",
            w="yes" if c["has-wave-follow-up"] else "NO",
            p="yes" if c["has-phase-follow-up"] else "NO",
            o="yes" if c["observable-evidence-defined"] else "NO",
            s="yes" if c["has-scenarios"] else "NO",
            tm=",".join(c["test-paths-missing"]) or "—",
            cl=c["coverage-classification"],
        )
    )
with open(REPORT_DIR / "module-coverage.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Modules: {metrics['total-modules']}")
print(f"V-M entries: {metrics['total-vm-entries']}")
print(f"Modules without verification: {metrics['modules-without-verification']}")
print(f"Status counts: {dict(status_counts)}")
print(f"Classification: {dict(cls_counts)}")
print(f"Missing module-checks: {metrics['entries-missing-module-checks']}")
print(f"Missing wave-follow-up: {metrics['entries-missing-wave-follow-up']}")
print(f"Missing phase-follow-up: {metrics['entries-missing-phase-follow-up']}")
print(f"Missing observable evidence: {metrics['entries-missing-observable-evidence']}")
print(f"Missing scenarios: {metrics['entries-missing-scenarios']}")
print(f"Test files missing on disk: {metrics['entries-with-test-files-missing-on-disk']}")
print("Wrote module-coverage.json and module-coverage.md")
