"""Build module coverage map for Stage 2 verification coverage analysis.

Reads:
- docs/knowledge-graph.xml
- docs/development-plan.xml
- docs/verification-plan.xml
- baseline-autonomy.json (from grace lint --profile autonomous --format json)
- tests/ directory

Writes:
- module-coverage.json
- module-coverage.md
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
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


# --- Load verification plan V-M entries ---
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
        "has_wave_checks": False,
        "has_phase_checks": False,
        "has_scenarios": False,
        "has_required_log_markers": False,
        "has_required_trace_assertions": False,
        "test_files": [],
        "module_checks": [],
        "wave_checks": [],
        "phase_checks": [],
        "scenarios": [],
        "required_log_markers": [],
        "required_trace_assertions": [],
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
        elif ctag == "wave-checks":
            entry["has_wave_checks"] = True
            for c in child:
                if (c.text or "").strip():
                    entry["wave_checks"].append((c.text or "").strip())
        elif ctag == "phase-checks":
            entry["has_phase_checks"] = True
            for c in child:
                if (c.text or "").strip():
                    entry["phase_checks"].append((c.text or "").strip())
        elif ctag == "scenarios":
            entry["has_scenarios"] = True
            for s in child:
                if (s.text or "").strip():
                    entry["scenarios"].append((s.text or "").strip())
        elif ctag == "required-log-markers":
            entry["has_required_log_markers"] = True
            # may contain <marker> children or text
            if (child.text or "").strip():
                entry["required_log_markers"].append((child.text or "").strip())
            for m in child:
                if (m.text or "").strip():
                    entry["required_log_markers"].append((m.text or "").strip())
        elif ctag == "required-trace-assertions":
            entry["has_required_trace_assertions"] = True
            if (child.text or "").strip():
                entry["required_trace_assertions"].append((child.text or "").strip())
            for m in child:
                if (m.text or "").strip():
                    entry["required_trace_assertions"].append((m.text or "").strip())
    vm_entries[vid] = entry


# --- Map module -> V-M entry ---
module_to_vm: dict[str, str] = {}
for vid, entry in vm_entries.items():
    module_to_vm[entry["module"]] = vid


# --- Load autonomy lint issues for per-module/per-entry signals ---
with open(REPORT_DIR / "baseline-autonomy.json", "r", encoding="utf-8") as f:
    auto = json.load(f)

autonomy_by_code: dict[str, list] = {}
for issue in auto["issues"]:
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
    kg = kg_modules.get(mid, {})
    dp = dp_modules.get(mid, {})
    vid = module_to_vm.get(mid, "")
    vm = vm_entries.get(vid, None)
    status = kg.get("status") or dp.get("status") or ""
    paths = kg.get("paths", [])
    source_paths = [p for p in paths if "test" not in p.lower().split("/")[-1]]
    test_paths_decl = list(vm["test_files"]) if vm else []
    # check test files exist on disk
    test_paths_existing = [
        t for t in test_paths_decl if (ROOT / t).exists() or t in test_files_on_disk
    ]
    test_paths_missing = [t for t in test_paths_decl if t not in test_paths_existing]

    obs_evidence = bool(vm and (vm["has_required_log_markers"] or vm["has_required_trace_assertions"]))

    # autonomy signals for this module
    mod_missing_verif = any(
        extract_module_from_msg(i.get("message", "")) == mid
        for i in autonomy_by_code.get("autonomy.module-missing-verification", [])
    )

    # autonomy signals for this V-M entry
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
    else:
        classification = "NO_EXECUTABLE_EVIDENCE"

    coverage.append({
        "module-id": mid,
        "module-status": status,
        "module-name": kg.get("name", ""),
        "phase": dp.get("layer", ""),
        "source-paths": source_paths,
        "test-paths": test_paths_decl,
        "test-paths-existing": test_paths_existing,
        "test-paths-missing": test_paths_missing,
        "verification-id": vid,
        "verification-entry-exists": bool(vm),
        "verification-status": vm["status"] if vm else "",
        "verification-priority": vm["priority"] if vm else "",
        "has-module-checks": bool(vm and vm["has_module_checks"]) if vm else False,
        "has-wave-checks": bool(vm and vm["has_wave_checks"]) if vm else False,
        "has-phase-checks": bool(vm and vm["has_phase_checks"]) if vm else False,
        "has-scenarios": bool(vm and vm["has_scenarios"]) if vm else False,
        "observable-evidence-defined": obs_evidence,
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


# --- Write JSON ---
out = {
    "generated_at": REPORT_DIR.name,
    "total-modules": len(all_module_ids),
    "total-vm-entries": len(vm_entries),
    "modules-without-verification": sum(1 for c in coverage if not c["verification-entry-exists"]),
    "coverage": coverage,
}
with open(REPORT_DIR / "module-coverage.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

# --- Write Markdown summary ---
lines = []
lines.append("# Stage 2 — Module Coverage Map")
lines.append("")
lines.append(f"- Total modules: {out['total-modules']}")
lines.append(f"- Total V-M entries: {out['total-vm-entries']}")
lines.append(f"- Modules without verification entry: {out['modules-without-verification']}")
lines.append("")
from collections import Counter
cls_counts = Counter(c["coverage-classification"] for c in coverage)
lines.append("## Coverage classification")
for k in ["VERIFIED_PASSED", "VERIFIED_FAILED", "VERIFICATION_PLANNED", "VERIFICATION_BLOCKED",
          "MISSING_VERIFICATION_ENTRY", "STALE_VERIFICATION_ENTRY", "NO_EXECUTABLE_EVIDENCE"]:
    lines.append(f"- {k}: {cls_counts.get(k, 0)}")
lines.append("")
lines.append("## Existing V-M entries missing follow-up structure")
ent = [c for c in coverage if c["verification-entry-exists"]]
lines.append(f"- entries missing wave-checks: {sum(1 for c in ent if not c['has-wave-checks'])}")
lines.append(f"- entries missing phase-checks: {sum(1 for c in ent if not c['has-phase-checks'])}")
lines.append(f"- entries missing observable-evidence: {sum(1 for c in ent if not c['observable-evidence-defined'])}")
lines.append(f"- entries missing scenarios: {sum(1 for c in ent if not c['has-scenarios'])}")
lines.append(f"- entries with test files missing on disk: {sum(1 for c in ent if c['test-paths-missing'])}")
lines.append("")
lines.append("## Modules without verification entry")
for c in coverage:
    if not c["verification-entry-exists"]:
        lines.append(f"- **{c['module-id']}** ({c['module-name']}) — status={c['module-status'] or 'n/a'}, phase={c['phase'] or 'n/a'}")
lines.append("")
lines.append("## Full coverage table")
lines.append("")
lines.append("| Module | Status | V-M | V-Status | Wave | Phase | Obs | Scen | Test-missing | Classification |")
lines.append("|--------|--------|-----|----------|------|-------|-----|------|--------------|----------------|")
for c in sorted(coverage, key=lambda x: x["module-id"]):
    lines.append("| {mid} | {st} | {vid} | {vst} | {w} | {p} | {o} | {s} | {tm} | {cl} |".format(
        mid=c["module-id"], st=c["module-status"] or "n/a", vid=c["verification-id"] or "—",
        vst=c["verification-status"] or "—",
        w="yes" if c["has-wave-checks"] else "NO",
        p="yes" if c["has-phase-checks"] else "NO",
        o="yes" if c["observable-evidence-defined"] else "NO",
        s="yes" if c["has-scenarios"] else "NO",
        tm=",".join(c["test-paths-missing"]) or "—",
        cl=c["coverage-classification"],
    ))
with open(REPORT_DIR / "module-coverage.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Modules: {out['total-modules']}")
print(f"V-M entries: {out['total-vm-entries']}")
print(f"Modules without verification: {out['modules-without-verification']}")
print("Classification:", dict(cls_counts))
print("Wrote module-coverage.json and module-coverage.md")
