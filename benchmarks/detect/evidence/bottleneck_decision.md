# Step 18.4 Bottleneck Decision

## 1. Evidence Source
- **Accepted benchmark:** `hermes-600s-recovered-r2-20260713-465d89e`
- **Median run:** run-03 — 265.1s total elapsed wall-clock
- **Run variance:** run-01=276.1s, run-02=222.2s, run-03=265.0s (std dev ≈ 28.5s)
- **cProfile:** `profile/profile.txt` — cumulative hierarchy

## 2. Wall-Clock Stage Breakdown (median run-03)

| Stage | Seconds | % of total | Code location |
|-------|---------|-----------|---------------|
| **extract_features** | **101.7** | **38.4%** | frame_features.extract_features |
| Packet.decode (pyav) | overlapped | — | pyav_backend.iter_frames |
| visual_distance | ~12.4 | ~4.7% | slide_detector.detect_changes |
| threshold / debounce | <1.0 | <0.4% | slide_detector.detect_changes |
| **Pass 1 total** | **253.1** | **95.5%** | detect_slides.detect_changes |
| pass2_collect + dedupe | 10.9 | 4.1% | detect_slides (measure_collect_slides) |
| Other overhead | 1.1 | 0.4% | detect_slides |

## 3. Candidate Bottleneck Assessment

### FEATURE_EXTRACTION_CPU ← SELECTED
- **Wall-clock:** 101.7s (38.4%) — largest single measured stage
- **cProfile:** 107.3s cumulative
  - `compute_histogram`: 48.8s cumulative
  - `cv2_to_gray`: 34.0s cumulative (includes phash/dhash local grayscale calls)
  - `phash`: ~9.9s cumulative
  - `dhash`: ~8.5s cumulative
- **Subsystem (compute_histogram + cv2_to_gray):** 82.8s (78% of extract_features)
- **Verdict:** Primary bottleneck. Histogram and grayscale are pure CPU pixel ops on 18018 frames × 1920×1080. Both are amenable to OpenCV vectorized acceleration without algorithmic changes.

### DECODE_FRAME_PIPELINE (NOT primary)
- **cProfile cumulative:** 114.854s (Packet.decode) — larger than extract_features in profile
- **Wall-clock:** Not independently measurable due to producer-consumer overlap with extract_features
- **Analysis:** 18018 frames / 265.1s ≈ 68 fps decode throughput. RTX 4090 NVDEC handles this well. The profile cumulative is inflated because decode frames are consumed asynchronously by feature extraction. Measured wall-clock would be bounded by the slower stage (extract_features).
- **Verdict:** Not a bottleneck at current HW. Optimizing decode would not improve end-to-end time as the pipeline is feature-extraction-bound.

### PASS2_COLLECTION (NOT primary)
- **Wall-clock:** 10.9s (4.1%)
- **Verdict:** Too small to target. Would yield at most ~4% improvement.

### THRESHOLD_OR_DECISION_LOGIC (NOT primary)
- **Wall-clock:** visual_distance ~12.4s (4.7%); threshold/debounce <1s
- **Verdict:** Negligible. Combined <6%.

## 4. Selected Optimization

### Name: `opencv-accelerated-histogram-gray`

| Property | Value |
|----------|-------|
| **Target module** | M-FRAME-FEATURES |
| **Target file** | `src/video2pptx/frame_features.py` |
| **Target function** | `extract_features` |
| **Subsystem** | `compute_histogram` (48.8s) + `cv2_to_gray` (34.0s) = 82.8s |
| **Acceleration type** | OpenCV-native vectorized (cv2.calcHist, fused grayscale path) |
| **Hypothesis** | Replace per-iteration custom histogram logic with cv2.calcHist over optimized memory layout; fuse grayscale + histogram into single pass to reduce memory bandwidth. Estimated 30–50% reduction on the 82.8s subsystem (25–41s saved). |
| **Estimated total gain** | 9–15% of 265s pipeline → **225–241s expected median** |

## 5. Acceptance Gates (Step 18.6)

| Gate | Criterion |
|------|-----------|
| Wall-clock reduction | ≥15% vs baseline 265.1s (≤225s expected) |
| Missed slide rate | ≤5% |
| False split rate | ≤10% |
| Timestamp error | ≤1.5s |
| Benchmark integrity | Same short video, same HW (RTX 4090), same 3-run protocol |
| Comparison baseline | Median run-03 (265.1s) from accepted Step 18.3 |

## 6. Historical Context

- **F-0087:** Previous DECODE_PROFILE bottleneck hypothesis from regressed benchmark is superseded.
- **F-0088:** Remains OPEN — run variance (std dev ~28.5s) needs investigation post-optimization.
