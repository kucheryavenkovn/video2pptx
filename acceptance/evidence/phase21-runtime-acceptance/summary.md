# Phase 21 Wave 8 — Integrated runtime acceptance

**Date:** 2026-07-19  
**Branch:** `fix/phase21-runtime-detection-timeline`  
**Method:** Automated targeted/bounded tests + fixture detect + static out11 baseline

## Timeline (automated)

| Interaction | Result | Evidence |
|-------------|--------|----------|
| click | PASS | `tests/gui/test_timeline_interactions.py::test_slide_click_does_not_raise` |
| hover | PASS | `test_slide_hover_does_not_raise` |
| move | PASS | `test_slide_move_commit_is_deferred` |
| resize | PASS | `test_slide_resize_commit_is_deferred` |
| scene rebuild | PASS | `test_scene_rebuild_after_move_does_not_access_deleted_item` |
| no monkeypatch | PASS | `test_no_instance_virtual_method_monkeypatch` |

Manual installed-GUI on out11 not re-run in this session; code path matches deferred-commit fix.

## Progress

| Check | Result |
|-------|--------|
| operationStarted before progress | PASS |
| detector progress → observer | PASS |
| monotonic StatusBarManager | PASS |
| ETA hidden first 3s | PASS |
| map pass1 → 5–65 | PASS |
| map pass2 → 70–93 | PASS |

Fixture detect (local stage percents before service mapping) shows stage-local resets; DetectionService maps to global monotonic scale.

## Detection fixture (`tests/fixtures/test_slides.mp4`)

See `acceptance-fixture.json`:

- analysis_max_side=480
- sampled_frames=12, candidates=3, debounced=3, final slides=4
- pass2_peak_live_fullres_frames=2
- pass2_comparisons=15 (≪ frames×targets)
- PNG dims = native 640×480

## out11 project (baseline, not full re-detect)

From Wave 1 baseline (pre-correction artifacts):

- duration ~3654s, analysis_max_side=480, sample_fps=2
- ~7311 sampled frames, 403 final slides, PNG 1920×1080 full-res
- Full re-detect of Hermes ~60min lecture deferred (non-goal: new benchmark)

## Phase 19/20 preservation

| Contract | Status |
|----------|--------|
| New project 480 | PASS (`Project.create_new`) |
| Legacy domain default None | PASS |
| DETAILED 720 | unchanged presets |
| CUSTOM 240–2160 | unchanged |
| Full-res PNG | PASS on fixture |
| Settings rollback | PASS Qt-free tests |

## Threshold algorithm

**AUTO_THRESHOLD_ACCEPTED** (no algorithm change). Diagnostics expose score distribution; out11 high segment counts remain an observability/product-tuning topic, not a blind code change in this correction wave.

## Remaining blockers

- Full out11 re-detect wall-time not re-measured in Wave 8 (use fixture + unit evidence).
- Interactive installed-GUI smoke on out11 recommended for human verification of timeline after install.
- Known Python 3.14 + PySide6 process crashes when stacking heavy Qt suites (external).
