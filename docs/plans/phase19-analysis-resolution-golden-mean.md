# Phase 19 — Analysis Resolution & Golden Mean

**Branch:** `plan/phase19-analysis-resolution-golden-mean`  
**Status:** DONE — Steps 19.0–19.9 accepted; runtime default `analysis_max_side=480`  
**Date:** 2026-07-18  
**Hermes result:** `analysis_max_side=480` → ~**2.15×** wall, extract **−93%**, gates PASS  
**Does not reopen Phase 18.** Phase 18 terminal outcome remains  
`T3_NO_EVIDENCE_SUPPORTED_TARGET_OPTIMIZATION` / `selected_optimization=NONE`.

---

## 1. Purpose

Determine whether **analysis-path resolution reduction** (and optionally lower
`sample_fps`) can speed up slide detection without violating quality gates, and
select a reproducible **golden-mean** configuration for educational videos.

This is a **new research track**, not a continuation of Phase 18 C1/C2/C3
(seek reuse, rolling retention, thread_count). Those candidates already failed
combined parity/performance gates. Analysis resolution was **never**
discriminated.

---

## 2. Problem statement

### Measured baseline (Phase 18, Hermes 600s, sample_fps=2)

| Stage | ~Share | Notes |
|-------|--------|-------|
| Pass1 decode/frame advance | 35% | demux + Packet.decode + to_ndarray |
| extract_features | 34% | pHash, dHash, hist, gray thumb |
| Pass2 decode/frame advance | 28% | second full sequential pass |
| Other | ~3% | ROI, distance, threshold, PNG write |

### Architectural mismatch

1. Detector decisions use **48×48 gray_thumb (80% weight)** plus tiny hashes/hist weights.
2. Pipeline still feeds **full-resolution RGB** into `extract_features` (after ROI).
3. Full resolution **is** required for export screenshots (Pass 2 representatives).
4. Therefore analysis quality budget ≠ screenshot quality budget.

**Hypothesis (H19):** Downscaling the analysis path to `analysis_max_side ∈ {960,640,480}`
after ROI (or via reformat) cuts feature CPU and RGB transfer, while Pass 2 still
writes native screenshots. Quality gates remain satisfiable for lecture-style content.

---

## 3. Non-goals

- Do **not** change Phase 18 accepted evidence or reopen Step 18.5 under C1/C2/C3.
- Do **not** claim HWAccel speedup without new runtime proof.
- Do **not** require exact byte-identity of scores vs native (scores **will** change).
  Quality is measured by segment alignment / missed / false_split / timestamp error.
- Do **not** degrade screenshot resolution for accepted slides.
- Do **not** use LLM for slide-change detection (CV remains primary).

---

## 4. Module breakdown

| ID | Name | Type | Role |
|----|------|------|------|
| M-ANALYSIS-SCALE | AnalysisScale | UTILITY | Config + pure helpers: `analysis_max_side`, scale policy, coordinate mapping |
| M-FRAME-FEATURES | FrameFeatures (extend) | CORE_LOGIC | Extract features on analysis-sized frames; optional cheap path |
| M-DETECT-SLIDES | DetectSlides (extend) | CORE_LOGIC | Dual-res path: Pass1 analysis scale, Pass2 full-res reps |
| M-SLIDE-DETECTOR | SlideDetector (touch) | CORE_LOGIC | Optional scale after ROI before extract; metrics tags |
| M-CONFIG | Config (extend) | UTILITY | `VideoConfig.analysis_max_side`, defaults, CLI/YAML |
| M-GOLDEN-MEAN-SWEEP | GoldenMeanSweep | TOOL | Grid sweep tool + segment quality metrics vs reference |
| M-GOLDEN-MEAN-DECISION | GoldenMeanDecision | DECISION | Decision artifact: selected defaults + gates |

### Contracts (planned)

#### M-ANALYSIS-SCALE

```
PURPOSE: Define analysis-resolution policy separate from screenshot resolution.
SCOPE:   analysis_max_side (None|int), scale_frame(image), map_roi_if_needed
INPUTS:  RGB ndarray H×W×C, max_side: int | None
OUTPUTS: scaled RGB ndarray (same aspect), scale_factor metadata
SIDE_EFFECTS: none
RULES:
  - max_side is None or 0 → identity (native)
  - only downscale when max(H,W) > max_side
  - INTER_AREA preferred for downscale
  - never upscale
```

#### Dual-resolution detect path

```
Pass 1 (detect):
  decode full → ROI/masks → analysis_scale → extract_features → distances → segments

Pass 2 (export):
  decode full → match rep timestamps → crop ROI at FULL res → dedupe → PNG
  (no analysis_scale on written screenshots)
```

---

## 5. Data flows

```
                    ┌─────────────────────────────┐
 video ──decode──►  │ Pass 1: sampled frames      │
                    │  ROI → scale(max_side)      │
                    │  features → scores          │
                    │  debounce → segments        │
                    └─────────────┬───────────────┘
                                  │ segment times + rep_ts
                    ┌─────────────▼───────────────┐
                    │ Pass 2: second decode       │
                    │  grab reps at FULL res      │
                    │  dedupe + write PNG          │
                    └─────────────────────────────┘

Sweep tool (offline):
  for (max_side, sample_fps) in GRID:
    run detect → compare segments to REF → metrics.json
  decide golden_mean.json
```

---

## 6. Golden-mean definition

### Hard quality gates (MVP, AGENTS.md)

| Gate | Threshold |
|------|-----------|
| missed_slide_rate | ≤ 5% |
| false_split_rate | ≤ 10% |
| timestamp_error_seconds | ≤ 1.5 s (at sample_fps=2; scale budget with fps grid) |

### Performance preference

Among configurations that pass hard gates:

1. Prefer higher `processing_x_realtime` (lower wall-clock).
2. Break ties toward higher `analysis_max_side` (safer quality).
3. Break remaining ties toward higher `sample_fps` (finer timestamps).

### Optional utility (recorded, not sole decider)

```
U = T_ref/T - λ_m·missed - λ_f·false_split - λ_t·(err_t / err_budget)
λ_m=10, λ_f=5, λ_t=2  (documented defaults; adjustable)
```

**Golden mean** = argmax U among gate-passers, reported with knee plot data.

---

## 7. Sweep protocol

### Parameter grid (minimum)

| Dimension | Values |
|-----------|--------|
| `analysis_max_side` | `null` (native), 960, 640, 480, 320 |
| `sample_fps` | 2.0, 1.0, 0.5 |

= 15 cells. Median of 3 runs for wall-clock on short clip; 1 run OK for synthetic fixture.

### Reference

- **Primary short clip:** Hermes 600s canonical (local-only, not committed) when available.
- **Synthetic:** `tests/fixtures/test_slides.mp4` for CI-safe regression of scale helpers.
- **Reference segments:** native `analysis_max_side=null`, `sample_fps=2.0` on same code HEAD.

### Per-cell metrics

- wall_clock_seconds (median)
- slides_count, score_count
- segment alignment to REF (interval IoU / greedy match)
- missed_slide_rate, false_split_rate
- mean/median absolute timestamp error on matched boundaries
- screenshots: PNG count + full-res shape check (assert native height/width of crop)
- stage timers: extract_features, pass1/pass2 decode (reuse DetectionRunMetrics)

### Content stratification (recommended, not blocking v1)

| Class | Example | Why |
|-------|---------|-----|
| layout-change lecture | Hermes-like | large visual jumps |
| dense text / code | future clip | small text-only changes |
| bullet builds | future clip | frequent partial updates |

v1 may complete decision on Hermes + synthetic if other clips unavailable; document limitation.

---

## 8. Implementation order (after approval)

| Step | Name | Status after plan | Depends |
|------|------|-------------------|---------|
| 19.0 | Plan freeze (this document + XML artifacts) | **in progress / done on merge of plan** | — |
| 19.1 | Contracts + config schema (`analysis_max_side`) | planned | 19.0 approve |
| 19.2 | `scale_for_analysis` helper + unit tests | planned | 19.1 |
| 19.3 | Wire Pass1 scale into detect path; Pass2 full-res invariant | planned | 19.2 |
| 19.4 | Metrics: tag analysis shape, scale factor | planned | 19.3 |
| 19.5 | Golden-mean sweep tool + quality comparison | planned | 19.3 |
| 19.6 | Short-clip discrimination run + evidence package | planned | 19.5 |
| 19.7 | Decision: selected defaults or NONE | planned | 19.6 |
| 19.8 | Optional: adopt defaults in config.example / project defaults | planned | 19.7 select≠NONE |
| 19.9 | Acceptance: gates + docs refresh | planned | 19.7 |

**Stop conditions**

- Quality gates fail on all downscale cells → accept `selected_analysis_scale=NONE`, document negative outcome (like Phase 18 T3).
- Pass2 screenshots drop below full res → hard fail, do not ship.
- Diff touches modules outside write-scope without contract update → stop.

---

## 9. Verification surface

| ID | Purpose |
|----|---------|
| V-M-ANALYSIS-SCALE | Unit: scale identity, no-upscale, aspect, INTER_AREA |
| V-M-DETECT-ANALYSIS-SCALE | Detect path: Pass1 uses scaled; PNG still full-res crop |
| V-M-GOLDEN-MEAN-SWEEP | Tool emits grid artifacts + metrics schema |
| V-M-GOLDEN-MEAN-DECISION | Decision JSON: selected params or NONE + gates |
| V-M-PHASE19-ACCEPTANCE | End gates: quality + documented defaults |

Existing Phase 18 V-entries remain unchanged in meaning.

---

## 10. Risk assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Text-only slide changes missed at 480/320 | missed_slide_rate | Prefer 640/960; stratify content |
| Auto threshold shifts with score magnitude | false splits | Recompute threshold on scaled scores; compare segments not raw scores |
| Users expect exact score CSV parity | confusion | Document soft parity; gates on segments |
| Decode still dominates → small speedup | disappointment | Report stage breakdown; don't oversell |
| ROI coordinates vs scaled frames | bugs | Scale **after** ROI in native coords |
| Reopening Phase 18 by accident | process drift | Explicit non-goal; separate module IDs |

---

## 11. Candidate defaults (hypotheses only — not selected)

| Use case | analysis_max_side | sample_fps |
|----------|-------------------|------------|
| Conservative | 960 | 1.0 |
| **Suspected golden mean** | **640** | **1.0** |
| Aggressive lecture | 640 | 0.5 |
| Preview / Quick | 320 | 0.5 |

Selection requires Step 19.6–19.7 evidence.

---

## 12. Write-scope for first execution wave (19.1–19.4)

```
src/video2pptx/config.py
src/video2pptx/roi.py                    # only if needed; prefer scale after process()
src/video2pptx/frame_features.py         # optional extract path helpers
src/video2pptx/slide_detector.py         # optional scale hook + metrics
src/video2pptx/detect_slides.py          # dual-res orchestration
src/video2pptx/domain/project.py         # VideoConfig persistence if required
config.example.yaml
tests/test_config.py
tests/test_analysis_scale.py             # new
tests/test_detect_slides.py              # extend
tests/test_frame_features.py             # if needed
docs/*                                   # refresh after implement
```

Tools wave (19.5+):

```
tools/sweep_analysis_resolution.py      # new
tools/README.md
benchmarks/detect/evidence/phase19-*/    # evidence only
```

---

## 13. Relationship to Phase 18

| Topic | Phase 18 | Phase 19 |
|-------|----------|----------|
| Bottleneck | DECODE_FRAME_PIPELINE primary | Features + transfer secondary lever |
| Candidates | C1 seek, C2 retention, C3 threads | Analysis max_side × sample_fps |
| Outcome | NONE selected | TBD after sweep |
| Exact score parity | required for those candidates | **not** required |
| Screenshots | full res | full res (invariant) |

Phase 18 Step 18.5 remains planned/blocked under **old** candidates.  
Phase 19 may later unlock a **different** optimization class without rewriting 18.4.

---

## 14. Approval checklist

- [x] User approves this plan (scope, gates, dual-res invariant).
- [x] On approval: treat Step 19.0 as done; start 19.1 implementation via grace-execute.
- [x] Steps 19.1–19.4 implemented (config, helper, dual-res path, metrics).
- [x] Steps 19.5–19.8: sweep tool, Hermes measurements, decision 480, config.example.
- [x] Step 19.9: acceptance — runtime default 480 enabled; Phase 19 closed.

### Implemented API (19.1–19.4)

- `VideoConfig.analysis_max_side: int | None = None`
- `scale_for_analysis(image, max_side) -> (image, scale_factor)` in `analysis_scale.py`
- CLI: `--analysis-max-side` on `detect` / `detect-slides`
- Domain `DetectionConfig.analysis_max_side` + project.json DTO/mapper
- Metrics gauges: `analysis_max_side`, `analysis_height`, `analysis_width`, `analysis_scale_factor`

---

## 15. Links

- Research context: conversation 2026-07-18 independent study
- Phase 18 decision: `benchmarks/detect/evidence/bottleneck_decision.md`
- F-0104: analysis resolution not discriminated in Phase 18
- Development plan: `docs/development-plan.xml` Phase-19
- Verification: `docs/verification-plan.xml` V-M-ANALYSIS-SCALE …
- Graph: `docs/knowledge-graph.xml` M-ANALYSIS-SCALE …
