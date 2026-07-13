# Step 18.4 Bottleneck Decision — Corrected Evidence Reconstruction

## Status: BLOCKED_INSUFFICIENT_DISCRIMINATION

**This corrected decision replaces the rejected draft at 27a28bf.**

No bottleneck class is accepted. No optimization is selected.

---

## 1. Evidence Source

- **Accepted benchmark:** `hermes-600s-recovered-r2-20260713-465d89e`
- **Evidence identities:**
  - `benchmark_code_head` = `465d89e243651e56a23e8c141632335bdd3a3303`
  - `benchmark_code_tree` = `66f9a5d50d7b97a34bfc151623d726fee2d03365`
  - `evidence_builder_head` = `3e3007cd9cb7f9e931acf8ccca1d8baa52fc5156`
  - `recovered_master_base` = `713ea07827f3efc9abec1b8db50768fe8ef9bad0`
- **Median run:** run-03 — 265.1246777999986s total
- **Mean:** 254.48840076666602s
- **Std dev:** 28.476225778418335s

---

## 2. Wall-Clock Stage Accounting (median run-03)

| Stage | Seconds | % | Notes |
|-------|---------|---|-------|
| extract_features | 101.6887 | 38.36% | Largest instrumented non-overlapping timer |
| pass2_collect | 65.2197 | 24.60% | Mixed: second decode + decode + segment matching + ROI + collection |
| unattributed_residual | 87.3865 | 32.96% | First-pass decode + service/metadata/persistence (not measured) |
| pass2_dedupe | 9.9022 | 3.73% | deduplicate_segments including extract_features on 84 reps |
| roi | 0.3374 | 0.13% | SlideRegion.process only |
| visual_distance | 0.2750 | 0.10% | Feature comparison only |
| threshold | 0.1708 | 0.06% | _resolve_threshold + compute_threshold |
| pass2_screenshots | 0.1389 | 0.05% | Screenshot output |
| debounce | 0.0054 | <0.01% | _debounce_changes |
| **Measured total** | **177.7382** | **67.04%** | |
| **Residual** | **87.3865** | **32.96%** | |

---

## 3. Pipeline Execution Model: SYNCHRONOUS

The current detection pipeline uses **synchronous generator consumption**:

```
decoder.iter_frames()       # generator — yields VideoFrame on .__next__()
    → pyav_iter_frames()    # for packet in container.demux(): packet.decode()
                              #   for frame: optional test, yield if sampled
    ↓
for timestamp, image in frames:   # detect_changes loop
    roi()                          # measure("roi")
    extract_features()             # measure("extract_features")
    visual_distance()              # measure("visual_distance")
    threshold()                    # measure("threshold")
    # loop body done → next advance
```

- **No producer thread:** The generator runs in the same thread as the consumer.
- **No feature worker pool:** All processing is single-threaded.
- **No async queue:** No bounded buffer between decode and feature extraction.
- **No overlap:** Packet.decode and extract_features execute serially. Each sampled frame is fully processed before the next decode advance.

**Therefore:** Claims in the 27a28bf draft about "producer-consumer overlap", "asynchronous overlap", or "decode occurring in parallel with feature extraction" are **false** for the current accepted source code.

---

## 4. cProfile Evidence (profile run: 229.750s)

### Key Entries

| Function | Cumulative (s) | Self (s) | Calls |
|----------|-------|----------|-------|
| pyav_iter_frames | 135.128 | 10.469 | 2404 |
| Packet.decode | 114.854 | 114.854 | 72004 |
| extract_features | 92.712 | 0.039 | 1285 |
| compute_histogram | 48.842 | 0.887 | 1285 |
| cv2_calc_hist | 47.946 | 0.311 | 3855 |
| numpy histogram | 40.567 | 36.744 | 3855 |
| cv2_to_gray | 34.049 | 32.438 | 1285 |
| to_ndarray | 9.580 | 9.580 | 2402 |
| phash | 3.898 | — | 1285 |
| dhash | 3.130 | — | 1285 |

### Overlap Rules

All parent/child pairs are **nested cumulative contexts** — do NOT add their cumulative times:

- `pyav_iter_frames` → `Packet.decode` — decode is subset of iter_frames
- `pyav_iter_frames` → `to_ndarray` — to_ndarray is subset of iter_frames
- `extract_features` → `compute_histogram` → `cv2_calc_hist` → `numpy histogram` — all subsets
- `extract_features` → `cv2_to_gray` — subset

### Call Reconciliation

- `extract_features` calls: **1285**
- Pass 1 sampled frames (features_full): **1201**
- Representative frames (extract_features from dedupe): **84**
- **1201 + 84 = 1285** ✓  (not 18018 — feature extraction is on sampled frames only, not every decoded frame)

---

## 5. Counter-Invariants

| Counter | Value |
|---------|-------|
| frames_decoded | 72002 |
| frames_sampled | 1201 |
| features_full | 1201 |
| pass2_frames_sampled | 1201 |
| ndarray_conversions | 2402 (1201 Pass 1 + 1201 Pass 2) |
| representative_frames | 84 |
| screenshots_written | 6 |

---

## 6. Candidate Evaluation

### FEATURE_EXTRACTION_CPU
- **Wall-clock:** 101.69s (38.36%) — largest instrumented timer
- **Profile:** 92.712s cumulative; subsystem compute_histogram (48.842s) + cv2_to_gray (34.049s)
- **For:** Largest measured stage by wide margin. Sub-components are well-understood pixel ops.
- **Against:** Residual (87.39s, 32.96%) is nearly as large and likely contains first-pass decode (aggregate note: decode/open/service/persistence and other uninstrumented work). Without isolating decode wall-clock, cannot confirm extract_features exceeds decode.
- **Confidence: MEDIUM** — possible primary but unconfirmed

### DECODE_FRAME_PIPELINE
- **Wall-clock:** No independent timer. Decode lives in residual (87.39s, 32.96%).
- **Profile:** Packet.decode 114.854s self (larger than extract_features 92.712s cumulative)
- **For:** Profile suggests decode work exceeds feature extraction. Residual is large.
- **Against:** The profile run (229.750s) is a separate instrumented run with a different elapsed time from the median recorded run (265.125s); cProfile is supporting evidence and cannot substitute for isolated median wall-clock stage timers. No wall-clock timer validates this.
- **Confidence: MEDIUM** — possible primary but no direct wall-clock evidence

### PASS2_COLLECTION
- **Wall-clock:** 65.22s (24.60%) — mixed timer with second decode + collection
- **For:** Second-largest measured stage.
- **Against:** Pure collection overhead is NOT independently measured — it is entangled with second-pass decode/frame advancement within the same mixed timer. The internal proportion between collection cost and decode cost is UNKNOWN. Cannot select as primary because no wall-clock timer isolates collection from decode.
- **Confidence: LOW** — not primary; mixed timer cannot isolate pure collection

### THRESHOLD_OR_DECISION_LOGIC
- Combined: <0.5s (<0.2%) — negligible
- **Confidence: HIGH** — clearly not a bottleneck

### MIXED_OR_UNRESOLVED
- This is the honest fallback. Neither FEATURE_EXTRACTION_CPU nor DECODE_FRAME_PIPELINE can be safely discriminated with current instrumentation.
- **Confidence: HIGH**

---

## 7. Decision

| Field | Value |
|-------|-------|
| **Status** | `BLOCKED_INSUFFICIENT_DISCRIMINATION` |
| **Selected class** | `NONE` |
| **Selected optimization** | `NONE` |
| **Decision confidence** | LOW |
| **Evidence gap** | Missing independent wall-clock timers for pass1_decode, pass2_decode, pass2_match_and_collect. Without these, residual (87.4s, 33%) cannot be attributed, and FEATURE_EXTRACTION_CPU vs DECODE_FRAME_PIPELINE cannot be safely discriminated. |
| **F-0097** | Documents this evidence gap |

---

## 8. Run Variance Analysis

| Run | Total (s) | extract_features (s) | pass2_collect (s) | pass2_dedupe (s) | Residual (s) |
|-----|-----------|---------------------|-------------------|------------------|-------------|
| run-01 | 276.12 | 117.37 (42.5%) | 62.91 (22.8%) | 6.08 (2.2%) | 88.77 (32.1%) |
| run-02 | 222.22 | 85.77 (38.6%) | 52.98 (23.8%) | 6.19 (2.8%) | 76.49 (34.4%) |
| run-03 | 265.12 | 101.69 (38.4%) | 65.22 (24.6%) | 9.90 (3.7%) | 87.39 (33.0%) |

**Directional stability:** extract_features is consistently the largest measured stage (38-43%), pass2_collect is consistently second (23-25%), residual is consistently ~32-34%. The stage structure is stable across runs, but the absolute values vary significantly (std dev 28.5s).

**Variance impact:** High run-to-run variance reduces confidence in any single-run-based classification. The 85.8s–117.4s range for extract_features spans ~27% variation, indicating that system noise (GPU clock, memory bandwidth contention, OS scheduling) plays a meaningful role.

---

## 9. F-0088 Status

OPEN — 28 slides detected, 6 PNG screenshots written. This is a pre-existing quality observation, not run variance as incorrectly stated in the 27a28bf draft.

---

## 10. What the 27a28bf Draft Got Wrong

| Issue | 27a28bf claim | Correct evidence |
|-------|---------------|------------------|
| pass2_collect value | 10.9s (4.1%) | 65.22s (24.6%) |
| visual_distance value | ~12.4s (~4.7%) | 0.275s (0.1%) |
| extract_features cProfile | 107.3s cumulative | 92.712s cumulative |
| phash cProfile | ~9.9s cumulative | 3.898s cumulative |
| dhash cProfile | ~8.5s cumulative | 3.130s cumulative |
| Pipeline model | Async producer-consumer overlap | Synchronous generator consumption |
| Frame count | 18018 frames feature-extracted | 1201 sampled + 84 dedupe = 1285 calls |
| Decode/extract overlap | Claimed "asynchronous" | Serial execution in for loop |
| F-0088 meaning | Run variance | 28 slides / 6 PNGs |
| Acceptance gates | Quality tolerance (5%/10%/1.5s) | Exact canonical signature parity |

---

## 11. Historical Context

- **F-0087 (DECODE_PROFILE):** From the regressed benchmark. Not carried forward to this decision.
- **F-0088:** 28 slides / 6 PNGs — remains OPEN.
- **F-0096:** 27a28bf draft documented as rejected; corrected in this commit.
- **F-0097:** Evidence gap — missing instrumentation for first-pass and second-pass decode wall-clock.
