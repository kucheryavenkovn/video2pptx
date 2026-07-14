# Step 18.4 Bottleneck Decision — Corrected

## Status: BLOCKED_TARGET_OPTIMIZATION_NOT_DISCRIMINATED

**Selected bottleneck class:** DECODE_FRAME_PIPELINE
**Decision confidence:** HIGH
**Selected optimization:** NONE

**F-0097:** RESOLVED — decoder/frame advancement pipeline wall-clock captured.
**F-0098:** OPEN — HWAccel runtime activation evidence gap; no targeted optimization selected.

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
| **F-0098** | OPEN — HWAccel runtime activation evidence gap. |

---

## 8. Rejected Optimization: PYAV_HWACCEL_CUDA

**Status:** REJECTED_SOURCE_MODEL_MISMATCH

**Hypothesis (rejected):** Add `hwaccel=cuda` to PyAV `av.open()` to offload H.264 Packet.decode from CPU to GPU.

**Why rejected:** Source audit at candidate HEAD proves the existing `pyav_iter_frames` already:
1. Prefers `"cuda"` first in `_HW_PREFERRED` (`pyav_backend.py:28`)
2. Calls `_pick_hw_device()` which selects the best available HW device
3. Calls `_create_hwaccel(hw_device)` to create a `HWAccel` object
4. Passes `hwaccel=hwaccel` to `av.open(str(video_path), hwaccel=hwaccel)` (`pyav_backend.py:123`)

The hypothesized intervention already exists in source. No committed benchmark evidence proves whether hardware decode was actually active at runtime (see F-0098).

**False source assumptions:**
- "PyAV defaults to software H.264 decoder" — contradicted by `_HW_PREFERRED = ["cuda", ...]`
- "Step 18.5 needs to add hwaccel=cuda to av.open()" — already present
- "Existing benchmark decode is definitely software-only" — no runtime evidence supports this

**Historical context:** This hypothesis was the initial Step 18.4 decision before source audit. It is preserved in git history for traceability.

---

## 9. Optimization Candidate Evaluation

### HWACCEL_RUNTIME_OBSERVABILITY_AND_FALLBACK
- **Type:** Evidence/observability, not optimization.
- **Current behavior:** HWAccel is requested via `_pick_hw_device() → _create_hwaccel() → av.open(hwaccel=...)`. No runtime telemetry records whether HWAccel was created or active.
- **Verdict:** Cannot be the sole optimization for Step 18.5.

### PYAV_HARDWARE_DECODE_ACTIVATION_OR_FALLBACK_FIX
- **Type:** Conditional optimization (requires prior runtime evidence).
- **Current evidence:** NONE — no committed benchmark evidence proves hardware decode was inactive.
- **Verdict:** Not viable without F-0098 evidence first.

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

## 12. F-0098 — New Evidence Gap

**Status:** OPEN

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

**Step 18.4A correction state (2026-07-13):**

Evidence mechanism **implemented and corrected**:
- Private observer with corrected schema: `codec_context_is_hwaccel` separated from `actual_hardware_decode_active`
- Creation-error capture via `_create_hwaccel_with_evidence()`
- Explicit `gen.close()` in probe
- Provenance-validated probe tool (`--accepted-base`, `--canonical-mode`)
- Deterministic hardware identity (no Python object repr)
- 17/17 evidence tests pass

**Blocked:** exact canonical Hermes H.264 clip (`examples/hermes-0000-1000.mp4`, SHA256 `dd9da344...`) not available on this workstation.

**F-0098 remains OPEN.** The evidence mechanism is ready but cannot be exercised on the canonical H.264 clip without the file. See F-0100.

**MPEG-4 diagnostic probe** (at `benchmarks/detect/evidence/hwaccel-runtime-evidence/`) classified as `DIAGNOSTIC_NON_CANONICAL_FIXTURE_PROBE` — does not constitute accepted Step 18.4A evidence.

---

## 13. F-0088 Status

**OPEN** — 28 slides detected, 6 PNG screenshots written. Pre-existing quality observation, unchanged by this decision.

---

## 14. Historical Context

- **F-0087:** Previous profile-based bottleneck from regressed benchmark. Not carried forward.
- **F-0088:** 28 slides / 6 PNGs — remains OPEN.
- **F-0096:** Previous rejected draft at incorrect HEAD. Historical.
- **F-0097:** RESOLVED — decoder/frame advancement pipeline wall-clock captured.
- **F-0098:** OPEN — HWAccel runtime activation evidence gap.
- **PYAV_HWACCEL_CUDA:** REJECTED_SOURCE_MODEL_MISMATCH. Source already requests HWAccel.
