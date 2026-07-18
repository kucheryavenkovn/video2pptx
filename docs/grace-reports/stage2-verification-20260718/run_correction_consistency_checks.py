"""Stage 2 evidence-alignment correction consistency checks.

Checks A–G (plus supporting arithmetic) against:
- docs/verification-plan.xml
- module-coverage.json
- cleanup-summary.json
- test-runs/phase-tests.json
- test-runs/index.json
- test-runs/targeted-tests.json

Writes: cleanup-correction-consistency-check.txt

Exit code 0 = all checks passed; 1 = at least one failed.
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs"
REPORT_DIR = DOCS / "grace-reports" / "stage2-verification-20260718"
VP = DOCS / "verification-plan.xml"
CANONICAL = ("passed", "blocked", "planned", "in_progress", "failed")

FAILED_TEST_FILES = {
    "tests/test_backends.py",
    "tests/test_detection_metrics.py",
    "tests/test_video_decode.py",
}

CODEC_CONTEXT_TESTS = {
    "tests/test_detection_metrics.py::TestPyAVMetrics::test_exact_decode_conversion_and_transfer_metrics[False-key_frames0-2]",
    "tests/test_detection_metrics.py::TestPyAVMetrics::test_exact_decode_conversion_and_transfer_metrics[True-key_frames1-2]",
    "tests/test_detection_metrics.py::TestPyAVMetrics::test_decode_failure_closes_container_and_propagates",
}

BACKEND_SELECTION_TESTS = {
    "tests/test_backends.py::TestResolveBackend::test_auto_returns_opencv",
    "tests/test_backends.py::TestResolveBackend::test_unsupported_falls_back",
    "tests/test_video_decode.py::TestSelectBackend::test_auto_returns_opencv",
    "tests/test_video_decode.py::TestSelectBackend::test_fallback_log",
}


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1]


def check(name: str, condition: bool, detail: str = "") -> tuple[str, bool, str]:
    return (name, bool(condition), detail)


def load_entries(root: ET.Element) -> list[tuple[str, ET.Element]]:
    entries = []
    for node in root.iter():
        tag = strip_ns(node.tag)
        if tag.startswith("V-M-") and re.fullmatch(r"V-M-[A-Z0-9-]+", tag):
            entries.append((tag, node))
    return entries


def entry_test_files(node: ET.Element) -> list[str]:
    out = []
    for child in node:
        if strip_ns(child.tag) == "test-files":
            for f in child:
                t = (f.text or "").strip()
                if t:
                    out.append(t)
    return out


def targeted_green_files() -> set[str]:
    """Test files covered by a green targeted run (exit_code 0)."""
    path = REPORT_DIR / "test-runs" / "targeted-tests.json"
    if not path.exists():
        return set()
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("exit_code", 1) != 0:
        return set()
    cmd = data.get("command", "")
    files = set(re.findall(r"tests/[\w./-]+\.py", cmd))
    # wave is also green but broader; include for optional evidence
    wave = REPORT_DIR / "test-runs" / "wave-tests.json"
    if wave.exists():
        w = json.loads(wave.read_text(encoding="utf-8"))
        if w.get("exit_code", 1) == 0:
            # wave is directory-scoped; do not claim specific root test files
            pass
    return files


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    # --- Parse XML ---
    try:
        root = ET.parse(VP).getroot()
        xml_ok = True
        xml_err = ""
    except Exception as exc:  # noqa: BLE001
        root = None
        xml_ok = False
        xml_err = f"{type(exc).__name__}: {exc}"
    results.append(check("A0_xml_parse", xml_ok, xml_err or "verification-plan.xml parses"))

    if root is None:
        _write(results, extra_notes=["XML parse failed; remaining checks skipped."])
        return 1

    entries = load_entries(root)
    total = len(entries)
    ids = [vid for vid, _ in entries]
    duplicates = sorted({vid for vid in ids if ids.count(vid) > 1})

    # A: entry count preservation
    results.append(
        check(
            "A_entry_count_preservation",
            total == 144,
            f"all V-M entries parsed = {total} (expected 144)",
        )
    )
    results.append(
        check(
            "A2_no_duplicate_ids",
            len(duplicates) == 0,
            f"duplicates={duplicates}",
        )
    )

    # B: status arithmetic
    status_counts: Counter[str] = Counter()
    unknown_list = []
    for vid, node in entries:
        raw = node.get("STATUS")
        if raw is None or raw == "":
            bucket = "unknown_or_other"
            unknown_list.append((vid, node.get("MODULE") or "", repr(raw)))
        elif raw in CANONICAL:
            bucket = raw
        else:
            bucket = "unknown_or_other"
            unknown_list.append((vid, node.get("MODULE") or "", raw))
        status_counts[bucket] += 1

    all_status_counts = {k: status_counts.get(k, 0) for k in list(CANONICAL) + ["unknown_or_other"]}
    status_sum = sum(all_status_counts.values())
    results.append(
        check(
            "B_status_arithmetic",
            status_sum == total,
            f"sum(status counts including unknown_or_other)={status_sum} "
            f"total={total} counts={all_status_counts} "
            f"unknown_or_other_entries={unknown_list}",
        )
    )

    # C: module vs entry distinction
    cov_path = REPORT_DIR / "module-coverage.json"
    cov = json.loads(cov_path.read_text(encoding="utf-8"))
    metrics = cov.get("metrics", {})
    levels = cov.get("levels", {})
    mod_total = metrics.get("total-modules") or levels.get("module", {}).get("total_modules")
    ent_total = metrics.get("total-vm-entries") or levels.get(
        "verification_entry", {}
    ).get("total_verification_entries")
    entry_wave = metrics.get("entries-missing-wave-follow-up")
    module_wave = metrics.get("module-level-missing-wave-all-entries")
    # Ensure module-level wave is not silently used as entry-level
    levels_present = "module" in levels and "verification_entry" in levels
    results.append(
        check(
            "C_module_vs_entry_distinction",
            mod_total == 120
            and ent_total == 144
            and levels_present
            and entry_wave is not None
            and module_wave is not None,
            f"module count={mod_total} entry count={ent_total} "
            f"levels_present={levels_present} "
            f"entry_missing_wave={entry_wave} "
            f"module_missing_wave={module_wave}",
        )
    )
    # Explicitly fail if entry-level missing-wave is incorrectly 35 (old bug)
    # while XML has 47 empty waves — report must use entry-level 47.
    empty_wave_xml = 0
    for vid, node in entries:
        has_wave_tag = False
        non_empty = False
        for child in node:
            if strip_ns(child.tag) == "wave-follow-up":
                has_wave_tag = True
                if (child.text or "").strip():
                    non_empty = True
        if not has_wave_tag or not non_empty:
            empty_wave_xml += 1
    results.append(
        check(
            "C2_entry_level_missing_wave_matches_xml",
            entry_wave == empty_wave_xml,
            f"module-coverage entry-level missing-wave={entry_wave} "
            f"xml empty/missing wave={empty_wave_xml} "
            f"(must not report module-level {module_wave} as entry-level)",
        )
    )

    # D: multi-entry modules preserved
    module_to_vm: dict[str, list[str]] = defaultdict(list)
    for vid, node in entries:
        mid = node.get("MODULE") or ""
        if mid:
            module_to_vm[mid].append(vid)
    multi = {m: vids for m, vids in module_to_vm.items() if len(vids) > 1}
    # coverage must list every multi-entry module's vids without loss
    cov_multi = cov.get("multi_entry_modules", {})
    lost = []
    for mid, vids in multi.items():
        reported = cov_multi.get(mid) or []
        for v in vids:
            if v not in reported and v not in (
                # also accept presence in entry_coverage
                []
            ):
                # check entry_coverage
                pass
        if set(vids) != set(reported):
            # if multi is empty this is fine; if multi non-empty must match
            if multi:
                lost.append((mid, vids, reported))
    # Also verify every entry appears in entry_coverage
    entry_cov = cov.get("entry_coverage") or []
    entry_ids = {e.get("verification-id") for e in entry_cov}
    missing_from_cov = [vid for vid, _ in entries if vid not in entry_ids]
    results.append(
        check(
            "D_multi_entry_modules_preserved",
            len(missing_from_cov) == 0
            and len(entry_ids) == total
            and (not multi or not lost),
            f"multi_entry_modules={dict(multi)} "
            f"coverage_multi={cov_multi} lost={lost} "
            f"missing_from_entry_coverage={missing_from_cov} "
            f"entry_coverage_count={len(entry_ids)}",
        )
    )

    # E: failed-test contradiction for STATUS=passed
    phase = json.loads(
        (REPORT_DIR / "test-runs" / "phase-tests.json").read_text(encoding="utf-8")
    )
    failed_tests = set(phase.get("failed_tests") or [])
    failed_files = {t.split("::", 1)[0] for t in failed_tests}
    green_files = targeted_green_files()

    contradictions = []
    for vid, node in entries:
        if (node.get("STATUS") or "") != "passed":
            continue
        tfs = entry_test_files(node)
        hit = [f for f in tfs if f in failed_files]
        if not hit:
            continue
        # Separate green targeted evidence only counts if it covers the failing file
        covered = [f for f in hit if f in green_files]
        if set(hit) <= set(covered):
            continue
        contradictions.append(
            {
                "verification_id": vid,
                "status": "passed",
                "failed_test_files": hit,
                "green_targeted_cover": covered,
            }
        )
    results.append(
        check(
            "E_failed_test_contradiction",
            len(contradictions) == 0,
            f"passed entries with failing test files and no separate green "
            f"targeted evidence: {contradictions}",
        )
    )

    # F: V-M-VIDEO-DECODE not passed while its tests fail
    vd_status = None
    for vid, node in entries:
        if vid == "V-M-VIDEO-DECODE":
            vd_status = node.get("STATUS") or ""
            break
    video_failures_present = any(
        t.startswith("tests/test_video_decode.py::") for t in failed_tests
    )
    video_green = "tests/test_video_decode.py" in green_files
    results.append(
        check(
            "F_vm_video_decode_not_passed",
            (not video_failures_present)
            or video_green
            or (vd_status is not None and vd_status != "passed"),
            f"V-M-VIDEO-DECODE status={vd_status!r} "
            f"video_failures_present={video_failures_present} "
            f"separate_green={video_green}",
        )
    )

    # G: failure classification groups
    failure_groups = phase.get("failure_groups")
    if not failure_groups and "phase_test_pre_existing_failures" in (
        cleanup := json.loads(
            (REPORT_DIR / "cleanup-summary.json").read_text(encoding="utf-8")
        )
    ):
        failure_groups = cleanup.get("phase_test_pre_existing_failures", {}).get(
            "failure_groups"
        )

    group_ok = False
    group_detail = f"failure_groups={failure_groups!r}"
    if isinstance(failure_groups, list) and len(failure_groups) >= 2:
        by_class = {g.get("classification"): g for g in failure_groups}
        a = by_class.get("STALE_PYAV_CODEC_CONTEXT_TEST_DOUBLE")
        b = by_class.get("ENVIRONMENT_DEPENDENT_BACKEND_SELECTION_EXPECTATION")
        if a and b:
            a_tests = set(a.get("tests") or [])
            b_tests = set(b.get("tests") or [])
            a_count = a.get("count")
            b_count = b.get("count")
            total_fail = phase.get("failed", 0)
            group_ok = (
                a_count == 3
                and b_count == 4
                and a_tests == CODEC_CONTEXT_TESTS
                and b_tests == BACKEND_SELECTION_TESTS
                and (a_count + b_count) == total_fail
                and a.get("runtime_regression_proven") is False
                and b.get("runtime_regression_proven") is False
            )
            # F-0103 must not be the sole classification for all seven
            legacy = phase.get("failure_classification", "")
            all_as_f0103 = (
                "CODEC_CONTEXT_PROVENANCE" in str(legacy)
                and "ENVIRONMENT_DEPENDENT" not in str(legacy)
                and failure_groups is None
            )
            group_detail = (
                f"codec_context_group count={a_count} tests={sorted(a_tests)} "
                f"backend_selection count={b_count} tests={sorted(b_tests)} "
                f"total_failed={total_fail} "
                f"legacy_classification={legacy!r} "
                f"all_as_f0103_only={all_as_f0103}"
            )
    results.append(
        check(
            "G_failure_group_classification",
            group_ok,
            group_detail
            + " | expected: 3 STALE_PYAV_CODEC_CONTEXT_TEST_DOUBLE + "
            "4 ENVIRONMENT_DEPENDENT_BACKEND_SELECTION_EXPECTATION",
        )
    )

    # Bonus: status_sum hard assertion in coverage metrics
    cov_status_sum = metrics.get("status_sum")
    results.append(
        check(
            "B2_coverage_status_sum",
            cov_status_sum == 144
            and metrics.get("passed", -1)
            + metrics.get("blocked", -1)
            + metrics.get("planned", -1)
            + metrics.get("in_progress", -1)
            + metrics.get("failed", -1)
            + metrics.get("unknown_or_other", -1)
            == 144,
            f"coverage metrics status_sum={cov_status_sum} "
            f"passed={metrics.get('passed')} blocked={metrics.get('blocked')} "
            f"planned={metrics.get('planned')} "
            f"in_progress={metrics.get('in_progress')} "
            f"failed={metrics.get('failed')} "
            f"unknown_or_other={metrics.get('unknown_or_other')}",
        )
    )

    # Bonus: empty wave entry-level is 47 if XML says 47
    results.append(
        check(
            "C3_empty_wave_is_entry_level_47_if_xml_has_47",
            empty_wave_xml != 47 or entry_wave == 47,
            f"xml_empty_wave={empty_wave_xml} entry_level_missing_wave={entry_wave}",
        )
    )

    return _write(
        results,
        extra_notes=[
            f"Total V-M parsed: {total}",
            f"Status counts: {all_status_counts}",
            f"Status sum: {status_sum}",
            f"unknown_or_other_entries: {unknown_list}",
            f"XML empty/missing wave-follow-up entries: {empty_wave_xml}",
            f"Module-level missing-wave (all entries empty): {module_wave}",
            f"Entry-level missing-wave: {entry_wave}",
            f"Multi-entry modules: {dict(multi) if multi else '(none)'}",
            f"Passed/failing contradictions remaining: {contradictions}",
            f"V-M-VIDEO-DECODE status: {vd_status}",
            "Product runtime and tests were not modified by this correction.",
        ],
    )


def _write(
    results: list[tuple[str, bool, str]],
    extra_notes: list[str] | None = None,
) -> int:
    lines = [
        "# Stage 2 Evidence Alignment — Correction Consistency Checks",
        "",
        f"Total checks: {len(results)}",
    ]
    passed = sum(1 for _, ok, _ in results if ok)
    lines.append(f"Passed: {passed}")
    lines.append(f"Failed: {len(results) - passed}")
    lines.append("")
    lines.append("## Detail")
    lines.append("")
    for name, ok, detail in results:
        marker = "PASS" if ok else "FAIL"
        lines.append(f"[{marker}] {name}")
        if detail:
            for dl in str(detail).splitlines():
                lines.append(f"        {dl}")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for note in extra_notes or []:
        lines.append(f"- {note}")

    out_path = REPORT_DIR / "cleanup-correction-consistency-check.txt"
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
