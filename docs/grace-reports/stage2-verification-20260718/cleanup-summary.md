# Stage 2 Verification — Evidence Alignment Correction Summary

- **Parent HEAD:** `3101dd423a7f279c212bb0c58e381f38d4732da9`
- **Stage 2 verification coverage:** SUFFICIENT_FOR_CONTROLLED_AGENT_USE
- **Full autonomy readiness:** INCOMPLETE
- **GRACE documentation truthfulness:** CORRECTED AGAINST RAW TEST EVIDENCE
- **Product runtime changed:** NO
- **Tests changed:** NO
- **Raw pytest TXT changed:** NO
- **New user-visible capability:** NO
- **Phase 18 product work changed:** NO
- **Full pytest rerun:** NO
- **Single correction commit:** YES (on top of `3101dd4`)

## Status counts

| Status | Before (reported) | Before (actual raw) | After correction |
|--------|------------------:|--------------------:|-----------------:|
| passed | 69 | 69 | 67 |
| blocked | 38 | 38 | 40 |
| planned | 33 | 33 | 34 |
| in_progress | 2 | 2 | 2 |
| failed | 0 | 0 | 0 |
| pending | *(omitted)* | 1 | 0 (→ planned) |
| done | *(omitted)* | 1 | 1 (`unknown_or_other`) |
| unknown_or_other | — | — | 1 |
| **status sum** | **142 (bug)** | **144** | **144** |
| **total V-M** | **144** | **144** | **144** |

### Previously omitted entries

| verification_id | raw_status | resolution |
|-----------------|------------|------------|
| V-M-REF-CLEAN-WINDOWS | `pending` | Normalized to `planned` (unambiguous synonym; scenarios are kind=pending, not executed). |
| V-M-PERF-DETECT-BOTTLENECK | `done` | Left as `done`. Not mapped to `passed` (no pytest surface; would invent a false green gate). Listed under `unknown_or_other`. |

## Module vs entry coverage

| Metric | Value |
|--------|------:|
| unique M-* modules | 120 |
| total V-M-* entries | 144 |
| modules with multiple V-M entries | 0 |
| module-level missing-wave (all linked entries empty) | 35 |
| entry-level missing-wave | **47** |
| V-M entries lost by aggregation | 0 |
| module and entry metrics separated | yes |

`build_coverage_map.py` no longer last-write-wins on `module_to_vm[module] = vid`.
It uses `module_to_vm: dict[str, list[str]]` and reports two levels explicitly.

## Downgrades (passed → blocked)

### V-M-VIDEO-DECODE

- **Previous status:** passed
- **Final status:** blocked
- **Failed tests:** `test_auto_returns_opencv`, `test_fallback_log` in `tests/test_video_decode.py`
- **blocked-reason:** recorded environment has PyAV available and selects PyAV for auto/fallback paths, while those tests expect OpenCV. Declared module-check is not reproducibly green. Separate decision required: update backend-selection policy or make tests environment-independent.
- **Runtime or test fix:** none (metadata only)

### V-M-PERF-DETECT-BASELINE

- **Previous status:** passed
- **Final status:** blocked
- **Failed tests:** three `TestPyAVMetrics` cases in `tests/test_detection_metrics.py` (stale codec_context test double)
- **Reason:** declared module-check is not green; no separate green targeted evidence covers the failing surface.
- **Runtime or test fix:** none (metadata only)

## Passed-entry evidence audit

Checked against failed test files from `phase-tests.json`:

| Test file | Linked V-M (status after) | Action |
|-----------|---------------------------|--------|
| tests/test_video_decode.py | V-M-VIDEO-DECODE (blocked) | downgraded |
| tests/test_detection_metrics.py | V-M-DETECT-METRICS (blocked), V-M-BACKEND-PYAV (blocked), V-M-PERF-DETECT-BASELINE (blocked) | baseline downgraded; others already blocked |
| tests/test_backends.py | V-M-BACKENDS (in_progress) | no change (not passed) |

- Remaining passed/failing contradictions: **none**

## Failure groups (7 pre-existing phase failures)

**Not** all classified as F-0103.

| Classification | Count | Related finding | Runtime regression proven |
|----------------|------:|-----------------|---------------------------|
| STALE_PYAV_CODEC_CONTEXT_TEST_DOUBLE | 3 | F-0103_CONTEXT_ONLY | false |
| ENVIRONMENT_DEPENDENT_BACKEND_SELECTION_EXPECTATION | 4 | null | false |

Raw `phase-tests.txt` is unchanged evidence of the original run.

## Consistency

| Check set | Result |
|-----------|--------|
| cleanup-consistency-check.txt | 17/17 PASS |
| cleanup-correction-consistency-check.txt | 12/12 PASS (A–G) |

Correction checks cover: entry count preservation, status arithmetic including `unknown_or_other`, module vs entry distinction, multi-entry preservation, failed-test contradiction, V-M-VIDEO-DECODE not passed, failure-group classification.

## What this correction is / is not

- **Is:** metadata honesty against already-recorded raw pytest evidence
- **Is not:** Stage 2 redo, Phase 18 Step 18.5, runtime fix, test fix, GRACE blocker reduction campaign
