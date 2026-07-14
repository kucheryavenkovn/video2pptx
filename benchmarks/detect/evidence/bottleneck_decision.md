# Step 18.4 Bottleneck Decision — Corrected

## Status: BLOCKED_TARGET_OPTIMIZATION_NOT_DISCRIMINATED

**Selected bottleneck class:** DECODE_FRAME_PIPELINE
**Decision confidence:** HIGH
**Selected optimization:** NONE

**F-0097:** RESOLVED — decoder/frame advancement pipeline wall-clock captured.
**F-0098:** RESOLVED (activation-defect discrimination) — strict no-software-fallback CUDA control (Step 18.4B) decoded a canonical H.264 frame (`FIRST_FRAME_DECODED`); no activation/fallback defect proven; `PYAV_HARDWARE_DECODE_ACTIVATION_OR_FALLBACK_FIX` contradicted. Bounded: does NOT prove all production decode was hardware. No targeted optimization selected.
**F-0100:** RESOLVED — canonical Hermes H.264 clip located and copied local-only (not committed).
**Step 18.4A strict control (historical):** `INVALID_SUPPORTING_CONTROL_IMPLEMENTATION_DEFECT` (premature `break`) in raw `9b4cc` — carried no evidentiary weight; immutable provenance.
**Step 18.4B strict control (corrected):** `FIRST_FRAME_DECODED` (`allow_software_fallback=false`, packets_examined=3, frames_decoded=1, frames_converted=1, container_closed=true) — corrected control demuxes until first frame / EOF / exception; see §12B.

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
| **F-0098** | RESOLVED (activation-defect discrimination) — strict no-fallback CUDA control decoded a canonical frame (FIRST_FRAME_DECODED); no activation defect proven. |
| **F-0100** | RESOLVED — canonical clip located and copied local-only. |
| **Step 18.4A strict control** | INVALID_SUPPORTING_CONTROL_IMPLEMENTATION_DEFECT (historical, raw 9b4cc) — no evidentiary weight. |
| **Step 18.4B strict control** | FIRST_FRAME_DECODED (corrected, allow_software_fallback=false); OUTCOME_S1. |

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
- **Type:** Conditional optimization (would have required direct runtime proof of an activation defect).
- **Current evidence:** CONTRADICTED — Step 18.4B corrected strict no-software-fallback control (`HWAccel('cuda',0)`, `allow_software_fallback=false`) on the exact canonical Hermes H.264 clip produced `FIRST_FRAME_DECODED` (packets_examined=3, frames_decoded=1, frames_converted=1, container_closed=true; strict_control_evidence_commit `ef589a1`). The current environment decodes at least one canonical H.264 frame through a CUDA HWAccel configuration with software fallback explicitly disabled.
- **Verdict:** CONTRADICTED. No CUDA activation/fallback defect is proven — the strict no-fallback path already decodes the canonical stream — so there is nothing for this optimization to fix. Bounded: this does NOT prove all production decode was hardware, that the production fallback-enabled path never fell back, or any speedup.

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

**Status:** RESOLVED (activation-defect discrimination).

**Current resolution (Step 18.4B, 2026-07-14):** The corrected strict no-software-fallback control (`HWAccel('cuda',0)`, `allow_software_fallback=false`) decoded a canonical Hermes H.264 frame (`FIRST_FRAME_DECODED`; see §12B). No CUDA activation/fallback defect is proven, so `PYAV_HARDWARE_DECODE_ACTIVATION_OR_FALLBACK_FIX` is contradicted. Bounded: this does NOT prove all production decode was hardware, that the production fallback-enabled path never fell back, or any speedup. Production-path per-frame HW usage remains UNKNOWN_NOT_PROVEN by observer design (not needed to discriminate the optimization). `selected_optimization = NONE`; `Step 18.4 = in_progress`; `Step 18.5 = planned / blocked`.

> **Historical Step 18.4A intermediate state (before Step 18.4B).** The remainder of this section is preserved for traceability. It documents why F-0098 was `PARTIALLY_RESOLVED` after Step 18.4A and why the strict control then required correction — both of which Step 18.4B resolved. The statements below (including the previously-required strict-control correction and the Step 18.4A-time `F-0098 = PARTIALLY_RESOLVED` status) describe the Step 18.4A-time state, NOT the current state. Current state: F-0098 = RESOLVED (see §12B).

**Problem (historical):** Step 18.4 selected DECODE_FRAME_PIPELINE with HIGH confidence, but the proposed PYAV_HWACCEL_CUDA optimization was invalid because current source already requests HWAccel. Accepted benchmark evidence did not record actual HWAccel activation or software fallback state, so a targeted decoder optimization could not yet be selected safely.

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

**Step 18.4A canonical evidence run (2026-07-14) — historical intermediate state, outcome OUTCOME_D:**

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

**Strict fallback control (historical Step 18.4A result)** (`allow_software_fallback=false`, cuda): `result = STRICT_PROBE_NO_FRAME`, `error_type = null`, no exception — **`INVALID_SUPPORTING_CONTROL_IMPLEMENTATION_DEFECT`**, NOT a runtime signal. The control's loop executed an outer `break` immediately after the inner `packet.decode()` loop, so it surrendered after the FIRST demuxed packet regardless of whether a frame was produced; for this H.264 stream the first packet yields no frame, hence `STRICT_PROBE_NO_FRAME`. It carried **no evidentiary weight** on actual HW decode activation or software fallback. It had to be corrected (continue `demux` until the first decoded frame / EOF / exception) — this correction was performed in Step 18.4B (see §12B, `FIRST_FRAME_DECODED`). The canonical production-path observations (which DO yield frames) are unaffected and remain valid.

**Raw-artifact known-limitation omission (`raw_artifact_known_limitation_omission`).** The committed raw artifact (`9b4cc54`, a provenance object that is intentionally NOT rewritten) reports `evidence_confidence = HIGH` and `limitations = []`. In the decision layer these must be qualified:
- raw `evidence_confidence = HIGH` refers ONLY to **canonical observation completeness** (two consistent production-path opens, `OBSERVATION_COMPLETE`) — it is NOT a confidence statement about actual HW decode activation;
- raw `limitations = []` omits that `actual_hardware_decode_active = UNKNOWN_NOT_PROVEN` and `software_fallback_detected = UNKNOWN_NOT_PROVEN` are by-design non-determinations, and that the strict fallback control result is an `INVALID_SUPPORTING_CONTROL_IMPLEMENTATION_DEFECT`, not a runtime signal.
- Confidence separation: **canonical observation completeness confidence = HIGH**; **actual hardware decode conclusion confidence = NOT_ESTABLISHED**.

**Decision (historical Step 18.4A — OUTCOME_D):** Canonical H.264 production-path observations succeed, but actual hardware decode state remained `UNKNOWN_NOT_PROVEN`. This determination rested solely on the production-observer design limitation (installed API does not expose actual HW decode vs configured HWAccel) — it was NOT inferred from decode speed and NOT inferred from the (then-invalid) strict control. The strict fallback control was invalid and provided no signal either way. `cuda` was requested and available (not OUTCOME_C). At Step 18.4A this yielded:
- **F-0098 = PARTIALLY_RESOLVED at Step 18.4A** (now RESOLVED at Step 18.4B — see §12B) — canonical evidence object existed and was complete (observation completeness confidence HIGH); `codec_context_is_hwaccel=true` confirmed; activation question still UNKNOWN_NOT_PROVEN (conclusion confidence NOT_ESTABLISHED).
- **F-0100 = RESOLVED** — canonical clip located and copied local-only (gitignored `*.mp4`, not committed).
- **Step 18.4A = done** (canonical runtime observation collection complete, status `OBSERVATION_COMPLETE`).
- **selected_optimization = NONE**; **Step 18.4 = in_progress**; **Step 18.5 = planned / blocked**.

**MPEG-4 diagnostic probe** (at `benchmarks/detect/evidence/hwaccel-runtime-evidence/`) remains classified as `DIAGNOSTIC_NON_CANONICAL_FIXTURE_PROBE` — superseded by the canonical Hermes H.264 evidence; never constituted accepted Step 18.4A evidence.

---

## 12B. Step 18.4B — Corrected Strict No-Software-Fallback Control (OUTCOME_S1)

Step 18.4A's strict control was an `INVALID_SUPPORTING_CONTROL_IMPLEMENTATION_DEFECT` (premature outer `break` after the first demux packet). Step 18.4B corrected it and re-ran **only** the corrected control on the exact canonical Hermes H.264 clip (production observations were NOT rerun; raw `9b4cc` is immutable).

- **Corrected loop behavior:** demux/decode until ONE deterministic terminal state — `FIRST_FRAME_DECODED` / `EOF_NO_FRAME` / `PACKET_LIMIT_REACHED_NO_FRAME` / `SETUP_EXCEPTION` / `CONTAINER_OPEN_EXCEPTION` / `DECODE_EXCEPTION` / `FRAME_CONVERSION_EXCEPTION`. It does NOT stop merely because one packet yielded zero frames; container is explicitly closed in a `finally` block.
- **Result:** `FIRST_FRAME_DECODED` (stage `first_frame_decoded`).
  - `requested_hw_device = cuda`; `allow_software_fallback = false`
  - `packets_examined = 3`; `packets_with_decoded_frames = 1`; `frames_decoded = 1`; `frames_converted = 1`
  - `first_frame_timestamp = 0.033`; `first_frame_shape = [1080, 1920, 3]`; `codec_name = h264`
  - `container_opened = true`; `container_closed = true`; no error
- **Evidence dir:** `benchmarks/detect/evidence/hwaccel-strict-control-hermes-h264-20260714/`
- **Commits:** strict-control code `04c0dc1f` (tree `b93329dd`); raw strict evidence `ef589a1`; accepted master base `547dc06e`; canonical runtime evidence `9b4cc` (unchanged).
- **Bounded fact (directly proven):** the current environment supports decoding at least one canonical H.264 frame through a CUDA HWAccel configuration with software fallback explicitly disabled.
- **NOT proven:** that all production benchmark frames used hardware decode; that the production fallback-enabled path never used software fallback; any decode throughput improvement / speedup.
- **Confidence:** `strict_control_execution_completeness_confidence = HIGH`; `strict_control_runtime_interpretation_confidence = HIGH`.
- **Decision (OUTCOME_S1):** no CUDA activation/fallback defect is proven → `PYAV_HARDWARE_DECODE_ACTIVATION_OR_FALLBACK_FIX` is CONTRADICTED. `F-0098 = RESOLVED` (activation-defect discrimination). `selected_optimization = NONE`; `Step 18.4 = in_progress`; `Step 18.4B = done`; `Step 18.5 = planned / blocked`. No new finding (the corrected control succeeded; no new gap).

---

## 13. F-0088 Status

**OPEN** — 28 slides detected, 6 PNG screenshots written. Pre-existing quality observation, unchanged by this decision.

---

## 14. Historical Context

- **F-0087:** Previous profile-based bottleneck from regressed benchmark. Not carried forward.
- **F-0088:** 28 slides / 6 PNGs — remains OPEN.
- **F-0096:** Previous rejected draft at incorrect HEAD. Historical.
- **F-0097:** RESOLVED — decoder/frame advancement pipeline wall-clock captured.
- **F-0098:** RESOLVED (activation-defect discrimination) — Step 18.4B corrected strict control decoded a canonical H.264 frame (FIRST_FRAME_DECODED); no CUDA activation/fallback defect proven; PYAV_HARDWARE_DECODE_ACTIVATION_OR_FALLBACK_FIX contradicted. Production-path actual_hardware_decode_active remains UNKNOWN_NOT_PROVEN by observer design (not needed to discriminate the optimization).
- **F-0100:** RESOLVED — canonical Hermes H.264 clip located and copied local-only (not committed).
- **Step 18.4A strict control:** `INVALID_SUPPORTING_CONTROL_IMPLEMENTATION_DEFECT` (historical, raw 9b4cc) — no evidentiary weight; immutable provenance.
- **Step 18.4B strict control:** corrected; `FIRST_FRAME_DECODED`; demuxes until first frame / EOF / exception; explicit container close.
- **PYAV_HWACCEL_CUDA:** REJECTED_SOURCE_MODEL_MISMATCH. Source already requests HWAccel (historical source state at rejection HEAD `acb424f`; current production uses `_create_hwaccel_with_evidence()`).
- **PYAV_HARDWARE_DECODE_ACTIVATION_OR_FALLBACK_FIX:** CONTRADICTED_BY_STRICT_NO_FALLBACK_CONTROL (Step 18.4B FIRST_FRAME_DECODED).

---

## 15. Step 18.4C — Target Optimization Discrimination Correction (2026-07-14)

**Status:** in_progress.
**Corrected evidence:** not yet executed.
**Selected optimization:** NONE.
**Step 18.4:** in_progress.
**Step 18.5:** planned / blocked; implementation not started.
**F-0102:** `REJECTED_STEP_18_4C_DRAFT_FINDING`; not current.

The package in `benchmarks/detect/evidence/target-optimization-discrimination-20260714-13e6fff/`
(evidence commit `b869464a6e84b2deba83a3df5e7c37ffe65ccde8`, decision commit
`4b6eba59467110642e0959407d7bec9ff59ac7d8`) is
`REJECTED_FOR_STEP_18_4C_ACCEPTANCE`.

Primary reason: `C3_CODE_ARTIFACT_PROVENANCE_CONTRADICTION`.

Additional reasons: `UNSUPPORTED_C1_CAUSAL_ATTRIBUTION` and
`C2_UPPER_BOUND_MISLABELED_AS_REQUIRED_MINIMUM`.

The exact tested C1 prototype's 0/84 result remains historical, with root cause
`UNKNOWN_NOT_ISOLATED`. The C2 value 7,471,180,800 bytes remains
`retain_all_upper_bound_bytes`, not a proven minimum. C3
`NO_EVIDENCE_SUPPORTED_CONFIGURATION_VARIANT` and Outcome T3 are not accepted.

No terminal corrected decision exists until clean committed diagnostic code emits the new r2
child artifacts and a child-consistent aggregate.
