# Phase 18 — Detect Performance & Quality

## Status: In Progress (Steps 18.1–18.2 done)

### Step 18.1 — PerformanceBaseline

**Module created:** `M-DETECT-METRICS` (`src/video2pptx/detection_metrics.py`)
- `DetectionRunMetrics` dataclass with typed timers/counters/gauges
- `measure()` context manager for sub-second instrumentation
- `collect()` for zero-cost enabled/disabled semantics
- `to_dict()`/`from_dict()` JSON round-trip

**Instrumentation added to:**
- `slide_detector.py` — Pass 1 sub-stage timers (feature extraction, PHash, FrameDiff)
- `detect_slides.py` — Pass-level timers (total, pass1, pass2)
- `pyav_backend.py` — decoded frame counter, ndarray conversion counter, RGB transfer bytes gauge

**Benchmark tool:** `tools/benchmark_detect.py`
- Canonical route via `DetectionService` (not raw `run_detect_slides`)
- Artifacts: `metrics.json`, `environment.json`, `effective_config.json`, `output_signature.json`, `comparison.json`, optional `profile.pstats`
- Environment capture: Git SHA, Python/OS/CPU/RAM, OpenCV/PyAV/Qt versions

**Hermes baseline result: TIMEOUT (partial)**

Target video: `05_4. Hermes.mp4` (3655s, 60fps, H.264, 1920x1080, sample_fps=2)
- Killed after 30 min during Pass 3 (screenshot saving)
- 414 segments detected correctly (confirmed from stdout)
- Partial screenshots saved (13 of 414)
- Full metrics lost due to process kill
- Finding: **3-pass structure is the primary bottleneck** — each pass requires full sequential video decode

### Step 18.2 — TwoPassDetection (completed)

**Change:** Collapse Pass 3 (save screenshots) into Pass 2 (dedup frame grab).

Before: `decoder.iter_frames()` called 3 times (detect → dedup → screenshots)
After:  `decoder.iter_frames()` called 2 times (detect → dedup+screenshots)

**Code changes:**
- `src/video2pptx/detect_slides.py`: Unified `DEDUPE_AND_SAVE_SCREENSHOTS` block — one video decode pass collects `rep_frames` (for dedup comparison) and `saved_frames` (for screenshot write). Dedup runs in memory, then screenshots written from `saved_frames` dict.
- Log markers: `Pass 1/3` → `Pass 1/2`, `Pass 2/3` → `Pass 2/2`, `Pass 3/3` removed
- `src/video2pptx/slide_detector.py`: Progress callback label updated
- Contract updated: SIDE_EFFECTS now says "iterates video 2 times"

**Verification:**
- `test_detect_slides.py`: 6/6 pass (including new `test_log_markers_dedupe_enabled` which asserts no `Pass 3/3`)
- Full test suite: 985 passed, 8 pre-existing e2e errors (MCP port not running)
- Confirmed: zero `Pass */3` references remain in source

### Next Steps

| Step | Description | Status |
|------|-------------|--------|
| 18.3 | Short-video benchmark for quick iteration | Pending |
| 18.4 | Full Hermes re-benchmark | Pending |
| 18.5 | Additional optimizations (parallel features, lazy decode, etc.) | Planned |
