# Phase 20 — Analysis Quality Presets

**Branch:** `feature/analysis-quality-presets`  
**Base:** `plan/phase19-analysis-resolution-golden-mean` @ `80afbbb` (Phase 19 not in master)  
**Status:** DONE  
**Date:** 2026-07-19  

Does **not** reopen Phase 18 or rewrite Phase 19 evidence. Dual-resolution invariants from Phase 19 remain mandatory.

---

## Product goal

Expose Pass1 `analysis_max_side` as user-facing **«Качество анализа»** presets in project settings, with correct semantics for:

| Case | Behavior |
|------|----------|
| New project | Explicit `analysis_max_side = 480` (FAST) |
| Legacy project missing field | Load as `None` (NATIVE historical) |
| Explicit JSON `null` | Stay `None` |
| Explicit number | Round-trip unchanged |
| Corrupted value | Validation error (no silent 480) |

Screenshots / PPTX stay full-res (Phase 19 Pass2).

---

## Presets (UI ↔ value)

| UI label | Code | `analysis_max_side` | Notes |
|---------|------|---------------------|-------|
| Быстрый — рекомендуется | FAST | `480` | Hermes evidence; new-project default |
| Повышенная детализация — экспериментально | DETAILED | `720` | Experimental; no Hermes claim |
| Исходная детализация | NATIVE | `None` | Historical detector behavior |
| Пользовательский режим | CUSTOM | user int 240–2160 | Validated |

Do not show «480p» / «720p» in UI.

---

## Parameter precedence (Detect / Auto)

```
explicit CLI/API override
  → Project.detection.analysis_max_side
  → (standalone CLI AppConfig only) VideoConfig.analysis_max_side
```

Project setting is source of truth for project-bound GUI/Auto/Detect. Global AppConfig does not override project when override is absent.

---

## Modules

| ID | Role |
|----|------|
| M-ANALYSIS-QUALITY | Preset enum, mapping, validation, NEW_PROJECT constant |
| M-ANALYSIS-SCALE | Existing; range validation for custom max_side |
| M-DOMAIN-PROJECT | `apply_detection_config`, new-project factory default |
| M-PERSIST-DTO | Missing field → None (not 480) |
| M-GUI-SETTINGS-PROJECT | «Качество анализа» combo + custom spin |
| M-GUI-MAIN | Confirm + apply via domain path |

---

## Dual-res invariants (unchanged)

1. ROI/masks in native coordinates  
2. evidence_observer sees native crop before scale  
3. Scale only before extract_features  
4. Pass2 full-res reps/PNG/PPTX  
5. None disables scale; no upscale  

---

## Implementation order

1. Plan + GRACE docs  
2. `analysis_quality.py` + validation range in `analysis_scale`  
3. Domain defaults split: new project explicit 480; DetectionConfig default None  
4. DTO missing → None  
5. `Project.apply_detection_config` + pipeline STALE for detect+downstream  
6. GUI presets + main_window confirm/no-op/cancel  
7. Tests + verification  

---

## 720 caveat

`720` is an experimental intermediate mode. **480** has Hermes evidence. Do not claim 720 is more accurate.
