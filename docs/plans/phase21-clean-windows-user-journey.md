# Phase 21 — Clean Windows User Journey + Runtime Correction

**Branch (journey):** `feature/phase21-clean-windows-user-journey`  
**Correction branch:** `fix/phase21-runtime-detection-timeline`  
**Base:** `origin/feature/phase21-clean-windows-user-journey` @ `f388350`  
**Accepted master:** `f388350`  
**Status:** in_progress (correction waves 21.1–21.8 code complete; installed-GUI smoke optional)
**Verification status:** in_progress
**Date:** 2026-07-19

Does **not** reopen Phase 19 golden-mean evidence or Phase 20 preset/rollback contracts.

---

## Product goal

Stabilize the real clean-Windows / user-journey runtime after Phase 19–20:

1. Timeline green-block interaction must not crash.
2. Detect progress must propagate to the GUI on a monotonic two-pass scale.
3. Detection duration / debounce semantics must be consistent and time-based.
4. Pass 2 must stream full-resolution representatives without `frames × segments` and without holding hundreds of full-res frames.

## Immutable contracts (Phase 19 / 20)

| Case | Value |
|------|-------|
| New project | `analysis_max_side = 480` |
| FAST | 480 |
| DETAILED | 720 (experimental) |
| NATIVE | `None` |
| CUSTOM | 240–2160 |
| Legacy missing field | `None` / Native |
| Pass 1 | may use reduced frames |
| Pass 2 / PNG / PPTX | full-resolution screenshots |

Do not change: default 480, legacy missing-field semantics, CLI UNSET/native/int, analysis quality presets, Phase 19 benchmarks, Phase 20 persistence/rollback fixes.

---

## Correction waves

| Wave | Name | Goal | Gate |
|------|------|------|------|
| 21.1 | RuntimeForensics | Localize defects; baseline evidence; no code fixes | Causes recorded under `acceptance/evidence/phase21-runtime-baseline/` |
| 21.2 | TimelineInteractionStability | Defer mutations; no Qt virtual monkeypatches; busy policy | Click/hover/move/resize/rebuild do not crash |
| 21.3 | DetectProgressPropagation | Callback path + monotonic map + ETA policy | GUI shows Pass1/Pass2/dedupe progress |
| 21.4 | QtFreeSettingsWorkflow | Extract workflow from Qt adapter | Pure tests import no PySide6 |
| 21.5 | DetectionDurationSemantics | min_stable ≥ 0; time-based debounce | FPS-independent; 0 disables debounce |
| 21.6 | DetectionDiagnostics | DetectionCounts + threshold diagnostics | Counts available; no blind threshold rewrite |
| 21.7 | StreamingRepresentativeFrames | O(frames+targets) Pass 2; ≤2 live full-res frames | Equivalence + peak frames ≤ 2 |
| 21.8 | IntegratedRuntimeAcceptance | out11 end-to-end after fixes | Timeline + progress + reopen PASS |

---

## Wave 1 summary (forensics)

Evidence: `acceptance/evidence/phase21-runtime-baseline/`

| Defect | Localized? | Root cause |
|--------|------------|------------|
| Timeline crash on move/resize | YES | Sync callback → reload → `scene.clear()` before `mouseReleaseEvent` returns |
| Timeline monkeypatch arity error | PARTIAL | Not present in timeline3 at HEAD; deleted-item path confirmed; guard tests still required |
| Progress stuck at 10% | YES | `progress_callback` not wired DetectionService → adapter → `detect_changes` |
| Duration / debounce inconsistency | YES | AppConfig `ge=0.5`; debounce uses frame-gap with hard 0.5s unit |
| Pass 2 cost | YES | Nested frames×segments; all full-res held; no early stop |

out11 baseline:

- duration ~3654 s, native PNG 1920×1080, `analysis_max_side=480`
- ~7311 sampled frames, 403 final slides, 222 PNGs
- stage counts mostly missing (observability gap → Wave 6)

---

## Implementation rules

- Separate commit per wave (no mega-commit).
- Targeted tests per wave; bounded wave after 2–7; no full suite until waves pass.
- No force-push, amend of published history, or merge to master from this plan.
- Threshold algorithm change only with separate evidence commit (Wave 6 optional).

---

## Non-goals

New 480/720 benchmarks, Phase 19 re-evaluation, preset model changes, PNG/PPTX quality changes, general GUI redesign, CI cleanup, installer release, merge to master.
