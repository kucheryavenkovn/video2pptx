# Stage 2 Verification — Evidence Alignment Correction Summary

- **Parent HEAD:** `8eec38537ec4bd53feacd33ae531c8909f030311`
- **Stage 2 verification coverage:** SUFFICIENT_FOR_CONTROLLED_AGENT_USE
- **Full autonomy readiness:** INCOMPLETE
- **GRACE documentation truthfulness:** CORRECTED AGAINST RAW TEST EVIDENCE
- **Product runtime changed:** NO
- **Tests changed:** NO
- **Raw pytest TXT changed:** NO
- **New user-visible capability:** NO
- **Full pytest rerun:** NO
- **Single correction commit:** YES (on top of `8eec385`)

### Phase 18 change matrix

| Dimension | Changed |
|-----------|---------|
| Phase 18 management state changed | **NO** |
| Phase 18 development plan changed | **NO** |
| Phase 18 verification metadata changed | **YES** |
| Phase 18 terminal outcome changed | **NO** |
| Step 18.5 started | **NO** |

Phase 18 was **not** reopened. Only verification documentation metadata for existing Phase 18 entries was corrected.

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
| cleanup-correction-consistency-check.txt | **14/14 PASS** (A–G + H no pytest src targets + I baseline invariants) |

Correction checks cover: entry count preservation, status arithmetic including `unknown_or_other`, module vs entry distinction, multi-entry preservation, failed-test contradiction, V-M-VIDEO-DECODE not passed, failure-group classification, pytest module-check must not target production `src/**/*.py`, and V-M-PERF-DETECT-BASELINE blocked/notes/module-check invariants.

## Final localized correction

**Тип результата:** `VERIFICATION_DOCUMENTATION`

**Пользовательская функция:** Непосредственно не изменяется.

**Что было неправильно:**
`V-M-PERF-DETECT-BASELINE` имела `STATUS=blocked`, но notes продолжали
утверждать passed status. Module-checks также запускали pytest против
production `src/*.py` файлов.

**Что исправлено:**
Notes согласованы со статусом blocked. Невалидные pytest src targets удалены.
Оставлены только реальные test modules (`tests/test_detection_metrics.py`,
`tests/test_detect_slides.py`). Аналогичные invalid `pytest src/...` targets
удалены из `V-M-PERF-DETECT-TWO-PASS` (тот же дефект module-check).
Причина: production `.py` не содержит pytest test cases; entry не зависит от
doctest/plugin сценария; runtime/test logic не менялись.

**Как проверено:**
Consistency check подтверждает отсутствие pytest module-checks на `src/*.py`,
сохранение blocked status и отсутствие текста о passed verification status.

**Практический эффект:**
Следующий агент не примет завершённый management milestone за зелёную
текущую verification entry и не будет запускать pytest против production-файлов.

## What this correction is / is not

- **Is:** metadata honesty against already-recorded raw pytest evidence
- **Is not:** Stage 2 redo, Phase 18 reopening, Phase 18 Step 18.5, runtime fix, test fix, GRACE blocker reduction campaign
