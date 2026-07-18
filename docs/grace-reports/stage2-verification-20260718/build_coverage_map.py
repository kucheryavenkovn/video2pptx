"""Build module + verification-entry coverage map for Stage 2.

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

Two reporting levels (must never be conflated):
  A. Module coverage — unique M-* modules (expected 120)
  B. Verification-entry coverage — all V-M-* entries (expected 144)

Multi-entry modules preserve every linked V-M id (no last-write-wins).
Status arithmetic includes unknown_or_other and must sum to total entries.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs"
REPORT_DIR = DOCS / "grace-reports" / "stage2-verification-20260718"

CANONICAL_STATUSES = ("passed", "blocked", "planned", "in_progress", "failed")


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
    if not (tag.startswith("V-M-") and re.fullmatch(r"V-M-[A-Z0-9-]+", tag)):
        continue
    vid = tag
    mid = node.get("MODULE") or ""
    entry = {
        "id": vid,
        "module": mid,
        "priority": node.get("PRIORITY") or "",
        "status": node.get("STATUS") or "",
        "raw_status": node.get("STATUS") if node.get("STATUS") is not None else "",
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


# --- Map module -> list of V-M entries (preserve all; no last-write-wins) ---
module_to_vm: dict[str, list[str]] = defaultdict(list)
for vid, entry in vm_entries.items():
    mid = entry["module"]
    if mid:
        module_to_vm[mid].append(vid)


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


def entry_flags(vm: dict) -> dict:
    """Derive structural flags for one verification entry."""
    return {
        "has-module-checks": bool(vm["has_module_checks"] and vm["module_checks"]),
        "has-wave-follow-up": bool(vm["has_wave_follow_up"] and vm["wave_follow_up"]),
        "has-phase-follow-up": bool(vm["has_phase_follow_up"] and vm["phase_follow_up"]),
        "has-scenarios": bool(vm["has_scenarios"] and vm["scenarios"]),
        "observable-evidence-defined": bool(
            vm["has_required_trace_assertions"] and vm["required_trace_assertions"]
        ),
        "has-blocked-reason": bool(vm["has_blocked_reason"]),
        "test-paths": list(vm["test_files"]),
        "test-paths-existing": [
            t
            for t in vm["test_files"]
            if (ROOT / t).exists() or t in test_files_on_disk
        ],
        "test-paths-missing": [
            t
            for t in vm["test_files"]
            if not ((ROOT / t).exists() or t in test_files_on_disk)
        ],
        "module-checks": list(vm["module_checks"]),
        "wave-follow-up": list(vm["wave_follow_up"]),
        "unbounded-wave": any(
            cmd in {"python -m pytest tests -q", "pytest tests -q"}
            for cmd in vm["wave_follow_up"]
        ),
    }


def autonomy_for_vid(vid: str) -> dict:
    return {
        "vm-missing-wave-follow-up": any(
            extract_vm_from_msg(i.get("message", "")) == vid
            for i in autonomy_by_code.get("autonomy.verification-missing-wave-follow-up", [])
        ),
        "vm-missing-phase-follow-up": any(
            extract_vm_from_msg(i.get("message", "")) == vid
            for i in autonomy_by_code.get("autonomy.verification-missing-phase-follow-up", [])
        ),
        "vm-missing-observable-evidence": any(
            extract_vm_from_msg(i.get("message", "")) == vid
            for i in autonomy_by_code.get(
                "autonomy.verification-missing-observable-evidence", []
            )
        ),
        "vm-missing-scenarios": any(
            extract_vm_from_msg(i.get("message", "")) == vid
            for i in autonomy_by_code.get("autonomy.verification-missing-scenarios", [])
        ),
        "vm-missing-module-checks": any(
            extract_vm_from_msg(i.get("message", "")) == vid
            for i in autonomy_by_code.get("autonomy.verification-missing-module-checks", [])
        ),
        "vm-test-file-missing-on-disk": any(
            extract_vm_from_msg(i.get("message", "")) == vid
            for i in autonomy_by_code.get(
                "autonomy.verification-test-file-missing-on-disk", []
            )
        ),
        "vm-module-check-no-test-ref": any(
            extract_vm_from_msg(i.get("message", "")) == vid
            for i in autonomy_by_code.get(
                "autonomy.verification-module-check-does-not-reference-test-file", []
            )
        ),
    }


def classify_status(status: str, has_entry: bool) -> str:
    if not has_entry:
        return "MISSING_VERIFICATION_ENTRY"
    if status == "passed":
        return "VERIFIED_PASSED"
    if status == "failed":
        return "VERIFIED_FAILED"
    if status == "blocked":
        return "VERIFICATION_BLOCKED"
    if status == "planned":
        return "VERIFICATION_PLANNED"
    if status == "in_progress":
        return "VERIFICATION_IN_PROGRESS"
    return "NO_EXECUTABLE_EVIDENCE"


def status_bucket(raw: str) -> str:
    if raw in CANONICAL_STATUSES:
        return raw
    return "unknown_or_other"


# --- Section A: per-module coverage (unique M-*) ---
all_module_ids = sorted(set(kg_modules.keys()) | set(dp_modules.keys()))
module_coverage = []
for mid in all_module_ids:
    kgm = kg_modules.get(mid, {})
    dpm = dp_modules.get(mid, {})
    vids = list(module_to_vm.get(mid, []))
    vms = [vm_entries[v] for v in vids if v in vm_entries]
    status = kgm.get("status") or dpm.get("status") or ""
    paths = kgm.get("paths", [])
    source_paths = [p for p in paths if "test" not in p.lower().split("/")[-1]]

    # Aggregate flags across all linked entries (any/all as appropriate)
    all_test_paths: list[str] = []
    for vm in vms:
        all_test_paths.extend(vm["test_files"])
    # de-dupe preserving order
    seen_tf: set[str] = set()
    test_paths_decl: list[str] = []
    for t in all_test_paths:
        if t not in seen_tf:
            seen_tf.add(t)
            test_paths_decl.append(t)
    test_paths_existing = [
        t for t in test_paths_decl if (ROOT / t).exists() or t in test_files_on_disk
    ]
    test_paths_missing = [t for t in test_paths_decl if t not in test_paths_existing]

    statuses = [vm["status"] for vm in vms]
    # Aggregate status: prefer worst-case when multiple (failed > blocked > in_progress > planned > passed)
    rank = {"failed": 5, "blocked": 4, "in_progress": 3, "planned": 2, "passed": 1}
    if not statuses:
        aggregate_status = ""
    else:
        aggregate_status = max(statuses, key=lambda s: rank.get(s, 0))

    mod_missing_verif = any(
        extract_module_from_msg(i.get("message", "")) == mid
        for i in autonomy_by_code.get("autonomy.module-missing-verification", [])
    )

    # OR of per-entry missing signals
    agg_flags = {
        "has-module-checks": any(
            entry_flags(vm)["has-module-checks"] for vm in vms
        )
        if vms
        else False,
        "has-wave-follow-up": any(
            entry_flags(vm)["has-wave-follow-up"] for vm in vms
        )
        if vms
        else False,
        "has-phase-follow-up": any(
            entry_flags(vm)["has-phase-follow-up"] for vm in vms
        )
        if vms
        else False,
        "has-scenarios": any(entry_flags(vm)["has-scenarios"] for vm in vms)
        if vms
        else False,
        "observable-evidence-defined": any(
            entry_flags(vm)["observable-evidence-defined"] for vm in vms
        )
        if vms
        else False,
        "has-blocked-reason": any(entry_flags(vm)["has-blocked-reason"] for vm in vms)
        if vms
        else False,
    }

    # Missing wave at module level = every linked entry lacks non-empty wave
    # (or no entries). This is module-level aggregate, not entry-level count.
    module_all_missing_wave = (
        (not vms)
        or all(not entry_flags(vm)["has-wave-follow-up"] for vm in vms)
    )

    classification = classify_status(aggregate_status, bool(vms))

    module_coverage.append(
        {
            "module-id": mid,
            "module-status": status,
            "module-name": kgm.get("name", ""),
            "phase": dpm.get("layer", ""),
            "source-paths": source_paths,
            "test-paths": test_paths_decl,
            "test-paths-existing": test_paths_existing,
            "test-paths-missing": test_paths_missing,
            "verification-ids": vids,
            "verification-id": vids[0] if len(vids) == 1 else (
                ",".join(vids) if vids else ""
            ),
            "verification-entry-count": len(vids),
            "verification-entry-exists": bool(vms),
            "verification-statuses": statuses,
            "verification-status": aggregate_status,
            "verification-priority": vms[0]["priority"] if len(vms) == 1 else "",
            "has-module-checks": agg_flags["has-module-checks"],
            "has-wave-follow-up": agg_flags["has-wave-follow-up"],
            "has-phase-follow-up": agg_flags["has-phase-follow-up"],
            "has-scenarios": agg_flags["has-scenarios"],
            "observable-evidence-defined": agg_flags["observable-evidence-defined"],
            "has-blocked-reason": agg_flags["has-blocked-reason"],
            "module_all_entries_missing_wave": module_all_missing_wave,
            "autonomy_signals": {
                "module-missing-verification": mod_missing_verif,
            },
            "coverage-classification": classification,
        }
    )


# --- Section B: per-entry coverage (all V-M-*) ---
entry_coverage = []
for vid, vm in sorted(vm_entries.items()):
    flags = entry_flags(vm)
    auto_sig = autonomy_for_vid(vid)
    bucket = status_bucket(vm["status"])
    entry_coverage.append(
        {
            "verification-id": vid,
            "module": vm["module"],
            "priority": vm["priority"],
            "status": vm["status"],
            "raw_status": vm["raw_status"],
            "status_bucket": bucket,
            "has-module-checks": flags["has-module-checks"],
            "has-wave-follow-up": flags["has-wave-follow-up"],
            "has-phase-follow-up": flags["has-phase-follow-up"],
            "has-scenarios": flags["has-scenarios"],
            "observable-evidence-defined": flags["observable-evidence-defined"],
            "has-blocked-reason": flags["has-blocked-reason"],
            "test-paths": flags["test-paths"],
            "test-paths-existing": flags["test-paths-existing"],
            "test-paths-missing": flags["test-paths-missing"],
            "module-checks": flags["module-checks"],
            "wave-follow-up": flags["wave-follow-up"],
            "unbounded-wave": flags["unbounded-wave"],
            "broken-module-checks": [
                cmd
                for cmd in flags["module-checks"]
                if any(
                    (not (ROOT / p).exists() and p not in test_files_on_disk)
                    for p in re.findall(r"tests/[\w./-]+\.py", cmd)
                )
            ],
            "autonomy_signals": auto_sig,
            "coverage-classification": classify_status(vm["status"], True),
        }
    )


# --- Metrics A: module-level ---
mod_cls = Counter(c["coverage-classification"] for c in module_coverage)
mod_status = Counter(
    c["verification-status"] for c in module_coverage if c["verification-entry-exists"]
)
modules_with_one = sum(1 for c in module_coverage if c["verification-entry-count"] == 1)
modules_with_multi = sum(1 for c in module_coverage if c["verification-entry-count"] > 1)
modules_without = sum(1 for c in module_coverage if c["verification-entry-count"] == 0)

module_metrics = {
    "total_modules": len(all_module_ids),
    "modules_without_verification": modules_without,
    "modules_with_one_verification_entry": modules_with_one,
    "modules_with_multiple_verification_entries": modules_with_multi,
    "modules_by_aggregate_status": {
        k: mod_status.get(k, 0) for k in CANONICAL_STATUSES
    },
    "modules_missing_wave_all_entries": sum(
        1
        for c in module_coverage
        if c["verification-entry-exists"] and c["module_all_entries_missing_wave"]
    ),
    "coverage_classification": dict(mod_cls),
}


# --- Metrics B: entry-level ---
entry_status_counts: dict[str, int] = {k: 0 for k in CANONICAL_STATUSES}
entry_status_counts["unknown_or_other"] = 0
unknown_or_other_entries = []
for e in entry_coverage:
    bucket = e["status_bucket"]
    entry_status_counts[bucket] = entry_status_counts.get(bucket, 0) + 1
    if bucket == "unknown_or_other":
        unknown_or_other_entries.append(
            {
                "verification_id": e["verification-id"],
                "module": e["module"],
                "raw_status": e["raw_status"],
            }
        )

entry_metrics = {
    "total_verification_entries": len(vm_entries),
    "entries_by_status": dict(entry_status_counts),
    "entries_missing_module_checks": sum(
        1 for e in entry_coverage if not e["has-module-checks"]
    ),
    "entries_missing_wave_follow_up": sum(
        1 for e in entry_coverage if not e["has-wave-follow-up"]
    ),
    "entries_missing_phase_follow_up": sum(
        1 for e in entry_coverage if not e["has-phase-follow-up"]
    ),
    "entries_missing_observable_evidence": sum(
        1 for e in entry_coverage if not e["observable-evidence-defined"]
    ),
    "entries_missing_scenarios": sum(
        1 for e in entry_coverage if not e["has-scenarios"]
    ),
    "entries_with_missing_test_paths": sum(
        1 for e in entry_coverage if e["test-paths-missing"]
    ),
    "entries_with_broken_module_checks": sum(
        1 for e in entry_coverage if e["broken-module-checks"]
    ),
    "entries_with_unbounded_wave": sum(
        1 for e in entry_coverage if e["unbounded-wave"]
    ),
    "unknown_or_other_entries": unknown_or_other_entries,
}

# Hard assertion: status arithmetic
status_sum = sum(entry_status_counts.values())
assert status_sum == entry_metrics["total_verification_entries"], (
    f"status sum {status_sum} != total entries "
    f"{entry_metrics['total_verification_entries']}: {entry_status_counts}"
)

# Preserve entries: every V-M must appear in entry_coverage
assert len(entry_coverage) == len(vm_entries)

# Multi-entry modules: every linked vid must still exist in vm_entries
lost_by_aggregation = []
for mid, vids in module_to_vm.items():
    for vid in vids:
        if vid not in vm_entries:
            lost_by_aggregation.append((mid, vid))
assert not lost_by_aggregation, f"lost entries: {lost_by_aggregation}"

# Multi-entry module list for report
multi_entry_modules = {
    mid: vids for mid, vids in sorted(module_to_vm.items()) if len(vids) > 1
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
    "levels": {
        "note": (
            "Module-level metrics count unique M-* modules. "
            "Entry-level metrics count all V-M-* verification entries. "
            "These must not be treated as interchangeable."
        ),
        "module": module_metrics,
        "verification_entry": entry_metrics,
    },
    # Backward-compatible top-level metrics (entry-level truth + module totals)
    "metrics": {
        "total-modules": module_metrics["total_modules"],
        "total-vm-entries": entry_metrics["total_verification_entries"],
        "modules-without-verification": module_metrics["modules_without_verification"],
        "modules-with-one-verification-entry": module_metrics[
            "modules_with_one_verification_entry"
        ],
        "modules-with-multiple-verification-entries": module_metrics[
            "modules_with_multiple_verification_entries"
        ],
        "passed": entry_status_counts.get("passed", 0),
        "blocked": entry_status_counts.get("blocked", 0),
        "planned": entry_status_counts.get("planned", 0),
        "failed": entry_status_counts.get("failed", 0),
        "in_progress": entry_status_counts.get("in_progress", 0),
        "unknown_or_other": entry_status_counts.get("unknown_or_other", 0),
        "status_sum": status_sum,
        "entries-missing-module-checks": entry_metrics["entries_missing_module_checks"],
        "entries-missing-wave-follow-up": entry_metrics[
            "entries_missing_wave_follow_up"
        ],
        "entries-missing-phase-follow-up": entry_metrics[
            "entries_missing_phase_follow_up"
        ],
        "entries-missing-observable-evidence": entry_metrics[
            "entries_missing_observable_evidence"
        ],
        "entries-missing-scenarios": entry_metrics["entries_missing_scenarios"],
        "entries-with-test-files-missing-on-disk": entry_metrics[
            "entries_with_missing_test_paths"
        ],
        "entries-with-broken-module-checks": entry_metrics[
            "entries_with_broken_module_checks"
        ],
        "entries-with-unbounded-wave": entry_metrics["entries_with_unbounded_wave"],
        "module-level-missing-wave-all-entries": module_metrics[
            "modules_missing_wave_all_entries"
        ],
    },
    "multi_entry_modules": multi_entry_modules,
    "unknown_or_other_entries": unknown_or_other_entries,
    "module_coverage": module_coverage,
    "entry_coverage": entry_coverage,
    # Keep legacy key for older consumers (module-level rows only)
    "coverage": module_coverage,
}
with open(REPORT_DIR / "module-coverage.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)


# --- Write Markdown summary ---
lines = []
lines.append("# Stage 2 — Module & Verification-Entry Coverage Map")
lines.append("")
lines.append(
    "This report separates **module-level** (unique `M-*`) from "
    "**verification-entry-level** (all `V-M-*`). Do not treat module counts "
    "as entry counts."
)
lines.append("")
lines.append("## A. Module coverage (unique M-*)")
lines.append("")
lines.append(f"- total_modules: {module_metrics['total_modules']}")
lines.append(
    f"- modules_without_verification: "
    f"{module_metrics['modules_without_verification']}"
)
lines.append(
    f"- modules_with_one_verification_entry: "
    f"{module_metrics['modules_with_one_verification_entry']}"
)
lines.append(
    f"- modules_with_multiple_verification_entries: "
    f"{module_metrics['modules_with_multiple_verification_entries']}"
)
lines.append(
    f"- modules_missing_wave_all_entries (module-level aggregate): "
    f"{module_metrics['modules_missing_wave_all_entries']}"
)
lines.append("- modules_by_aggregate_status:")
for k in CANONICAL_STATUSES:
    lines.append(f"  - {k}: {module_metrics['modules_by_aggregate_status'].get(k, 0)}")
lines.append("")
lines.append("### Multi-entry modules (all linked V-M-* preserved)")
if multi_entry_modules:
    for mid, vids in multi_entry_modules.items():
        lines.append(f"- **{mid}**: {', '.join(vids)}")
else:
    lines.append(
        "- (none — each M-* currently has at most one V-M entry; "
        "Phase-*/Step-* verification entries are reported at entry level only)"
    )
lines.append("")
lines.append("## B. Verification-entry coverage (all V-M-*)")
lines.append("")
lines.append(
    f"- total_verification_entries: "
    f"{entry_metrics['total_verification_entries']}"
)
lines.append("- entries_by_status:")
for k in list(CANONICAL_STATUSES) + ["unknown_or_other"]:
    lines.append(f"  - {k}: {entry_status_counts.get(k, 0)}")
lines.append(f"- status_sum: {status_sum} (must equal total_verification_entries)")
lines.append(
    f"- entries_missing_module_checks: "
    f"{entry_metrics['entries_missing_module_checks']}"
)
lines.append(
    f"- entries_missing_wave_follow_up: "
    f"{entry_metrics['entries_missing_wave_follow_up']}"
)
lines.append(
    f"- entries_missing_phase_follow_up: "
    f"{entry_metrics['entries_missing_phase_follow_up']}"
)
lines.append(
    f"- entries_missing_observable_evidence: "
    f"{entry_metrics['entries_missing_observable_evidence']}"
)
lines.append(
    f"- entries_missing_scenarios: {entry_metrics['entries_missing_scenarios']}"
)
lines.append(
    f"- entries_with_missing_test_paths: "
    f"{entry_metrics['entries_with_missing_test_paths']}"
)
lines.append(
    f"- entries_with_broken_module_checks: "
    f"{entry_metrics['entries_with_broken_module_checks']}"
)
lines.append(
    f"- entries_with_unbounded_wave: "
    f"{entry_metrics['entries_with_unbounded_wave']}"
)
lines.append("")
if unknown_or_other_entries:
    lines.append("### unknown_or_other_entries")
    for u in unknown_or_other_entries:
        lines.append(
            f"- {u['verification_id']} module={u['module']} "
            f"raw_status={u['raw_status']!r}"
        )
    lines.append("")
else:
    lines.append(
        "### unknown_or_other_entries\n"
        "- (none — all entries use canonical STATUS values)\n"
    )

lines.append("## Module coverage classification")
for k in [
    "VERIFIED_PASSED",
    "VERIFICATION_BLOCKED",
    "VERIFICATION_PLANNED",
    "VERIFICATION_IN_PROGRESS",
    "VERIFIED_FAILED",
    "MISSING_VERIFICATION_ENTRY",
    "NO_EXECUTABLE_EVIDENCE",
]:
    lines.append(f"- {k}: {mod_cls.get(k, 0)}")
lines.append("")
lines.append("## Modules without verification entry")
for c in module_coverage:
    if not c["verification-entry-exists"]:
        lines.append(
            f"- **{c['module-id']}** ({c['module-name']}) — "
            f"status={c['module-status'] or 'n/a'}, phase={c['phase'] or 'n/a'}"
        )
if modules_without == 0:
    lines.append("- (none)")
lines.append("")
lines.append("## Full module coverage table")
lines.append("")
lines.append(
    "| Module | Status | V-M entries | V-Status (agg) | Module-chk | Wave | "
    "Phase | Obs | Scen | Test-missing | Classification |"
)
lines.append(
    "|--------|--------|-------------|----------------|-----------|------|"
    "-------|-----|------|--------------|----------------|"
)
for c in sorted(module_coverage, key=lambda x: x["module-id"]):
    vids_disp = ", ".join(c["verification-ids"]) if c["verification-ids"] else "—"
    lines.append(
        "| {mid} | {st} | {vid} | {vst} | {mc} | {w} | {p} | {o} | {s} | {tm} | {cl} |".format(
            mid=c["module-id"],
            st=c["module-status"] or "n/a",
            vid=vids_disp,
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
lines.append("")
lines.append("## Full verification-entry table")
lines.append("")
lines.append(
    "| V-M | Module | Status | Module-chk | Wave | Phase | Obs | Scen | "
    "Missing tests | Unbounded wave |"
)
lines.append(
    "|-----|--------|--------|-----------|------|-------|-----|------|"
    "---------------|----------------|"
)
for e in entry_coverage:
    lines.append(
        "| {vid} | {mod} | {st} | {mc} | {w} | {p} | {o} | {s} | {tm} | {uw} |".format(
            vid=e["verification-id"],
            mod=e["module"] or "—",
            st=e["status"] or "—",
            mc="yes" if e["has-module-checks"] else "NO",
            w="yes" if e["has-wave-follow-up"] else "NO",
            p="yes" if e["has-phase-follow-up"] else "NO",
            o="yes" if e["observable-evidence-defined"] else "NO",
            s="yes" if e["has-scenarios"] else "NO",
            tm=",".join(e["test-paths-missing"]) or "—",
            uw="YES" if e["unbounded-wave"] else "—",
        )
    )

with open(REPORT_DIR / "module-coverage.md", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Modules: {module_metrics['total_modules']}")
print(f"V-M entries: {entry_metrics['total_verification_entries']}")
print(f"Modules without verification: {modules_without}")
print(f"Modules with multi V-M: {modules_with_multi}")
print(f"Entry status counts: {entry_status_counts}")
print(f"Status sum: {status_sum}")
print(
    f"Entry-level missing wave-follow-up: "
    f"{entry_metrics['entries_missing_wave_follow_up']}"
)
print(
    f"Module-level missing wave (all entries): "
    f"{module_metrics['modules_missing_wave_all_entries']}"
)
print(f"unknown_or_other: {unknown_or_other_entries}")
print("Wrote module-coverage.json and module-coverage.md")
