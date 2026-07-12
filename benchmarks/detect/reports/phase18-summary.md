# Phase 18 — Detect Performance & Quality

## Status: In Progress (Steps 18.1–18.2 complete)

### Step 18.1 — PerformanceBaseline

**Module created:** `M-DETECT-METRICS` (`src/video2pptx/detection_metrics.py`)
- `DetectionRunMetrics` dataclass with typed timers/counters/gauges
- Canonical `{timers/ counters/ gauges/}` schema with `to_dict()`/`from_dict()` JSON round-trip
- `measure()` context manager for per-block timing; `collect()` for zero-cost enable/disable
- Per-frame timers: roi, extract_features, visual_distance, threshold, debounce
- Counters: frames_decoded, frames_sampled, features_full/quick, ndarray_conversions, screenshots_written
- Gauges: rgb_transfer_bytes, peak_ram_mb (psutil), peak_in_flight

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
- `test_output_signature_match`: SHA-256 signature of score timestamps, values, segment boundaries, and screenshot count matches approved reference (`c11f0288e...`)
- `test_screenshots_have_valid_pngs`: all screenshots are valid PNG files with non-zero size and correct header
- `test_log_markers_present`: asserts no `Pass 3/3` markers
- Full test suite: all detection/metrics tests pass

### Next Steps

| Step | Description | Status |
|------|-------------|--------|
| 18.3 | Short-video benchmark for quick iteration | Pending |
| 18.4 | Full Hermes re-benchmark | Pending |
| 18.5 | Additional optimizations (parallel features, lazy decode, etc.) | Planned |
