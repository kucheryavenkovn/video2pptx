# Phase 18 — Detect Performance & Quality

## Status: In Progress (Steps 18.1–18.4 complete)

### Step 18.1 — PerformanceBaseline

**Module created:** `M-DETECT-METRICS` (`src/video2pptx/detection_metrics.py`)
- `DetectionRunMetrics` dataclass with typed timers/counters/gauges
- Canonical `{timers/ counters/ gauges/}` schema with `to_dict()`/`from_dict()` JSON round-trip
- `measure()` context manager for per-block timing; `collect()` for zero-cost enable/disable
- Per-frame timers: roi, extract_features, visual_distance, threshold, debounce
- Counters: frames_decoded, frames_sampled (Pass 1 only), pass2_frames_sampled (Pass 2 yields),
  features_full/quick, ndarray_conversions, screenshots_written, representative_frames,
  representative_frame_bytes
- Gauges: rgb_transfer_bytes, rss_before_mb, rss_peak_mb, rss_after_mb, peak_in_flight

**Instrumentation added to:**
- `slide_detector.py` — per-frame `measure("roi")`, `measure("extract_features")`, `measure("visual_distance")`, `measure("threshold")`, `measure("debounce")`
- `detect_slides.py` — `measure("total")`, `measure("pass2_collect")`, `measure("pass2_dedupe")`, `measure("pass2_screenshots")`, counters for `slides_detected`, `screenshots_written`, `representative_frames`, `frames_sampled` via `InstrumentedIterator`
- `pyav_backend.py` — `counter_frames_decoded` per `packet.decode()`, `counter_ndarray_conversions` per `to_ndarray()`, `gauge_rgb_transfer_bytes` = `img.nbytes`
- `opencv_backend.py` — same counters for `cap.read()` and `cv2.cvtColor()` path

**Benchmark tool:** `tools/benchmark_detect.py`
- Canonical route via `DetectionService` (delegates to `run_detect_slides`)
- Artifacts: `metrics.json`, `environment.json`, `effective_config.json`, `output_signature.json`, `comparison.json`, optional `profile.pstats`
- Metrics collector is re-entrant: benchmark's `collect()` and inner `_collect_metrics()` share the same collector

**Benchmark contract tests passed:**
- `test_metrics_collected_on_tiny_video`: all timers > 0, counters > 0, RGB bytes > 0, screenshots on disk match counter
- `test_metrics_json_serializable`: to_dict() → json → load → values preserved

**Hermes baseline result: TIMEOUT (partial)**

Target video: `05_4. Hermes.mp4` (3655s, 60fps, H.264, 1920x1080, sample_fps=2)
- Killed after 30 min during Pass 3 (screenshot saving)
- 414 deduplicated segments were reported before timeout
- Partial screenshots saved (13 of 414)
- Full metrics lost due to process kill (killed before `collect()` exit)
- Architectural finding: **The redundant third full sequential decode is a confirmed architectural cost and a strong optimization target.**

### Step 18.2 — TwoPassDetection (completed)

**Change:** Collapse Pass 3 (save screenshots) into Pass 2 (dedup frame grab).

Before: `decoder.iter_frames()` called 3 times (detect → dedup → screenshots)
After:  `decoder.iter_frames()` called 2 times (detect → dedup+screenshots)

**Code changes:**
- `src/video2pptx/detect_slides.py`: Unified `DEDUPE_AND_SAVE_SCREENSHOTS` block — one video decode pass collects `rep_frames`. `saved_frames` dict removed (only `rep_frames` used). Dedup runs in memory, then screenshots are written from `rep_frames` dict.
- Log markers: `Pass 1/3` → `Pass 1/2`, `Pass 2/3` → `Pass 2/2`, `Pass 3/3` removed
- `src/video2pptx/slide_detector.py`: Progress callback label updated
- Contract updated: SIDE_EFFECTS now says "iterates video 2 times"

**Verification:**
- `test_iter_frames_called_exactly_twice`: monkeypatched `VideoDecoder.iter_frames` verifies exactly 2 calls (dedup enabled)
- `test_iter_frames_called_twice_dedupe_disabled`: exactly 2 calls even without dedup
- `test_two_pass_matches_pre_twopass`: parity test against reference artifact `benchmarks/detect/reference/pre-twopass-3472e62.json`. Reference source commit `3472e62b19fa4fea59bde1fa52b45cd2ff4939d0`. Coverage: score_timestamps parity within abs tolerance 1e-4, score_values parity within abs tolerance 1e-4, segment index exact, segment start/end within abs tolerance 1e-4, representative_timestamp within abs tolerance 1e-4, segment image paths exact, screenshot count exact, screenshot relative paths exact, per-screenshot SHA-256 exact, decoder.iter_frames exactly 2 calls, no Pass 3/3 markers.
- `test_screenshots_have_valid_pngs`: all screenshots are valid PNG files with non-zero size and correct header
- `test_log_markers_present`: asserts no `Pass 3/3` markers
- Full test suite: all detection/metrics tests pass

### Step 18.3 — ShortVideoBenchmark (completed)

Fixed interval: first 600 seconds of the same local Hermes source, stream-copied without re-encoding.
The clip is H.264 1920x1080 at 60 fps, actual duration 600.016667 seconds, SHA-256
`dd9da3442e91ab7f17f0405198aa8e39d1538d74518b6b9a3b1e61ac2fc0f5a4`.

Canonical active config loaded through `FileProjectRepository`: sample_fps 2.0, backend auto
(resolved to PyAV), ROI auto, no ignored ROIs, threshold auto, min slide 2.0 seconds,
min stable 2.0 seconds, dedupe enabled, full mode.

One warm-up and three recorded DetectionService runs completed. Recorded detect elapsed:
242.126841, 245.960049, and 247.533700 seconds; median 245.960049 seconds. All canonical
output signatures equal `8cc06c6accb055fb6fed461f2f4a96f0b288ef864b9423000b6f59d9ab56bc85`.

### Step 18.4 — BottleneckDecision (completed)

Decision: **DECODE_PROFILE**. Median measured feature extraction is 88.616671 seconds
(36.029% of median detect elapsed), Pass 2 collect is 53.669377 seconds (21.820%), and
the derived unattributed residual is 96.728170 seconds (39.327%). The separate profile
shows 128.832 seconds cumulative in packet decode and 10.218 seconds in `to_ndarray`.
Threshold is only 0.127240 seconds (0.052%). Recommended next branch:
`perf/phase18-decode-profile`. No optimization was implemented in Step 18.3.

Immutable evidence: `benchmarks/detect/runs/hermes-600s-20260713-8623cd2/`.

### Next Steps

| Step | Description | Status |
|------|-------------|--------|
| 18.3 | Fixed short-video benchmark | Done |
| 18.4 | Evidence-driven bottleneck decision | Done: DECODE_PROFILE |
| 18.5 | Targeted optimization selected by evidence | Planned |
| 18.6 | Short-video re-benchmark | Planned |
| 18.7 | Full Hermes re-benchmark | Planned |
| 18.8 | Quality acceptance | Planned |
