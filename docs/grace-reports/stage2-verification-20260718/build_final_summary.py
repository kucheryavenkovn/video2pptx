"""Regenerate final-summary.json with dynamically computed values.

Reads:
- docs/verification-plan.xml (counts V-M-* entries)
- final-autonomy.json (autonomy blockers/warnings by code)
- final-lint.json (standard lint errors/warnings)
- final-status.json (overall integrity summary)

Writes:
- final-summary.json (replaces the prior file that had total_vm_entries=true)

No hardcoding: total_vm_entries is computed by counting <V-M-*> elements
in the verification plan.
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


def count_vm_entries(vp_path: Path) -> int:
    root = ET.parse(vp_path).getroot()
    n = 0
    for node in root.iter():
        tag = strip_ns(node.tag)
        if tag.startswith("V-M-") and re.fullmatch(r"V-M-[A-Z0-9-]+", tag):
            n += 1
    return n


def count_codes(issues: list[dict], code: str) -> int:
    return sum(1 for i in issues if i.get("code", "") == code)


def main() -> None:
    total_vm = count_vm_entries(DOCS / "verification-plan.xml")

    auto = json.loads((REPORT_DIR / "final-autonomy.json").read_text(encoding="utf-8"))
    lint = json.loads((REPORT_DIR / "final-lint.json").read_text(encoding="utf-8"))
    status = json.loads((REPORT_DIR / "final-status.json").read_text(encoding="utf-8"))

    auto_issues = auto.get("issues", [])
    lint_summary = lint.get("summary", {})
    status_summary = status.get("summary", {})

    summary = {
        "total_vm_entries": total_vm,
        "standard_lint_errors": lint_summary.get("errors", 0),
        "standard_lint_warnings": lint_summary.get("warnings", 0),
        "autonomy_blockers": status_summary.get("autonomyBlockers", 0),
        "autonomy_warnings": status_summary.get("autonomyWarnings", 0),
        "verification_missing_wave_follow_up": count_codes(auto_issues, "autonomy.verification-missing-wave-follow-up"),
        "verification_missing_phase_follow_up": count_codes(auto_issues, "autonomy.verification-missing-phase-follow-up"),
        "verification_missing_observable_evidence": count_codes(auto_issues, "autonomy.verification-missing-observable-evidence"),
        "verification_missing_scenarios": count_codes(auto_issues, "autonomy.verification-missing-scenarios"),
        "verification_missing_module_checks": count_codes(auto_issues, "autonomy.verification-missing-module-checks"),
        "module_missing_verification": count_codes(auto_issues, "autonomy.module-missing-verification"),
        "module_missing_implementation_files": count_codes(auto_issues, "autonomy.module-missing-implementation-files"),
        "verification_test_file_missing_on_disk": count_codes(auto_issues, "autonomy.verification-test-file-missing-on-disk"),
        "verification_test_file_unlinked_module": count_codes(auto_issues, "autonomy.verification-test-file-unlinked-module"),
        "verification_module_check_no_test_ref": count_codes(auto_issues, "autonomy.verification-module-check-does-not-reference-test-file"),
    }

    # Sanity cross-checks
    assert isinstance(summary["total_vm_entries"], int), "total_vm_entries must be int"
    assert summary["total_vm_entries"] > 0, "total_vm_entries must be > 0"

    (REPORT_DIR / "final-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
