# Findings (F-NNNN)

Журнал проблем, несовместимостей и неочевидных фактов об окружении.
Формат: одна находка = один блок `### F-NNNN`.

---

### F-0011 — LM Studio API: model load/unload endpoints are optional
- Date: 2026-07-08
- Area: llm
- Finding: LM Studio exposes OpenAI-compatible `/v1/chat/completions` but model load (`POST /v1/model/load`) and unload (`POST /v1/model/unload`) endpoints may not be available in all versions. The `LlmClient.load_model()` and `unload_model()` gracefully fall back if these endpoints return connection errors — the model is assumed to already be loaded by the user in LM Studio UI.
- Symptom/Reproduction: `POST /v1/model/load` returns 404 or connection refused if LM Studio version doesn't support the endpoint.
- Impact: Model lifecycle management is best-effort. The pipeline works regardless — model must be pre-loaded in LM Studio UI for first use.
- Resolution: `load_model()` catches `httpx.RequestError` and sets `_model_loaded = True` to continue. `unload_model()` logs warning and returns False.
- LINKS: M-LLM-CLIENT, src/video2pptx/llm_client.py

### F-0012 — Vision API requires base64 data URIs for image content
- Date: 2026-07-08
- Area: llm
- Finding: OpenAI-compatible vision API (used by LM Studio) requires images as base64-encoded data URIs in the format `data:image/{ext};base64,{b64}`, passed as `image_url` content part. File paths or raw bytes are not accepted. The `LlmClient.vision()` method reads the file, base64-encodes it, and constructs the correct data URI.
- Symptom/Reproduction: Passing raw bytes as `image_url` causes 400 error from LM Studio.
- Impact: Must read full image into memory and base64-encode — acceptable for slide screenshots (typically <500KB).
- Resolution: Implemented base64 encoding with correct MIME type detection from file extension.
- LINKS: M-LLM-CLIENT, src/video2pptx/llm_client.py

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
- LINKS: M-BACKEND-PYAV, src/video2pptx/backends/pyav_backend.py

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

### F-0013 — `httpx` is an eager import dependency for the GUI even when LLM is not used
- Date: 2026-07-09
- Area: gui
- Finding: `gui/workers.py` had a top-level `from video2pptx.llm_orchestrator import run_llm_pipeline`, which caused `llm_client.py` to import `httpx` eagerly. Users without `httpx` installed could not launch the GUI at all, even if they never intended to use LLM features.
- Symptom/Reproduction: `video2pptx gui` → `ModuleNotFoundError: No module named 'httpx'`.
- Impact: GUI was unreachable without installing `httpx`.
- Resolution: Moved the `from video2pptx.llm_orchestrator import run_llm_pipeline` import inside `LlmWorker.run()` (lazy import). The GUI now starts without `httpx`; the error only appears if the user actually triggers LLM processing.
- LINKS: M-GUI-WORKER, M-GUI-MAIN

### F-0014 — Qt6/PySide6 requires explicit `setVideoOutput()` for QVideoWidget
- Date: 2026-07-09
- Area: gui
- Finding: In Qt6/PySide6, `QMediaPlayer` does NOT automatically render to a `QVideoWidget` even if one exists in the widget tree. The call `player.setVideoOutput(video_widget)` is mandatory. Without it, audio plays but video shows a black screen.
- Symptom/Reproduction: Load video in `VideoPlayerWidget`, press play → audio heard, video area stays black.
- Impact: Video playback broken for all users.
- Resolution: Added `self._player.setVideoOutput(self._video_widget)` in `_setup_ui()` after creating `_video_widget`.
- LINKS: M-GUI-VIDEOPLAYER

### F-0015 — Subtitle overlay widget must be explicitly positioned over QVideoWidget
- Date: 2026-07-09
- Area: gui
- Finding: `SubtitleOverlayWidget` was parented to `VideoPlayerWidget` but never had its geometry set to match the `QVideoWidget` area. The overlay showed no text because it was zero-sized or positioned off-screen. `_resize_subtitle_overlay()` existed in MainWindow but was never called.
- Symptom/Reproduction: Load video with subtitles, play — subtitle text prints in log but nothing visible on screen.
- Impact: Subtitles invisible.
- Resolution: Moved overlay management into `VideoPlayerWidget` via `set_overlay_widget(w)` + `resizeEvent` override that calls `_position_overlay()`, which sets overlay geometry to match `_video_widget.geometry()` on every resize.
- LINKS: M-GUI-VIDEOPLAYER, M-GUI-SUBTITLE-OVERLAY

### F-0017 — `httpx` module-level import in `llm_client.py` crashes `ModelListCombo.showPopup()` and `Test Connection`
- Date: 2026-07-09
- Area: llm
- Finding: `import httpx` at module level in `llm_client.py` causes `ModuleNotFoundError` when `settins_app.py` imports `LlmClient` (lazily) for `ModelListCombo._fetch_and_populate()` and `_do_test_llm()`. The error propagates through `showPopup()` override → `QComboBox` Python override error → console spam, and crashes the "Test Connection" button handler.
- Symptom/Reproduction: Open App Settings → click LLM tab → click model dropdown → 5 repeated `Error calling Python override of QComboBox::showPopup()` + `ModuleNotFoundError: No module named 'httpx'`. Click "Test Connection" → same error.
- Impact: GUI unusable for users without `httpx` installed, even if they never use LLM features.
- Resolution: Wrapped `import httpx` in try/except at module level with `_HAS_HTTPX` flag. `LlmClient.__init__` now raises clear `ImportError` with install instructions only when instantiation is attempted. Both callers in `settings_app.py` already catch `Exception` → no more crash.
- LINKS: M-LLM-CLIENT, M-GUI-SETTINGS-APP, src/video2pptx/llm_client.py, src/video2pptx/gui/settings_app.py

### F-0016 — QVideoWidget hardware overlay renders above all QWidget siblings; use QGraphicsVideoItem instead
- Date: 2026-07-09
- Area: gui
- Finding: `QVideoWidget` renders video via platform-specific hardware overlay (Direct3D on Windows, etc.) which is outside Qt's widget stacking order. No amount of `raise_()`, `WA_NativeWindow`, or Z-order manipulation can make a regular `QWidget` (including `QLabel`) render on top of the video surface.
- Symptom/Reproduction: Subtitle text is synced and positioned correctly (verified via test) but invisible to user. Audio plays, video shows, overlay geometry is correct — text just never appears on screen.
- Impact: All text overlays (subtitles, UI labels) are invisible on top of QVideoWidget.
- Resolution: Replaced `QVideoWidget` + `QLabel` overlay with `QGraphicsView` + `QGraphicsScene` + `QGraphicsVideoItem` for video, and `QGraphicsSimpleTextItem` (ZValue=1) for subtitles. Graphics items live in the same scene and respect z-ordering natively.
- LINKS: M-GUI-VIDEOPLAYER, M-GUI-SUBTITLE-OVERLAY
