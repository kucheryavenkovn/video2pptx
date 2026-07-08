# Findings (F-NNNN)

Журнал проблем, несовместимостей и неочевидных фактов об окружении.
Формат: одна находка = один блок `### F-NNNN`.

---

<!-- Записи добавляются агентом по мере обнаружения -->

### F-0001 — `parse_roi` crashes on invalid string format
- Date: 2026-07-08
- Area: detection
- Finding: `parse_roi("not-a-roi")` raises `ValueError` from `int()` conversion before the `len(parts) == 4` check, because `re.split` on "not-a-roi" produces `["not-a-roi"]` which fails `int("not-a-roi")`.
- Symptom/Reproduction: test_roi.py::TestParseRoi::test_invalid_format_falls_back
- Impact: ROI parsing crashes instead of falling back to full frame
- Resolution: Wrapped `int()` conversion in `try`/`except (ValueError, IndexError)` — if parsing fails, return `SlideRegion(roi=None)`

### F-0002 — Negative ROI values break crop/mask bounds clamping
- Date: 2026-07-08
- Area: detection
- Finding: Tests for `crop()` and `apply_masks()` used negative ROI coordinates (e.g., `Roi(x1=-10, ...)`) to test boundary clamping. But `Roi` model has `Field(ge=0)` validation, rejecting negative values at construction.
- Symptom/Reproduction: test_roi.py::TestSlideRegionCrop::test_crop_clips_to_frame, TestSlideRegionMask::test_ignore_clips_to_frame
- Impact: Tests fail because Roi validation rejects negatives before they reach crop/mask
- Resolution: Changed test coordinates from negative to in-range values (e.g., `x1=0, y1=0` with `x2=500, y2=500` for a 100×200 frame)

### F-0003 — `visual_distance` returns `np.float32` rather than Python `float`
- Date: 2026-07-08
- Area: detection
- Finding: `visual_distance()` uses numpy operations internally, producing `np.float32` results. The test `test_auto_threshold` checked `isinstance(scores[0], float)` which fails for numpy float types.
- Symptom/Reproduction: test_slide_detector.py::TestDetectChanges::test_auto_threshold
- Impact: Type-check assertion failure
- Resolution: Changed assertion to `isinstance(scores[0], (float, np.floating))`

### F-0004 — `SlidesDocument` model uses `video` (VideoInfo), not `video_path`
- Date: 2026-07-08
- Area: export
- Finding: The Pydantic model `SlidesDocument` has a required `video: VideoInfo` field and `slides: list[SlideSegment]` field, not `video_path: str` and `segments: list[SlideSegment]` as initially assumed in markdown_export tests.
- Symptom/Reproduction: test_markdown_export.py::TestExportToMarkdown — Pydantic validation error "Field required: video"
- Impact: Tests fail to construct model instances
- Resolution: Updated test constructors to use `video=VideoInfo(...)` and `slides=[...]` instead of `video_path` and `segments`

### F-0005 — PyAV 18.0.0 HWAccel API: create via `av.open(path, hwaccel=HWAccel(...))`, not via codec context
- Date: 2026-07-08
- Area: tooling
- Finding: PyAV 18.0.0 exposes hardware acceleration via `av.codec.hwaccel.HWAccel` class. Setting `hwaccel` attribute on `CodecContext` is read-only. The correct approach is: `hw = HWAccel('cuda', 0)` then `av.open(path, hwaccel=hw)`. The `HWAccel.create(codec)` method is called internally by `av.open()`. `frame.to_ndarray(format='rgb24')` handles GPU→CPU transfer automatically for HW-decoded frames.
- Symptom/Reproduction: `stream.codec_context.hwaccel = 'cuda'` raises `AttributeError: not writable`; calling `HWAccel.create(codec)` before `av.open()` raises `RuntimeError: Hardware context already initialized`.
- Impact: Naive approach fails — must pass HWAccel to `av.open()` directly.
- Resolution: Implemented `pyav_iter_frames` with correct pattern: `_pick_hw_device()` → `_create_hwaccel()` → `av.open(path, hwaccel=hwaccel)`.
- LINKS: M-BACKEND-PYAV, src/video_slide_md/backends/pyav_backend.py

### F-0006 — `hwdevices_available()` returns ['cuda', 'dxva2', 'qsv', 'd3d11va', 'd3d12va', 'amf'] on RTX 4090 + Windows
- Date: 2026-07-08
- Area: tooling
- Finding: `av.codec.hwaccel.hwdevices_available()` lists all FFmpeg-compiled HW accelerators regardless of actual GPU. CUDA device creation succeeds on RTX 4090. Priority order in auto-select: cuda > d3d12va > d3d11va > qsv > dxva2.
- Symptom/Reproduction: `av.codec.hwaccel.hwdevices_available()` returns 6 device types; `HWAccel('cuda', 0)` succeeds.
- Impact: Auto-selection picks CUDA which works correctly.
- Resolution: Used in `_pick_hw_device()` with prioritized list.
- LINKS: M-BACKEND-PYAV
### F-0007 — `python-pptx` 1.0.2 blank layout index is 6
- Date: 2026-07-08
- Area: export
- Finding: `python-pptx` default template has layouts at indices 0-10. Index 6 is the blank layout (no placeholders). `prs.slide_layouts[6]` gives a completely empty slide suitable for full-bleed images.
- Symptom/Reproduction: Using `slide_layouts[0]` (title slide) leaves title/subtitle placeholders overlapping the image.
- Impact: Image would be partially hidden by text placeholders.
- Resolution: Use `prs.slide_layouts[6]` for all slides in `export_to_pptx()`.
- LINKS: M-PPTX-EXPORT

### F-0008 — `visual_distance` weights dominated by histograms — pixel MAE needed for slide dedupe
- Date: 2026-07-08
- Area: detection
- Finding: Original `visual_distance` used 70% hash (phash+dhash) and 20% histogram MSE. For lecture slides with uniform backgrounds, hash/histogram distances are tiny even for different content. Added `gray_thumb` (48x48 grayscale thumbnail) with 80% weight for pixel MAE.
- Symptom/Reproduction: Slides with similar white backgrounds but different text had `visual_distance` < 0.05 while pixel_diff was 0.05-0.07.
- Impact: Dedupe merged genuinely different slides.
- Resolution: Added `gray_thumb` to `FrameFeatures`, `_pixel_mae()` to `visual_distance`, weight 0.80.
- LINKS: M-FRAME-FEATURES, M-DEDUPE

### F-0009 — `rep_frames` dict keys must use segment `representative_timestamp`, not `vf.timestamp`
- Date: 2026-07-08
- Area: detection
- Finding: In `deduplicate_segments()`, `frames.get(seg.representative_timestamp)` always returned `None` because `rep_frames` was keyed by `vf.timestamp` (the actual sample frame timestamp like 195.0), not by the segment's `representative_timestamp` (like 156.0).
- Symptom/Reproduction: `rep_frame is None` for all segments, dedupe never triggered = before=17 after=17.
- Impact: Deduplication silently did nothing.
- Resolution: Changed `rep_frames[vf.timestamp] = ...` to `rep_frames[ts] = ...` using the segment's representative timestamp.
- LINKS: M-DEDUPE, M-CLI

### F-0010 — `notes_processor` basic cleanup does not rephrase — only joins + fixes typography
- Date: 2026-07-08
- Area: export
- Finding: `_basic_cleanup()` joins SRT cue fragments, collapses whitespace, fixes punctuation spacing, capitalizes sentences, merges short orphan lines, and deduplicates repeated words. It does NOT rephrase sentences or rewrite anything — that's the `llm` mode's job.
- Symptom/Reproduction: process_notes(basic) on "привет мир, , как дела" → "Привет мир, как дела" — punctuation fixed but sentence structure preserved.
- Impact: Basic mode is safe (no quality risk, no LLM dependency) but produces note-like text rather than polished speaker notes. Users who want rephrasing must set up LM Studio.
- Resolution: Designed as designed — two-tier approach. Basic mode for instant use, LLM mode for quality.
- LINKS: M-NOTES-PROCESSOR, M-PPTX-EXPORT
