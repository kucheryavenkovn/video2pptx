# Step 18.4 Bottleneck Decision — F-0097 Instrumented Evidence

## Status: DECISION_MADE

**Selected bottleneck class:** DECODE_FRAME_PIPELINE
**Decision confidence:** HIGH
**Selected optimization:** PYAV_HWACCEL_CUDA

---

## 1. Evidence Source

- **Benchmark sequence:** `hermes-600s-f0097-instrumented-20260713-acb424f`
- **Evidence identities:**
  - `benchmark_code_head` = `acb424f904bc4b3459f6ad2ceb9f8c701cedb69b`
  - `benchmark_code_tree` = `6a7a596b802fa77465288136d4ea309a50557f2a`
  - `evidence_builder_head` = `acb424f904bc4b3459f6ad2ceb9f8c701cedb69b`
  - `recovered_master_base` = `836a456eee0312646747d755dfe838052eaa6752`
- **Median run:** run-01 — 272.5658s
- **Mean:** 277.2175s
- **Std dev:** 32.5005s
- **All provenance SHAs are exact 40-character lowercase identities.**

---

## 2. Wall-Clock Stage Accounting (median run-01)

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

**F-0097 impact:** Residual dropped from 87.39s (33.0%) to 0.53s (0.19%). All decode work is now captured by non-overlapping wall-clock timers.

---

## 3. Pipeline Execution Model: SYNCHRONOUS

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

## 4. Directional Stability

| Run | pass1_decode_advance | pass2_decode_advance | Decode Pipeline Total | extract_features | Gap |
|-----|---------------------|---------------------|---------------------|-----------------|-----|
| run-01 | 96.36s (35.35%) | 76.09s (27.92%) | **172.46s (63.27%)** | 92.62s (33.98%) | **79.84s (29.29%)** |
| run-02 | 114.76s (36.81%) | 52.90s (16.97%) | **167.65s (53.77%)** | 136.39s (43.75%) | **31.26s (10.03%)** |
| run-03 | 97.14s (39.28%) | 53.78s (21.75%) | **150.91s (61.03%)** | 88.43s (35.76%) | **62.49s (25.27%)** |

**Stability:** Decode pipeline total exceeds extract_features in ALL runs. Gap is directionally stable (31.26s–79.84s). The ordering (decode > extract) holds consistently despite ~12% run-to-run variance.

---

## 5. cProfile Supporting Evidence (carried forward from previous cycle)

| Function | Cumulative (s) | Self (s) | Calls |
|----------|-------|----------|-------|
| pyav_iter_frames | 135.128 | 10.469 | 2404 |
| Packet.decode | 114.854 | 114.854 | 72004 |
| extract_features | 92.712 | 0.039 | 1285 |

**Source:** `benchmarks/detect/runs/hermes-600s-recovered-r2-20260713-465d89e/profile/profile.txt`
**Provenance:** benchmark_code_head = `465d89e243651e56a23e8c141632335bdd3a3303`, evidence_builder_head = `3e3007cd9cb7f9e931acf8ccca1d8baa52fc5156`, recovered_master_base = `713ea07827f3efc9abec1b8db50768fe8ef9bad0`. **This is carried-forward supporting evidence, not the primary decision basis.** The new non-overlapping wall-clock timers are the primary evidence.

---

## 6. Counter-Invariants (median run-01)

| Counter | Value |
|---------|-------|
| frames_decoded | 72002 |
| frames_sampled (per pass) | 1201 |
| features_full | 1201 |
| pass2_frames_sampled | 1201 |
| ndarray_conversions | 2402 (1201 Pass 1 + 1201 Pass 2) |
| representative_frames | 84 |
| screenshots_written | 6 |
| slides_detected | 28 |
| Canonical signature | `8cc06c6accb055fb6fed461f2f4a96f0b288ef864b9423000b6f59d9ab56bc85` |

---

## 7. Candidate Evaluation

### FEATURE_EXTRACTION_CPU
- **Wall-clock:** 92.62s (33.98%) — second-largest measured timer.
- **Evidence:** Well-characterized with known sub-components (histogram ~49s, gray ~34s, phash+dhash ~7s).
- **Counter:** Total decode pipeline (172.46s, 63.27%) exceeds extract_features by 79.84s (29.29%). Gap is directionally stable.
- **Ruling:** NOT primary. Safely discriminated by the direct decode timers.

### DECODE_FRAME_PIPELINE
- **Wall-clock:** 172.46s (63.27%) — pass1 (35.35%) + pass2 (27.92%) decode advancement.
- **Evidence:** Directly measured by new non-overlapping timers. Residual near zero (0.19%) confirms full capture.
- **Profile:** Packet.decode 114.85s self — largest single function.
- **Ruling: PRIMARY.** Dominant bottleneck. Decode runs identical code in both passes; optimizing it reduces both.

### PASS2_COLLECTION
- **Wall-clock:** 0.04s (0.02%) — independently measured by pass2_match_and_collect.
- **Ruling:** NOT primary. Negligible.

### THRESHOLD_OR_DECISION_LOGIC
- **Wall-clock:** Combined <0.42s (<0.16%).
- **Ruling:** NOT primary. Negligible.

### MIXED_OR_UNRESOLVED
- **Wall-clock:** Residual 0.53s (0.19%) — down from 87.39s (33.0%).
- **Ruling:** NOT primary. F-0097 resolved; specific discrimination now succeeds.

---

## 8. Decision

| Field | Value |
|-------|-------|
| **Status** | `DECISION_MADE` |
| **Selected bottleneck class** | `DECODE_FRAME_PIPELINE` |
| **Decision confidence** | HIGH |
| **Selected optimization** | `PYAV_HWACCEL_CUDA` |
| **Step 18.5 hypothesis** | Add `hwaccel=cuda` to PyAV `av.open()` options to offload H.264 Packet.decode from CPU to GPU (RTX 4090). See `step18_5_hypothesis` in bottleneck_decision.json for full details. |
| **Evidence gap** | RESOLVED — F-0097 closed by pass1_decode_or_frame_advance, pass2_decode_or_frame_advance, pass2_match_and_collect timers. |

---

## 9. Selected Optimization: PYAV_HWACCEL_CUDA

**Target:** DECODE_FRAME_PIPELINE

**Code boundaries:** `src/video2pptx/backends/pyav_backend.py` — `pyav_iter_frames()` generator, specifically the `av.open(video_path, ...)` options dict and the `for packet in container.demux(): packet.decode()` loop.

**Mechanistic hypothesis:** PyAV defaults to FFmpeg software H.264 decoder (h264). By passing `hwaccel=cuda` to `av.open()`, FFmpeg uses the NVIDIA CUVID/CUDA decoder (h264_cuvid). This offloads the dominant CPU decode cost to the GPU. The `to_ndarray(format='rgb')` call still copies frame data from GPU to CPU.

**Expected affected timers:** `pass1_decode_or_frame_advance`, `pass2_decode_or_frame_advance`

**Expected unaffected timers:** `extract_features`, `roi`, `visual_distance`, `threshold`, `debounce`, `pass2_match_and_collect`, `pass2_dedupe`, `pass2_screenshots`

**Performance gate (Step 18.6):** `pass1_decode_or_frame_advance` + `pass2_decode_or_frame_advance` total must decrease by **at least 40%** (from ~172.46s to <103.47s).

**Quality gate (Step 18.6):** All output invariants must pass exactly: canonical signature `8cc06c6accb055fb6fed461f2f4a96f0b288ef864b9423000b6f59d9ab56bc85`, 28 slides, 1200 scores, 6 PNGs.

---

## 10. Step 18.6 Acceptance Gates

| Gate | Requirement |
|------|-------------|
| Canonical signature | `8cc06c6accb055fb6fed461f2f4a96f0b288ef864b9423000b6f59d9ab56bc85` |
| Slides count | 28 |
| Score count | 1200 |
| Screenshots written | 6 |
| Actual PNG count | 6 |
| sample_fps | 2.0 |
| Two-pass semantics | Preserved |
| Cancellation | Preserved |
| Progress | Preserved |
| GUI/MCP/CLI public semantics | Preserved |
| Decode pipeline performance | pass1 + pass2 decode advancement must decrease by >= 40% |
| Profile carry-forward | No new cProfile required; non-overlapping wall-clock timers are primary evidence |

---

## 11. F-0097 Status

**RESOLVED**

F-0097 documented the evidence gap where decode work was hidden in the unattributed residual (87.39s, 33.0%). Three new InstrumentedIterator-based wall-clock timers were added:

- `pass1_decode_or_frame_advance` — measures Pass 1 generator advancement (demux + Packet.decode + to_ndarray)
- `pass2_decode_or_frame_advance` — measures Pass 2 generator advancement
- `pass2_match_and_collect` — measures Pass 2 loop body (non-decode collection overhead)

All three timers use `time.perf_counter()` before/after `self._it.__next__()`, including StopIteration exhaustion and exception paths. Counters increment only after successful yields.

**Result:** Residual reduced from 87.39s (33.0%) to 0.53s (0.19%). F-0097 is RESOLVED with definitive evidence that DECODE_FRAME_PIPELINE is the primary bottleneck.

---

## 12. F-0088 Status

**OPEN** — 28 slides detected, 6 PNG screenshots written. Pre-existing quality observation, unchanged by this decision.

---

## 13. Historical Context

- **F-0087:** Previous profile-based bottleneck from regressed benchmark. Not carried forward.
- **F-0088:** 28 slides / 6 PNGs — remains OPEN.
- **F-0096:** Previous rejected draft at incorrect HEAD. Historical.
- **F-0097:** RESOLVED — decode work now directly measured by non-overlapping wall-clock timers.
- **Previous draft (`27a28bf`):** Contained incorrect values (pass2_collect 10.9s, visual_distance ~12.4s, async pipeline claim). Replaced by corrected evidence in this decision.
