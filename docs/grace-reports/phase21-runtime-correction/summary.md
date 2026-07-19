# Phase 21 Runtime Correction — Evidence Summary

**Branch:** `fix/phase21-runtime-detection-timeline`  
**Base:** `origin/feature/phase21-clean-windows-user-journey` @ f388350  
**Date:** 2026-07-19

## Commits

1. `docs(grace): record Phase 21 runtime defect baseline`
2. `fix(timeline): defer item mutations and remove Qt virtual monkeypatches`
3. `fix(progress): propagate monotonic two-pass detection progress`
4. `refactor(settings): extract rollback workflow from Qt adapter`
5. `fix(detect): make stable-duration debounce time-based`
6. `feat(detect): expose candidate-to-final slide counts`
7. `perf(detect): stream full-resolution representative frames`
8. `test(runtime): verify timeline progress and streaming detection`

## Decisions

| Wave | Decision |
|------|----------|
| 1 Forensics | WAVE_ACCEPTED |
| 2 Timeline | WAVE_ACCEPTED |
| 3 Progress | WAVE_ACCEPTED |
| 4 Qt-free settings | WAVE_ACCEPTED |
| 5 Duration semantics | WAVE_ACCEPTED |
| 6 Diagnostics | WAVE_ACCEPTED; AUTO_THRESHOLD_ACCEPTED (no algo change) |
| 7 Streaming Pass2 | WAVE_ACCEPTED |
| 8 Acceptance | WAVE_ACCEPTED (fixture + automated; full out11 re-detect optional) |

## Test gates

- Targeted timeline / progress / settings / detect / streaming: PASS
- Bounded domain+application+gui+detect subset: PASS
- Ruff on changed paths: PASS
- Full suite: not required for this wave set
