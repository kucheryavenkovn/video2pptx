# Step 18.4 Bottleneck Decision — Corrected

## Status: BLOCKED_TARGET_OPTIMIZATION_NOT_DISCRIMINATED

**Selected bottleneck class:** DECODE_FRAME_PIPELINE
**Decision confidence:** HIGH
**Selected optimization:** NONE

**F-0097:** RESOLVED — decoder/frame advancement pipeline wall-clock captured.
**F-0098:** PARTIALLY_RESOLVED — canonical Hermes H.264 runtime evidence collected; `codec_context_is_hwaccel=true` confirmed; `actual_hardware_decode_active` remains UNKNOWN_NOT_PROVEN (observer design; conclusion confidence NOT_ESTABLISHED; observation completeness confidence HIGH); no targeted optimization selected.
**F-0100:** RESOLVED — canonical Hermes H.264 clip located and copied local-only (not committed).
**Strict fallback control:** `INVALID_SUPPORTING_CONTROL_IMPLEMENTATION_DEFECT` (premature `break` after the first demuxed packet) — NOT a runtime signal, carries no evidentiary weight; must be corrected before the next HWAccel evidence decision.

---

## 1. Evidence Source (unchanged from previous decision)

- **Benchmark sequence:** `hermes-600s-f0097-instrumented-20260713-acb424f`
- **Evidence identities:**
  - `benchmark_code_head` = `acb424f904bc4b3459f6ad2ceb9f8c701cedb69b`
  - `benchmark_code_tree` = `6a7a596b802fa77465288136d4ea309a50557f2a`
  - `evidence_builder_head` = `acb424f904bc4b3459f6ad2ceb9f8c701cedb69b`
  - `recovered_master_base` = `836a456eee0312646747d755dfe838052eaa6752`
- **Median run:** run-01 — 272.5658s
- **Mean:** 277.2175s
- **Std dev:** 32.5005s

---

## 2. Wall-Clock Stage Accounting (unchanged)

| Stage | Seconds | % | Notes |
|-------|---------|---|-------|
| pass1_decode_or_frame_advance | 96.3635 | 35.35% | Pass 1 generator advancement (demux + Packet.decode + to_ndarray) |
| extract_features | 92.6178 | 33.98% | Feature extraction on ROI-cropped frames |
| pass2_decode_or_frame_advance | 76.0936 | 27.92% | Pass 2 generator advancement (same decode pipeline, second pass) |
| pass2_dedupe | 6.0939 | 2.24% | deduplicate_segments including extract_features on 84 reps |
| roi | 0.3175 | 0.12% | SlideRegion.process only |
| visual_distance | 0.2616 | 0.10% | Feature comparison only |
| threshold | 0.1440 | 0.05% | _resolve_threshold + compute_threshold |
| pass2_screenshots | 0.0910 | 0.03% | cv2.cvtColor + cv2.imwrite for 6 PNGs (no to_ndarray call) |
| pass2_match_and_collect | 0.0436 | 0.02% | Segment scanning, rep matching, rep_frames insertion |
| debounce | 0.0100 | <0.01% | _debounce_changes |
| **Measured total** | **272.0364** | **99.81%** | Sum of all canonical non-overlapping stage timers |
| **Residual** | **0.5293** | **0.19%** | Container setup, metadata, service overhead, timer overhead |

**F-0097 impact:** Residual dropped from 87.39s (33.0%) to 0.53s (0.19%). All decoder/frame advancement pipeline work is now captured by non-overlapping wall-clock timers. Note: the measured region is the "decoder/frame advancement pipeline" — it includes generator advancement, demux/decode, Packet.decode, sampling logic before yield, and VideoFrame.to_ndarray for sampled frames. It is NOT pure Packet.decode wall-clock.

---

## 3. Pipeline Execution Model (unchanged)

```
decoder.iter_frames()       # generator — yields VideoFrame on .__next__()
    → pyav_iter_frames()    # for packet in container.demux(): packet.decode()
                              #   for frame: test_sample, to_ndarray, yield if sampled
    ↓
for timestamp, image in frames:   # detect_changes loop
    roi()                          # measure("roi")
    extract_features()             # measure("extract_features")
    visual_distance()              # measure("visual_distance")
    threshold()                    # measure("threshold")
    # loop body done → next advance
```

- Single-threaded generator consumption. No producer thread, no worker pool, no async queue.
- `Packet.decode` and `extract_features` are serial — no overlap.

---

## 4. Directional Stability (unchanged)

| Run | pass1_decode_advance | pass2_decode_advance | Decode Pipeline Total | extract_features | Gap |
|-----|---------------------|---------------------|---------------------|-----------------|-----|
| run-01 | 96.36s (35.35%) | 76.09s (27.92%) | **172.46s (63.27%)** | 92.62s (33.98%) | **79.84s (29.29%)** |
| run-02 | 114.76s (36.81%) | 52.90s (16.97%) | **167.65s (53.77%)** | 136.39s (43.75%) | **31.26s (10.03%)** |
| run-03 | 97.14s (39.28%) | 53.78s (21.75%) | **150.91s (61.03%)** | 88.43s (35.76%) | **62.49s (25.27%)** |

**Stability:** Decode pipeline total exceeds extract_features in ALL runs. Gap is directionally stable (31.26s–79.84s).

---

## 5. Counter-Invariants (unchanged)

| Counter | Value |
|---------|-------|
| frames_decoded | 72002 |
| frames_sampled (per pass) | 1201 |
| ndarray_conversions | 2402 (1201 Pass 1 + 1201 Pass 2) |
| representative_frames | 84 |
| screenshots_written | 6 |
| slides_detected | 28 |
| Canonical signature | `8cc06c6accb055fb6fed461f2f4a96f0b288ef864b9423000b6f59d9ab56bc85` |

---

## 6. Candidate Evaluation (unchanged)

### DECODE_FRAME_PIPELINE — PRIMARY
- **Wall-clock:** 172.46s (63.27%) — pass1 (35.35%) + pass2 (27.92%) decode advancement.
- **Evidence:** Directly measured by new non-overlapping timers. Residual near zero (0.19%) confirms full capture.
- **Profile:** Packet.decode 114.85s self — largest single function.
- **Ruling: PRIMARY.** Dominant bottleneck. Decode runs identical code in both passes.

Other candidates (FEATURE_EXTRACTION_CPU, PASS2_COLLECTION, THRESHOLD_OR_DECISION_LOGIC, MIXED_OR_UNRESOLVED) all ruled NOT_PRIMARY as before.

---

## 7. Decision

| Field | Value |
|-------|-------|
| **Status** | `BLOCKED_TARGET_OPTIMIZATION_NOT_DISCRIMINATED` |
| **Selected bottleneck class** | `DECODE_FRAME_PIPELINE` |
| **Decision confidence** | HIGH |
| **Selected optimization** | `NONE` |
| **F-0097** | RESOLVED — decoder/frame advancement pipeline wall-clock captured. |
| **F-0098** | PARTIALLY_RESOLVED — canonical Hermes H.264 runtime evidence collected; activation still UNKNOWN_NOT_PROVEN (conclusion confidence NOT_ESTABLISHED). |
| **F-0100** | RESOLVED — canonical clip located and copied local-only. |
| **Strict fallback control** | INVALID_SUPPORTING_CONTROL_IMPLEMENTATION_DEFECT (premature `break`); not a runtime signal; must be fixed before next evidence decision. |

---

## 8. Rejected Optimization: PYAV_HWACCEL_CUDA

**Status:** REJECTED_SOURCE_MODEL_MISMATCH

**Hypothesis (rejected):** Add `hwaccel=cuda` to PyAV `av.open()` to offload H.264 Packet.decode from CPU to GPU.

**Why rejected:** Source audit at the Step 18.4 candidate HEAD (`acb424f`) at which PYAV_HWACCEL_CUDA was evaluated proved the `pyav_iter_frames` at **that HEAD** already:
1. Prefers `"cuda"` first in `_HW_PREFERRED`
2. Calls `_pick_hw_device()` which selects the best available HW device
3. Calls `_create_hwaccel(hw_device)` to create a `HWAccel` object
4. Passes `hwaccel=hwaccel` to `av.open(str(video_path), hwaccel=hwaccel)`

> **Historical source state (traceability only).** The list above describes the source at the rejection HEAD (`acb424f`), preserved for traceability. It is **not** a current-source claim. The **current production** `pyav_iter_frames` (merged master HEAD `da35cf34`) calls `_create_hwaccel_with_evidence()` (the evidence-capturing variant) instead of the plain `_create_hwaccel()`; the plain helper still exists but is not invoked by the production decode path.

The hypothesized intervention already existed in source at that HEAD. No committed benchmark evidence proves whether hardware decode was actually active at runtime (see F-0098).

**False source assumptions:**
- "PyAV defaults to software H.264 decoder" — contradicted by `_HW_PREFERRED = ["cuda", ...]`
- "Step 18.5 needs to add hwaccel=cuda to av.open()" — already present
- "Existing benchmark decode is definitely software-only" — no runtime evidence supports this

**Historical context:** This hypothesis was the initial Step 18.4 decision before source audit. It is preserved in git history for traceability.

---

## 9. Optimization Candidate Evaluation

### HWACCEL_RUNTIME_OBSERVABILITY_AND_FALLBACK
- **Type:** Evidence/observability, not optimization.
- **Current behavior:** Canonical Hermes H.264 runtime evidence now collected (2026-07-14). Observer captured: `requested_hw_device=cuda`, `hwaccel_object_created=true` (no creation error), `container_opened_with_hwaccel=true`, raw `codec_context.is_hwaccel=true`, `allow_software_fallback=true`, `actual_hardware_decode_active=UNKNOWN_NOT_PROVEN` (by design).
- **Verdict:** Observability gap closed and exercised on the canonical clip. Cannot be the sole optimization for Step 18.5.

### PYAV_HARDWARE_DECODE_ACTIVATION_OR_FALLBACK_FIX
- **Type:** Conditional optimization (requires direct runtime proof of an activation defect).
- **Current evidence:** NONE — canonical Hermes H.264 production-path evidence does NOT directly prove hardware decode was inactive and does NOT directly prove a software fallback occurred (`actual_hardware_decode_active = UNKNOWN_NOT_PROVEN` by observer design; conclusion confidence NOT_ESTABLISHED). The strict fallback control is `INVALID_SUPPORTING_CONTROL_IMPLEMENTATION_DEFECT` (premature `break`) and provides no signal.
- **Verdict:** Not viable. No activation defect is directly proven, so no bounded activation/fallback fix can be selected.

### SECOND_PASS_DECODE_ELIMINATION_OR_REUSE
- **Target:** Save ~76s (27.92%) from pass2_decode_or_frame_advance.
- **Challenge:** Representative timestamps become known only after Pass 1. Retaining all 1201 sampled frames costs ~7 GB. Current representative_frames = 84 (522547200 bytes).
- **Verdict:** Requires detailed design analysis. Not a bounded single intervention.

### PYAV_DECODE_CONFIGURATION_TUNING
- **Current evidence:** NONE — no committed benchmark evidence under alternative configs.
- **Challenge:** Baseline 1.6ms/frame Packet.decode may already use hardware path.
- **Verdict:** Undetermined without evidence.

### MIXED_OR_INSUFFICIENT_OPTIMIZATION_DISCRIMINATION
- **This is the honest outcome.** Bottleneck class known; exact optimization not yet discriminated.
- **Step 18.5 remains planned but blocked.**

---

## 10. Step 18.6 Gate Parity

No optimization-specific performance gate is selected. The following exact output parity requirements are immutable regardless of optimization choice:

| Gate | Requirement | Source |
|------|-------------|--------|
| Canonical signature | `8cc06c6accb055fb6fed461f2f4a96f0b288ef864b9423000b6f59d9ab56bc85` | Decision JSON |
| Slides count | 28 | Decision JSON |
| Score count | 1200 | Decision JSON |
| Screenshots written | 6 | Decision JSON |
| Actual PNG count | 6 | Decision JSON |
| sample_fps | 2.0 | Decision JSON |
| Two-pass semantics | Preserved | Decision JSON |
| Cancellation | Preserved | Decision JSON |
| Progress | Preserved | Decision JSON |
| GUI/MCP/CLI public semantics | Preserved | Decision JSON |

Step 18.8 broad tolerances (missed_slide_rate <= 5%, false_split_rate <= 10%, timestamp_error <= 1.5s) remain under V-PERF-DETECT-ACCEPTANCE only.

---

## 11. F-0097 Status

**RESOLVED**

F-0097 documented the evidence gap where decoder/frame advancement pipeline work was hidden in the unattributed residual (87.39s, 33.0%). Three new InstrumentedIterator-based wall-clock timers were added:

- `pass1_decode_or_frame_advance` — measures Pass 1 generator advancement (demux + Packet.decode + to_ndarray + sampling logic)
- `pass2_decode_or_frame_advance` — measures Pass 2 generator advancement
- `pass2_match_and_collect` — measures Pass 2 loop body (non-decode collection overhead)

All three timers use `time.perf_counter()` before/after `self._it.__next__()`, including StopIteration exhaustion and exception paths.

**Terminology correction:** The measured region is the "decoder/frame advancement pipeline" — it includes generator advancement, demux iteration, Packet.decode work, sampling logic before yield, and VideoFrame.to_ndarray for sampled frames. It is NOT pure Packet.decode wall-clock.

**Result:** Residual reduced from 87.39s (33.0%) to 0.53s (0.19%).

---

## 12. F-0098 — HWAccel Runtime Activation Evidence Gap

**Status:** PARTIALLY_RESOLVED

**Problem:** Step 18.4 has selected DECODE_FRAME_PIPELINE with HIGH confidence, but the proposed PYAV_HWACCEL_CUDA optimization is invalid because current source already requests HWAccel. Accepted benchmark evidence does not record actual HWAccel activation or software fallback state, so a targeted decoder optimization cannot yet be selected safely.

**Required evidence:**
- `requested_hw_device`
- `hwaccel_object_created`
- `container_opened_with_hwaccel`
- `codec_context_is_hwaccel` (raw `codec_ctx.is_hwaccel`)
- `actual_hardware_decode_active` (interpreted: true/false/UNKNOWN_NOT_PROVEN)
- `software_fallback_detected`
- `software_fallback_reason`
- `codec_name`
- `codec_long_name`
- Hardware decoder/device identity (where PyAV exposes it)

**Step 18.4A canonical evidence run (2026-07-14) — outcome OUTCOME_D:**

Evidence mechanism **implemented, corrected, and exercised on the canonical Hermes H.264 clip** (SHA256 `dd9da3442e91ab7f17f0405198aa8e39d1538d74518b6b9a3b1e61ac2fc0f5a4`; h264, 1920x1080, 60 fps, 600.016667 s):
- Evidence code HEAD = `da35cf3456c16aa662fc573b03a126a59ec89a25` (= `BLOCKED_STEP_18_4A_MASTER_HEAD`); tree = `713b8e7fdfbd5c7f127e60f5ebe64a393eb4b419`
- Canonical runtime evidence commit = `9b4cc54949537b2a36e70a0f98f1cb732d6688b2`
- Evidence dir = `benchmarks/detect/evidence/hwaccel-runtime-hermes-h264-20260714/`
- Two independent opens, 1 frame consumed per open, `sample_fps=2.0`, canonical mode on; observations consistent.

**Canonical observations (both identical):**
- `available_hw_devices = [cuda, d3d12va, d3d11va, qsv, dxva2]`
- `requested_hw_device = cuda`; `hwaccel_requested = true`; `hwaccel_object_created = true` (no creation error)
- `container_opened_with_hwaccel = true`; `allow_software_fallback = true`
- `codec_context_hwaccel_present = true`; `codec_context_is_hwaccel = true` (raw PyAV property)
- `hw_config_present = false` (`hw_config_device_type/format = null`)
- `codec_name = h264`; `codec_long_name = H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10`; `deterministic_hardware_identity = requested=cuda`
- `first_frame_yielded = true`; `first_frame_timestamp = 0.0`; `first_frame_shape = [1080, 1920, 3]`
- `actual_hardware_decode_active = UNKNOWN_NOT_PROVEN` (by design — installed API does not directly expose actual HW decode vs configured HWAccel)
- `software_fallback_detected = UNKNOWN_NOT_PROVEN`; `software_fallback_reason = ""`

**Strict fallback control** (`allow_software_fallback=false`, cuda): `result = STRICT_PROBE_NO_FRAME`, `error_type = null`, no exception — **`INVALID_SUPPORTING_CONTROL_IMPLEMENTATION_DEFECT`**, NOT a runtime signal. The control's loop executes an outer `break` immediately after the inner `packet.decode()` loop, so it surrenders after the FIRST demuxed packet regardless of whether a frame was produced; for this H.264 stream the first packet yields no frame, hence `STRICT_PROBE_NO_FRAME`. It carries **no evidentiary weight** on actual HW decode activation or software fallback. It must be corrected (continue `demux` until the first decoded frame / EOF / exception) before it can be used in any future HWAccel evidence decision. The canonical production-path observations (which DO yield frames) are unaffected and remain valid.

**Raw-artifact known-limitation omission (`raw_artifact_known_limitation_omission`).** The committed raw artifact (`9b4cc54`, a provenance object that is intentionally NOT rewritten) reports `evidence_confidence = HIGH` and `limitations = []`. In the decision layer these must be qualified:
- raw `evidence_confidence = HIGH` refers ONLY to **canonical observation completeness** (two consistent production-path opens, `OBSERVATION_COMPLETE`) — it is NOT a confidence statement about actual HW decode activation;
- raw `limitations = []` omits that `actual_hardware_decode_active = UNKNOWN_NOT_PROVEN` and `software_fallback_detected = UNKNOWN_NOT_PROVEN` are by-design non-determinations, and that the strict fallback control result is an `INVALID_SUPPORTING_CONTROL_IMPLEMENTATION_DEFECT`, not a runtime signal.
- Confidence separation: **canonical observation completeness confidence = HIGH**; **actual hardware decode conclusion confidence = NOT_ESTABLISHED**.

**Decision (OUTCOME_D):** Canonical H.264 production-path observations succeed, but actual hardware decode state remains `UNKNOWN_NOT_PROVEN`. This determination rests solely on the production-observer design limitation (installed API does not expose actual HW decode vs configured HWAccel) — it is NOT inferred from decode speed and NOT inferred from the (invalid) strict control. The strict fallback control is invalid and provides no signal either way. `cuda` was requested and available (not OUTCOME_C). Therefore:
- **F-0098 = PARTIALLY_RESOLVED** — canonical evidence object now exists and is complete (observation completeness confidence HIGH); `codec_context_is_hwaccel=true` confirmed; activation question still UNKNOWN_NOT_PROVEN (conclusion confidence NOT_ESTABLISHED).
- **F-0100 = RESOLVED** — canonical clip located and copied local-only (gitignored `*.mp4`, not committed).
- **Step 18.4A = done** (canonical runtime observation collection complete, status `OBSERVATION_COMPLETE`).
- **selected_optimization = NONE**; **Step 18.4 = in_progress**; **Step 18.5 = planned / blocked**.

**MPEG-4 diagnostic probe** (at `benchmarks/detect/evidence/hwaccel-runtime-evidence/`) remains classified as `DIAGNOSTIC_NON_CANONICAL_FIXTURE_PROBE` — superseded by the canonical Hermes H.264 evidence; never constituted accepted Step 18.4A evidence.

---

## 13. F-0088 Status

**OPEN** — 28 slides detected, 6 PNG screenshots written. Pre-existing quality observation, unchanged by this decision.

---

## 14. Historical Context

- **F-0087:** Previous profile-based bottleneck from regressed benchmark. Not carried forward.
- **F-0088:** 28 slides / 6 PNGs — remains OPEN.
- **F-0096:** Previous rejected draft at incorrect HEAD. Historical.
- **F-0097:** RESOLVED — decoder/frame advancement pipeline wall-clock captured.
- **F-0098:** PARTIALLY_RESOLVED — canonical Hermes H.264 runtime evidence collected; `codec_context_is_hwaccel=true` confirmed; `actual_hardware_decode_active` remains UNKNOWN_NOT_PROVEN (conclusion confidence NOT_ESTABLISHED).
- **F-0100:** RESOLVED — canonical Hermes H.264 clip located and copied local-only (not committed).
- **Strict fallback control:** `INVALID_SUPPORTING_CONTROL_IMPLEMENTATION_DEFECT` (premature `break` after first packet); not a runtime gap and not a finding; must be fixed before the next HWAccel evidence decision.
- **PYAV_HWACCEL_CUDA:** REJECTED_SOURCE_MODEL_MISMATCH. Source already requests HWAccel (historical source state at rejection HEAD `acb424f`; current production uses `_create_hwaccel_with_evidence()`).
