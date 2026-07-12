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

---

<!-- Release hardening findings (F-0022+) -->

### F-0022 — Markdown export produces double path prefix "slides/slides/slide_001.png"
- Date: 2026-07-10
- Area: export
- Finding: `markdown_export.render_slide()` computed `Path(slides_dir) / seg.image` where `seg.image` was already `"slides/slide_001.png"`, producing `"slides/slides/slide_001.png"`. The image link in deck.md was broken.
- Symptom/Reproduction: Run `export-md slides.json`, inspect deck.md → image links contain double `slides/slides/` prefix.
- Impact: Marp renders broken image links in generated presentations.
- Resolution: Created `paths.resolve_markdown_image_path()` that checks if the stored path already has a `slides/` prefix before prepending. All image paths in markdown now route through this resolver.
- LINKS: M-MD-EXPORT, M-PATHS, src/video2pptx/markdown_export.py, src/video2pptx/paths.py

### F-0023 — `export-md` CLI params silently ignored (--image-as-bg, --transcript-location, --timecodes)
- Date: 2026-07-10
- Area: cli
- Finding: The `export_md` command declared `image_as_background`, `transcript_location`, and `include_timecodes` parameters but never passed them to `export_to_markdown()`. The function signature didn't even accept them.
- Symptom/Reproduction: `video2pptx export-md slides.json --no-image-bg` → output still uses background image.
- Impact: Users cannot configure Markdown export formatting despite documented parameters.
- Resolution: Extended `export_to_markdown()` and `render_slide()` to accept and honor all three parameters. CLI now passes them through.
- LINKS: M-CLI, M-MD-EXPORT

### F-0024 — Circular dependency smell: `notes_processor` imports `_fmt_time` from `pptx_export`
- Date: 2026-07-10
- Area: export
- Finding: `notes_processor._llm_rephrase()` imported `_fmt_time` from `pptx_export.py`, creating a coupling between two independent export modules. This made `notes_processor` depend on `python-pptx` being importable.
- Symptom/Reproduction: Import chain: notes_processor → pptx_export → pptx (python-pptx). If python-pptx not installed, notes processing in LLM mode fails at import time.
- Impact: Notes processing unnecessarily coupled to PPTX export.
- Resolution: Created `paths.format_time()` as the single source for time formatting. Both `pptx_export` and `notes_processor` now use it.
- LINKS: M-NOTES-PROCESSOR, M-PPTX-EXPORT, M-PATHS

### F-0025 — `run_llm_pipeline` leaks httpx.Client and never calls unload_model
- Date: 2026-07-10
- Area: llm
- Finding: `run_llm_pipeline()` created `LlmClient`, called `load_model()`, processed slides, but never called `close()` or `unload_model()`. The contract and README promised model unload after processing. The httpx.Client TCP connections and the LM Studio model in VRAM were left leaked.
- Symptom/Reproduction: Run `detect --llm`, check LM Studio → model still loaded in VRAM. Check process → open TCP connections to localhost:1234 not closed.
- Impact: VRAM not freed; TCP connection leak on repeated runs.
- Resolution: Wrapped pipeline body in `try/finally`. Finally block calls `unload_model()` if `unload_when_done=true`, then `close()` unconditionally.
- LINKS: M-LLM-ORCHESTRATOR, M-LLM-CLIENT

### F-0026 — `detect --llm --export-md/--export-pptx` exports stale pre-LLM document
- Date: 2026-07-10
- Area: cli
- Finding: `cli.detect` built an in-memory `doc` object, then ran LLM enrichment (which writes enriched data to slides.json on disk), but subsequent `export_md`/`export_pptx` calls used the stale in-memory `doc` — not the enriched version.
- Symptom/Reproduction: Run `detect video.mp4 --llm --export-pptx` → PPTX notes contain pre-LLM transcript, not corrected/enriched text.
- Impact: LLM enrichment silently lost on export.
- Resolution: Added `doc = SlidesDocument.model_validate_json(json_path.read_text(...))` after LLM pipeline to reload enriched document before exports.
- LINKS: M-CLI, M-LLM-ORCHESTRATOR

### F-0027 — Missing `gui` extra in pyproject.toml; README documents `pip install video2pptx[gui]`
- Date: 2026-07-10
- Area: tooling
- Finding: README instructed users to `pip install video2pptx[gui]` but the `gui` extra did not exist in `pyproject.toml [project.optional-dependencies]`. Installation failed with "No matching distribution" or silently installed without GUI.
- Symptom/Reproduction: `pip install "video2pptx[gui]"` → PySide6 not installed.
- Impact: GUI installation path broken as documented.
- Resolution: Added proper extras: `gui` (PySide6), `pptx` (python-pptx), `llm` (httpx), `gpu` (av), `dev` (pytest+ruff+mypy), `all`.
- LINKS: pyproject.toml, README.md

### F-0028 — `httpx` required by llm_client but absent from dependencies
- Date: 2026-07-10
- Area: tooling
- Finding: `llm_client.py` imports `httpx` but it was not listed in `pyproject.toml` dependencies (neither base nor optional). Users running `llm-process` or `notes --notes-mode llm` got `ModuleNotFoundError`.
- Symptom/Reproduction: `pip install video2pptx && video2pptx llm-process slides.json` → ModuleNotFoundError: httpx.
- Impact: LLM features completely broken after clean install.
- Resolution: Added `httpx>=0.27` to `[llm]` extra and `[all]` extra.
- LINKS: pyproject.toml, M-LLM-CLIENT

### F-0029 — Version mismatch: `__version__` 0.1.0 vs pyproject 0.5.0
- Date: 2026-07-10
- Area: tooling
- Finding: `pyproject.toml` declared `version = "0.5.0"` while `__init__.py` had `__version__ = "0.1.0"`. Package metadata and runtime version disagreed.
- Symptom/Reproduction: `pip show video2pptx` → Version: 0.5.0; `python -c "import video2pptx; print(video2pptx.__version__)"` → 0.1.0.
- Impact: Version-dependent logic and debugging confused.
- Resolution: Switched to hatch dynamic version from `__init__.py` as single source of truth. Updated `__version__` to 0.5.0.
- LINKS: pyproject.toml, src/video2pptx/__init__.py

### F-0030 — `Private :: Do Not Upload` classifier conflicts with public install instructions
- Date: 2026-07-10
- Area: tooling
- Finding: `pyproject.toml` classifiers included `"Private :: Do Not Upload"` (PyPI safety flag) while README documented `pip install video2pptx` (implying PyPI publication). The classifier prevents accidental PyPI upload.
- Symptom/Reproduction: `python -m twine upload` would warn or refuse due to this classifier.
- Impact: Conflicting intent signals.
- Resolution: Removed the classifier. Added `"Development Status :: 4 - Beta"` and `"License :: OSI Approved :: MIT License"`.
- LINKS: pyproject.toml

### F-0031 — Placeholder documentation URL `github.com/user/video2pptx`
- Date: 2026-07-10
- Area: tooling
- Finding: `[project.urls] Documentation` pointed to `https://github.com/user/video2pptx` — a placeholder that doesn't resolve.
- Symptom/Reproduction: `pip show video2pptx` → URL leads to 404.
- Impact: Users can't find documentation from package metadata.
- Resolution: Updated all URLs to `https://github.com/kucheryavenkovn/video2pptx`.
- LINKS: pyproject.toml

### F-0032 — `notes --notes-mode llm` does not pass LlmConfig to run_notes
- Date: 2026-07-10
- Area: cli
- Finding: `cli.notes_cmd` called `run_notes(notes_mode="llm")` without passing `llm_config`. Since `run_notes` checks `if notes_mode == "llm" and llm_config is not None`, the LLM path was never taken — it silently fell back to basic.
- Symptom/Reproduction: `video2pptx notes slides.json --subtitles subs.srt --notes-mode llm` → output identical to basic mode, no LLM call made.
- Impact: LLM notes mode silently non-functional from CLI.
- Resolution: `notes_cmd` now loads config and passes `llm_config` when `notes_mode == "llm"`.
- LINKS: M-CLI, M-NOTES

### F-0033 — PPTX export `notes_mode=llm` silently executes basic mode (no LLM client)
- Date: 2026-07-10
- Area: export
- Finding: `pptx_export._format_slide_notes()` called `process_notes(seg, mode="llm")` without an `llm_client`. Inside `process_notes`, `mode == "llm" and llm_client is None` falls through to `_basic_cleanup()`. Users got basic output despite requesting LLM mode.
- Symptom/Reproduction: `export-pptx slides.json --notes-mode llm` → PPTX notes identical to `--notes-mode basic`.
- Impact: Silent mode mismatch; users believe LLM processing was done.
- Resolution: `_format_slide_notes` now uses pre-enriched `seg.transcript` (processed by pipeline before export) with `seg.llm_description` as header. Mode is effectively `basic` cleanup of already-enriched text.
- LINKS: M-PPTX-EXPORT

### F-0034 — Two independent detection pipeline implementations (cli.detect vs run_detect_slides)
- Date: 2026-07-10
- Area: detection
- Finding: `cli.detect()` reimplemented the entire detection pipeline (open video, detect changes, build segments, dedupe, save screenshots, build document) — ~100 lines duplicated from `run_detect_slides()`. The two implementations could diverge, leading to inconsistent behavior between `detect` and `detect-slides` commands.
- Symptom/Reproduction: Bug fixes in `run_detect_slides` (e.g., quick_mode support, progress callback) were not reflected in `cli.detect`.
- Impact: Maintenance burden; behavioral divergence risk.
- Resolution: `cli.detect` now delegates to `run_detect_slides()` for core detection, then adds subtitles/LLM/export as post-processing.
- LINKS: M-CLI, M-DETECT-SLIDES, M-PIPELINE

### F-0035 — Committed output artifacts, input files, and session logs in git
- Date: 2026-07-10
- Area: tooling
- Finding: The repository tracked output directories (out2/ through out7/ with slides.json, deck.md, deck.pptx), an input subtitle file (in/*.srt), session log files (session-ses_*.md, opencode_today.md), root project.json, and .mcp_port — all of which are local runtime artifacts that should not be in version control.
- Symptom/Reproduction: `git ls-files` shows 13 output artifacts + session files.
- Impact: Repository bloat; merge conflicts; accidental exposure of local paths.
- Resolution: Removed all from git tracking via `git rm --cached`. Updated `.gitignore` to prevent re-adding.
- LINKS: .gitignore

### F-0036 — One-time migration script `add_decorators.py` tracked as project file
- Date: 2026-07-10
- Area: tooling
- Finding: `.opencode/scripts/add_decorators.py` was a one-time code modification script that injected `@mcp_action` decorators into `main_window.py`. It was committed and remained tracked despite being a single-use migration tool.
- Symptom/Reproduction: File present in `git ls-files`, confusing for new contributors.
- Impact: Misleading project structure.
- Resolution: Deleted from disk and git tracking.
- LINKS: .opencode/scripts/

### F-0017 — `httpx` module-level import in `llm_client.py` crashes `ModelListCombo.showPopup()` and `Test Connection`
- Date: 2026-07-09
- Area: llm
- Finding: `import httpx` at module level in `llm_client.py` causes `ModuleNotFoundError` when `settins_app.py` imports `LlmClient` (lazily) for `ModelListCombo._fetch_and_populate()` and `_do_test_llm()`. The error propagates through `showPopup()` override → `QComboBox` Python override error → console spam, and crashes the "Test Connection" button handler.
- Symptom/Reproduction: Open App Settings → click LLM tab → click model dropdown → 5 repeated `Error calling Python override of QComboBox::showPopup()` + `ModuleNotFoundError: No module named 'httpx'`. Click "Test Connection" → same error.
- Impact: GUI unusable for users without `httpx` installed, even if they never use LLM features.
- Resolution: Wrapped `import httpx` in try/except at module level with `_HAS_HTTPX` flag. `LlmClient.__init__` now raises clear `ImportError` with install instructions only when instantiation is attempted. Both callers in `settings_app.py` already catch `Exception` → no more crash.
- LINKS: M-LLM-CLIENT, M-GUI-SETTINGS-APP, src/video2pptx/llm_client.py, src/video2pptx/gui/settings_app.py

### F-0018 — `_on_slide_resized` has duplicate saves + missing timeline refresh
- Date: 2026-07-09
- Area: gui
- Finding: `MainWindow._on_slide_resized` called `save_project()` twice and `statusBar().showMessage()` twice without calling `self._timeline.set_slides()`. After resizing a slide block, the visual did not update until a full redraw (zoom change, add slide, etc.).
- Symptom/Reproduction: Drag edge of slide block on timeline → block snaps back to old size visually. Log shows two `Project saved` messages and two status bar messages.
- Impact: Timeline visual out of sync after resize; double save is harmless but wasteful.
- Resolution: Removed duplicate `save_project()` + `showMessage()`. Added `self._timeline.set_slides(self._project.slides)` to refresh visual after resize.
- LINKS: M-GUI-MAIN, src/video2pptx/gui/main_window.py:750

### F-0019 — Manual slide position adjustments lost on project reopen
- Date: 2026-07-09
- Area: gui
- Finding: `open_project()` calls `load_slides_into_project()` which always overwrites `project.slides` from `slides.json` (the canonical detection artifact). Manual position adjustments persisted in `project.json` via `save_project()` are lost because `load_slides_into_project` unconditionally reloads from `slides.json`.
- Symptom/Reproduction: Move/resize a slide block → close project → reopen → positions reset to original detection values.
- Impact: All manual timeline adjustments lost on reopen.
- Resolution: Added `force: bool = False` parameter to `load_slides_into_project()`. Only overwrites `project.slides` from `slides.json` if `force=True` or `project.slides` is empty. New detection (`_on_detect_finished`) and notes (`_on_notes_finished`) pass `force=True`.
- LINKS: M-PROJECT, M-GUI-MAIN, src/video2pptx/project_manager.py:272

### F-0020 — `SlideBlockItem._start_sec`/`_end_sec` not updated after move/resize
- Date: 2026-07-09
- Area: gui
- Finding: `SlideBlockItem` stores `_start_sec` and `_end_sec` at construction but never updates them after a drag move or edge resize. The `on_moved`/`on_resized` callbacks emit correct new values to MainWindow, but `item.start_sec()` still returns the original value.
- Symptom/Reproduction: After moving a slide block, `item.start_sec()` returns old (pre-move) value. The context menu subtitle viewer (`_show_slide_subtitles`) reads these stale values.
- Impact: Context menu subtitle region uses wrong time bounds after any drag or resize.
- Resolution: Set `self._start_sec = new_start` and `self._end_sec = new_end` after computing the new values in `mouseReleaseEvent`.
- LINKS: M-GUI-TIMELINE3-ITEMS, src/video2pptx/gui/timeline3/items.py:138

### F-0021 — `MainWindow.closeEvent` does not clear timeline on window close
- Date: 2026-07-09
- Area: gui
- Finding: `closeEvent` only saves `last_project_path` to app config but does not call `_on_close_project()`. The timeline, project state, and video player are not cleared when the user closes the window directly (vs. using File → Close Project).
- Symptom/Reproduction: Open project → close window via `X` button → reopen app → previous project data still visible in timeline.
- Impact: Leftover state from previous session visible in GUI until a new project is opened or closed via menu.
- Resolution: Added `self._on_close_project()` call at end of `closeEvent()`.
- LINKS: M-GUI-MAIN, src/video2pptx/gui/main_window.py:438

### F-0016 — QVideoWidget hardware overlay renders above all QWidget siblings; use QGraphicsVideoItem instead
- Date: 2026-07-09
- Area: gui
- Finding: `QVideoWidget` renders video via platform-specific hardware overlay (Direct3D on Windows, etc.) which is outside Qt's widget stacking order. No amount of `raise_()`, `WA_NativeWindow`, or Z-order manipulation can make a regular `QWidget` (including `QLabel`) render on top of the video surface.
- Symptom/Reproduction: Subtitle text is synced and positioned correctly (verified via test) but invisible to user. Audio plays, video shows, overlay geometry is correct — text just never appears on screen.
- Impact: All text overlays (subtitles, UI labels) are invisible on top of QVideoWidget.
- Resolution: Replaced `QVideoWidget` + `QLabel` overlay with `QGraphicsView` + `QGraphicsScene` + `QGraphicsVideoItem` for video, and `QGraphicsSimpleTextItem` (ZValue=1) for subtitles. Graphics items live in the same scene and respect z-ordering natively.
- LINKS: M-GUI-VIDEOPLAYER, M-GUI-SUBTITLE-OVERLAY

---

<!-- MCP E2E Hardening findings (F-0037+) -->

### F-0037 — ProjectModel.create passes 'name' as 'video_path' positional arg
- Date: 2026-07-10
- Area: project
- Finding: `ProjectModel.create(path, name)` called `create_project(str(out_dir), name)` — the second positional arg of `create_project` is `video_path`, not `name`. The project name was interpreted as a video file path.
- Symptom/Reproduction: MCP `project_create` → project directory not created at expected path.
- Impact: Project creation broken via MCP.
- Resolution: Changed to `create_project(str(Path(path) / name), name=name)`.
- LINKS: M-PROJECT-MODEL, src/video2pptx/project_model.py:105

### F-0038 — MCP server _send_json missing Content-Length causes HTTP client timeout
- Date: 2026-07-10
- Area: debug
- Finding: The MCP HTTP server's `_send_json` didn't set `Content-Length`. The client waits for connection close, server keeps open → 30s+ timeouts.
- Symptom/Reproduction: Any MCP tool call after `initialize` → client hangs until timeout.
- Impact: MCP server unusable for automated testing.
- Resolution: Added `Content-Length` header + `close_connection=True` + `/health` endpoint.
- LINKS: M-DEBUG-MCP

### F-0039 — OpenCV cannot open paths with non-ASCII chars on Windows
- Date: 2026-07-10
- Area: video
- Finding: `cv2.VideoCapture` on Windows fails for paths with Cyrillic characters. Returns `isOpened()=False` silently.
- Impact: All video processing broken for non-English Windows users.
- Resolution: Added `_win_short_path()` using `GetShortPathNameW` ctypes.
- LINKS: M-BACKEND-OPENCV

### F-0040 — quick_extract returns list[float], detect_changes needs settable .timestamp
- Date: 2026-07-10
- Area: detection
- Finding: `detect_changes` sets `ff.timestamp = timestamp` on extracted features. `quick_extract` returned `list[float]` which doesn't support attribute assignment.
- Impact: Quick Preview pipeline non-functional.
- Resolution: Created `QuickFrame` dataclass with `thumb` and `timestamp`. Updated `quick_extract` and `quick_visual_distance`.
- LINKS: M-FRAME-FEATURES

### F-0041 — GRACE XML malformed: unescaped `<` in attribute values and element text
- Date: 2026-07-10
- Area: tooling, docs
- Finding: Several GRACE XML files contained unescaped `<` characters in attribute values (e.g., `val="&lt;=5%"`) and element text (`max-min < snap_flat_threshold`), causing `xml.parsers.expat` to fail. `grace lint` tolerates these (lenient parser) but strict XML tools reject them.
- Symptom/Reproduction: `python -c "import xml.dom.minidom as m; m.parse('docs/verification-plan.xml')"` fails with "not well-formed (invalid token)".
- Impact: Strict XML validation tools cannot process GRACE docs.
- Resolution: Fixed `&lt;=` in attribute values and unescaped `<` in element text.
- LINKS: docs/development-plan.xml, docs/verification-plan.xml

### F-0042 — app_service.py is dead code: never called from GUI, CLI, or MCP
- Date: 2026-07-10
- Area: architecture
- Finding: `src/video2pptx/app_service.py` implements `run_detect`, `run_preview`, `run_auto_align`, `run_export_md`, `run_export_pptx`, `run_auto` — but neither GUI, CLI, nor MCP calls them. All paths call `run_detect_slides` directly.
- Symptom/Reproduction: grep for `app_service` imports across src/ returns zero (only the defining file).
- Impact: Canonical command architecture requires retrofitting app_service as single entry point.
- Resolution: Phase 2 wires app_service into GUI/MCP/CLI.
- LINKS: M-APP-SERVICE, src/video2pptx/app_service.py

### F-0043 — MCP OpRunnerThread lacks Qt binding: app_service commands cannot mutate ProjectModel
- Date: 2026-07-10
- Area: mcp, architecture
- Finding: `AppServiceRunner` runs `app_service.execute_command` in a background `OpRunnerThread`. However, `detect` and other pipeline commands call `run_detect_slides` which is a standalone function that writes directly to disk — it does NOT go through ProjectModel. GUI refresh depends on ProjectModel Qt signals, which are not triggered by disk-only writes. Auto Align (`run_auto_align`) modifies `slides` in memory and writes `slides.json` but does not emit `slidesChanged`.
- Impact: After MCP-driven detect/align, the GUI timeline may not refresh automatically. A project_save → project_close → project_open cycle is needed for now.
- Resolution: Documented as known limitation. Phase 2 wiring (app_service → ProjectModel signals) is the planned fix — but app_service must remain Qt-free.
- LINKS: M-MCP-OPERATIONS, M-APP-SERVICE

### F-0044 — F-0043 resolved: completion bridge via drain_completed_ops + mcp_process_queue timer
- Date: 2026-07-10
- Area: mcp, architecture
- Finding: F-0043 fixed by adding `record_completed`/`drain_completed_ops` bridge from OpRunnerThread to Qt main thread. After any MCP operation completes, `OpRunner` records the operation_id. The existing `mcp_process_queue` QTimer (50ms in Qt main thread) drains completed ops and calls `model.refresh_from_disk()`, which re-reads project.json + slides.json, syncs timeline, and emits `slidesChanged`/`scoresChanged`/`videoChanged` signals. No Close/Open needed.
- Symptom/Reproduction: MCP `detect` followed by `get_timeline` now returns updated data without Close/Open.
- Impact: All MCP write commands now trigger automatic GUI refresh.
- Resolution: Implemented in commit 858a8e1. Also added missing `project_path` property to ProjectModel.
- LINKS: M-MCP-OPERATIONS, M-PROJECT-MODEL

### F-0045 — ProjectModel lacked `project_path` property; MCP read tools referenced undefined attribute
- Date: 2026-07-10
- Area: architecture
- Finding: `mcp_read_tools.py` and `mcp_server.py` referenced `model.project_path` but `ProjectModel` had no such property. `create()` and `open()` didn't store the project directory. The property was implicitly None, causing MCP read tools to miss project path context.
- Symptom/Reproduction: `model.project_path` always returned None, breaking `list_artifacts` and `get_project(project_dir)`.
- Impact: MCP read tools returned incomplete project data.
- Resolution: Added `_project_path` attribute, `project_path` property, stored path in `create()` and `open()`, cleared in `close()`.
- LINKS: M-PROJECT-MODEL, M-MCP-READ-TOOLS

### F-0046 — CLI has no Quick Preview use case
- Date: 2026-07-10
- Area: architecture, cli
- Finding: Direct application service and GUI expose Quick Preview, but the Typer CLI has no equivalent command. The CLI only exposes full `detect` and `detect-slides`.
- Symptom/Reproduction: inspect `src/video2pptx/cli.py`; no preview command is registered.
- Impact: Adapter equivalence cannot currently be characterized for Preview across direct service, CLI, MCP, and GUI.
- Resolution/Status: Open for Phase-16 Step 7. Phase-1 characterization covers valid direct Preview invariants and records the adapter gap rather than treating it as desired behavior.
- LINKS: M-APP-SERVICE, M-CLI, V-REF-CHAR-TESTS

### F-0047 — MCP E2E runner bypasses GUI and MCP transport
- Date: 2026-07-10
- Area: tooling, mcp
- Finding: `tools/mcp_e2e_runner.py::run_e2e` imports and calls `run_preview`, `run_detect`, `run_auto_align`, and exporters directly. It does not launch `video2pptx gui`, discover an instance-owned MCP port, or call MCP tools.
- Symptom/Reproduction: `tools/mcp_e2e_runner.py:113-128` explicitly describes and implements direct Python API execution.
- Impact: Existing runner results cannot certify GUI/MCP operation lifecycle or adapter synchronization.
- Resolution/Status: Open in Phase-16 Step 1. A real subprocess/MCP harness must replace the direct path before characterization is complete.
- LINKS: M-E2E-RUNNER, M-DEBUG-MCP, V-REF-CHAR-TESTS

### F-0048 — Qt-affine MCP commands had no operation lifecycle and lost arguments
- Date: 2026-07-10
- Area: mcp, architecture
- Finding: `project_create`, project lifecycle, media import, and slide mutations used `_CMD_QUEUE` but returned only `{status: queued}` without an operation ID. `project_create` forwarded only `path`; `name` was silently dropped, creating `Untitled`.
- Symptom/Reproduction: real GUI MCP call `project_create(path=..., name='characterized')` created `projects/Untitled/project.json` and could not be awaited through `wait_operation`.
- Impact: E2E synchronization was impossible and the requested project identity was corrupted.
- Resolution/Status: Fixed. Qt-affine commands now create OperationRegistry entries, transition in the Qt timer, return structured terminal state, preserve `name`, and use the common completion bridge.
- LINKS: M-DEBUG-MCP, M-OPERATION-REGISTRY, V-REF-CHAR-TESTS

### F-0049 — get_project fallback hid project_dir due to str/Path mismatch
- Date: 2026-07-10
- Area: mcp, persistence
- Finding: `ProjectModel.project_path` is a string while `_find_artifact_paths` assumed `Path` and used `/`. The exception activated the legacy fallback serializer, dropping `project_dir`, pipeline details, and artifact paths.
- Symptom/Reproduction: subprocess log contained `get_project fallback: unsupported operand type(s) for /: 'str' and 'str'`.
- Impact: MCP state snapshots were incomplete even though the project was valid.
- Resolution/Status: Fixed by normalizing the adapter boundary with `Path(project_dir)`.
- LINKS: M-MCP-READ-TOOLS, M-PROJECT-MODEL, V-REF-CHAR-TESTS

### F-0050 — ProjectModel lacked a project-opened event for adapter refresh
- Date: 2026-07-10
- Area: gui, architecture
- Finding: GUI-originated code manually called `MainWindow._on_project_opened()`, while MCP-originated `ProjectModel.create/open/refresh_from_disk` had no neutral event. Model and disk updated but the window title and button state remained stale.
- Symptom/Reproduction: real MCP `project_create` succeeded and `get_project` returned the new project, while `get_ui_state.window_title` remained `video2pptx`.
- Impact: F-0043 remained partially unresolved for project lifecycle commands.
- Resolution/Status: Fixed with `ProjectModel.projectOpened` signal. MainWindow subscribes as a GUI adapter; manual lifecycle slot calls were removed.
- LINKS: M-PROJECT-MODEL, M-GUI-MAIN, V-REF-CHAR-TESTS

### F-0051 — AppServiceRunner could not execute project operations or persist their results
- Date: 2026-07-10
- Area: mcp, architecture
- Finding: `AppServiceRunner` treated `ProjectModel.project_path` as `Path`, did not map `quick_preview` to the application command `preview`, marked `{success:false}` results as successful operations, and did not persist Detect/Preview/Align/Export results into project state.
- Symptom/Reproduction: real MCP Detect failed with `unsupported operand type(s) for /: 'str' and 'str'`; after correcting the path, successful filesystem output would still be absent from `ProjectModel` after refresh.
- Impact: E2E-006 and E2E-007 could not be characterized through real GUI+MCP.
- Resolution/Status: Fixed with a temporary compatibility persistence bridge in `AppServiceRunner`. It maps adapter command names, propagates application failures, updates project pipeline state and artifacts, and is explicitly scheduled for removal in Phase-16 Step 5 when repository-backed application services own persistence.
- LINKS: M-MCP-OPERATIONS, M-APP-SERVICE, M-PROJECT, V-REF-CHAR-TESTS

### F-0052 — Windows allowed multiple MCP instances to share port 9812
- Date: 2026-07-10
- Area: mcp, os, tooling
- Finding: `_ThreadedServer.allow_reuse_address=True` allowed a new Windows process to bind `127.0.0.1:9812` while an orphan GUI process still listened on the same port. Requests were routed to either instance. The plain integer `.mcp_port` and anonymous health response could not prove ownership.
- Symptom/Reproduction: repeated real startup tests intermittently observed another project's enabled buttons and stale pipeline state; `Get-NetTCPConnection` showed an older Python owner while the new server also logged port 9812.
- Impact: E2E results were nondeterministic and cleanup could target the wrong port file.
- Resolution/Status: Fixed. Address reuse is disabled; occupied ports increment. `.mcp_port` and `/health` expose matching `port`, `pid`, `started_at`, and `instance_id`; the harness accepts only its subprocess-owned endpoint and isolates the GUI home directory.
- LINKS: M-DEBUG-MCP, M-E2E-RUNNER, V-REF-CHAR-TESTS

### F-0053 — Terminal operation status preceded Qt model synchronization
- Date: 2026-07-10
- Area: mcp, gui
- Finding: application operations were marked `succeeded` before the Qt timer consumed the completion queue and called `ProjectModel.refresh_from_disk()`.
- Symptom/Reproduction: `wait_operation` returned `succeeded`, followed immediately by `get_project.detect_done=false`; isolated runs sometimes passed because the timer won the race.
- Impact: The documented terminal lifecycle did not guarantee safe state inspection.
- Resolution/Status: Fixed with explicit completion synchronization tracking. `wait_operation` holds successful operations until their Qt refresh has completed.
- LINKS: M-MCP-OPERATIONS, M-DEBUG-MCP, V-REF-CHAR-TESTS

### F-0054 — Auto Align dry-run mutated project state and refreshed timeline
- Date: 2026-07-10
- Area: mcp, architecture
- Finding: `run_auto_align(dry_run=True)` preserved `slides.json`, but the MCP compatibility bridge still set `align_done`, wrote `project.json`, and triggered a Qt refresh that regenerated timeline UIDs. Confirmation was also required despite no intended mutation.
- Symptom/Reproduction: real MCP dry-run changed project/timeline snapshots while returning `dry_run=true`.
- Impact: E2E-008 could not provide a trustworthy preview of alignment changes.
- Resolution/Status: Fixed. Dry-run bypasses destructive confirmation, project persistence, and completion refresh. Apply writes both alignment JSON artifacts atomically.
- LINKS: M-APP-SERVICE, M-MCP-OPERATIONS, M-MCP-WRITE-TOOLS, V-REF-CHAR-TESTS

### F-0055 — Advertised slide CRUD did not mutate the persisted project
- Date: 2026-07-10
- Area: mcp, gui, persistence
- Finding: add/delete rebuilt the timeline from unchanged `Project.slides`, move was timeline-only, three CRUD tools routed to unknown application commands, and timeline UIDs changed on every reload.
- Symptom/Reproduction: MCP add returned queued but the slide disappeared after completion refresh; UID lookup failed after reopen.
- Impact: E2E-011 and adapter parity were impossible; Save/Open could not preserve edits.
- Resolution/Status: Fixed for characterization with persisted string UIDs, atomic `slides.json` updates, project/timeline synchronization, UID-preferred MCP routing, interval validation, and frame capture. Phase 2 will replace the string field with the `SlideId` value object.
- LINKS: M-MODELS, M-PROJECT-MODEL, M-CANONICAL-COMMANDS, M-DEBUG-MCP, V-REF-CHAR-TESTS

### F-0056 — Project close left Auto actions enabled and project writes were non-atomic
- Date: 2026-07-10
- Area: gui, persistence
- Finding: the close handler reset most controls but omitted Auto and Auto Align. `save_project()` also contradicted the graph's atomic-write contract by writing `project.json` directly.
- Symptom/Reproduction: after real MCP close, an action requiring an open project could remain enabled; interruption during save could leave partial JSON.
- Impact: E2E-014 postconditions and persistence guarantees were incomplete.
- Resolution/Status: Fixed. Close disables all project-dependent actions and `save_project()` uses the shared atomic JSON writer. Full repository/schema migration remains Phase 4.
- LINKS: M-GUI-MAIN, M-PROJECT, M-ATOMIC-JSON, V-REF-CHAR-TESTS

### F-0057 — MCP exports discarded the project title
- Date: 2026-07-10
- Area: export, mcp
- Finding: GUI supplied `Project.name`, but AppServiceRunner omitted it, so MCP Markdown used `Presentation`; PPTX accepted a title argument but did not persist it in package metadata.
- Symptom/Reproduction: export a named project through MCP and inspect `deck.md` front matter or PPTX core properties.
- Impact: Adapter outputs were structurally different and lost project identity.
- Resolution/Status: Fixed. The MCP application adapter supplies project name to both exporters and PPTX writes it to Open XML core properties. Overwrite-policy cleanup remains assigned to adapter migration.
- LINKS: M-APP-SERVICE, M-MCP-OPERATIONS, M-MD-EXPORT, M-PPTX-EXPORT, V-REF-CHAR-TESTS

### F-0058 — Video transport MCP tools routed to wrong object
- Date: 2026-07-10
- Area: mcp, gui
- Finding: `video_seek`, `video_play`, `video_pause` are in `_QT_WRITE_CMDS` and execute against `ProjectModel`, but the actual methods are on `VideoPlayerWidget`, not on `ProjectModel`. All three fail with `AttributeError: ProjectModel command not found`.
- Symptom/Reproduction: real MCP `video_seek(position=3.0)` returns failed operation with `ProjectModel command not found: seek`.
- Impact: E2E-005 Playback cannot be characterized through MCP.
- Resolution/Status: Resolved in Step 8.5. MCP queue routes play/pause to VideoPlayerWidget and seek to MainWindow's seek adapter; a real RPC-to-queue GUI regression test verifies routing.
- LINKS: M-DEBUG-MCP, M-GUI-VIDEOPLAYER, V-REF-CHAR-TESTS

### F-0059 — Schema 2.0 persistence contract was unstable for application service consumption
- Date: 2026-07-11
- Area: persistence, architecture
- Finding: The initial FileProjectRepository (Step 4) read and wrote schema 2.0 through the legacy `project_manager.Project` Pydantic model, losing full PipelineState (FAILED/STALE/CANCELLED/SKIPPED, operation_id, timestamps, error). The mapper called `replace_detected_slides()` during load, causing downstream invalidation as a side effect of hydration. `load()` did not return revision, making the standard `load→edit→save` optimistic cycle impossible. Absolute `output_dir` was persisted in the canonical document. Corrupt canonical documents could be silently overwritten when `expected_revision` was provided. `slides.json` lacked `source_revision`. `validate_storage()` only checked JSON syntax. `SlideId.new()` used only 48 bits of randomness.
- Symptom/Reproduction: Open a project with `notes_done=True`, close, reopen — notes stage could be STALE instead of SUCCEEDED due to rehydration invalidation.
- Impact: Application services cannot safely depend on the repository until the contract is stabilized.
- Resolution/Status: Resolved by Checkpoints 5.0A–5.0D. Persistence now uses strict ProjectDocumentV2, full side-effect-free state mapping, portable runtime roots, extension preservation, LoadedProject revision cycles, corrupt-document protection, revisioned derived artifacts, strict storage validation, aggregate validation, and 128-bit SlideId.
- LINKS: M-PORT-REPO, M-FILE-REPO, M-PERSIST-DTO, V-REF-PERSISTENCE-STABILIZATION

### F-0060 — Active Python environment lacks optional mypy dependency
- Date: 2026-07-11
- Area: tooling
- Finding: The active Python 3.14 interpreter does not have the optional `mypy` development dependency installed.
- Symptom/Reproduction: `python -m mypy src/video2pptx/infrastructure/persistence/dto.py src/video2pptx/domain/identifiers.py` returns `No module named mypy`.
- Impact: Checkpoint 5.0A could not produce static type-check evidence; pytest and Ruff evidence remain available.
- Resolution/Status: Open. Install the project `dev` extra in the verification environment before requiring mypy as a gate.
- LINKS: M-PERSIST-DTO, V-PERSIST-DTO, pyproject.toml

### F-0061 — grace module show does not resolve non-V-M verification IDs
- Date: 2026-07-11
- Area: tooling
- Finding: `grace module show M-PERSIST-DTO --with verification` reports `Verification: none` even though both plan and graph link the module to the existing `V-PERSIST-DTO` entry.
- Symptom/Reproduction: Run the command after Checkpoint 5.0A meta sync; XML parsing and direct reference checks pass, but the CLI omits the verification excerpt.
- Impact: CLI-generated execution packets cannot be trusted as the sole source for verification entries using the project's established `V-PERSIST-*` or `V-DOMAIN-*` naming.
- Resolution/Status: Open. Continue reading `docs/verification-plan.xml` directly or standardize IDs in a dedicated GRACE artifact migration.
- LINKS: M-PERSIST-DTO, V-PERSIST-DTO, docs/verification-plan.xml

### F-0062 — Canonical schema 2.0 was incompatible with legacy GUI projection writes
- Date: 2026-07-12
- Area: persistence, gui, mcp
- Finding: Phase 16 services correctly committed ProjectDocumentV2, but GUI refresh parsed canonical slides as legacy SlideSegment values without computed duration/null-image normalization, and GUI CRUD/save subsequently rewrote project.json through the legacy writer. Derived slides.json also used zero dimensions rejected by the legacy compatibility model.
- Symptom/Reproduction: MCP detect succeeded, then get_project reported detect_done=false; slide_add failed validation; project_save silently replaced schema_version/revision/pipeline with legacy version/state fields.
- Impact: MCP completion could desynchronize GUI state, slide CRUD could fail after detection, and save/open could lose optimistic revision and full pipeline state.
- Resolution/Status: Resolved. ProjectModel now projects schema 2.0 into the legacy Qt model for reads while routing canonical save and slide CRUD through FileProjectRepository. Compatibility slides use valid sentinel dimensions, nullable images are normalized, and real GUI+MCP detect/CRUD/save/open characterization passes while project.json remains schema 2.0.
- LINKS: M-PROJECT-MODEL, M-FILE-REPO, M-MCP-ADAPTER, V-REF-MCP-ADAPTER

### F-0063 — GUI pipeline stages execute synchronously on the Qt main thread
- Date: 2026-07-12
- Area: ui
- Finding: MainWindow calls PipelineController.run_* directly and PipelineController executes services synchronously without a QThread replacement.
- Symptom/Reproduction: A blocking fake detection service prevents a Qt timer from firing until run_detect returns.
- Impact: Detect, Auto, Notes, and Export freeze the GUI.
- Resolution/Status: Resolved in Step 8.5 with PipelineWorker and controller-owned QThread lifecycle; non-blocking regression test passes.
- LINKS: M-GUI-PIPELINE-CTRL, M-GUI-PIPELINE-WORKER, V-REF-GUI-ADAPTER

### F-0064 — Pipeline operation context is constructed but not consumed
- Date: 2026-07-12
- Area: ui
- Finding: PipelineController creates SignalProgressObserver and CancellationToken but dispatches through services built with ApplicationServices' original context.
- Symptom/Reproduction: Service progress is reported to the bootstrap context, while PipelineController.progress emits nothing.
- Impact: GUI progress and cancellation are disconnected from real service execution.
- Resolution/Status: Resolved. ApplicationServices.scoped builds services with the GUI ServiceContext; real ValidationService progress reaches PipelineController.progress.
- LINKS: M-GUI-PIPELINE-CTRL, M-APP-SERVICE-CONTEXT, V-REF-GUI-ADAPTER

### F-0065 — Project-open signal precedes legacy GUI projection synchronization
- Date: 2026-07-12
- Area: ui
- Finding: ProjectController emits projectOpened before MainWindow opens ProjectModel, while _on_project_opened reads ProjectModel.project_data.
- Symptom/Reproduction: create/open/recent-open signal handler sees stale or empty project data.
- Impact: Labels, timeline, actions, and recent-project state can remain stale.
- Resolution/Status: Resolved. ProjectController is canonical; MainWindow projects its loaded state before rendering, with a guarded one-way legacy MCP bridge.
- LINKS: M-GUI-PROJECT-CTRL, M-GUI-MAIN, V-REF-GUI-ADAPTER

### F-0066 — Timeline display indexes cross the SlideId application boundary
- Date: 2026-07-12
- Area: ui
- Finding: MainWindow forwards timeline indexes into TimelineController methods whose contracts require SlideId.
- Symptom/Reproduction: delete/move/resize/clear paths receive an integer instead of the displayed slide UID.
- Impact: Wrong slide mutation or domain lookup failure after reorder/delete.
- Resolution/Status: Resolved. MainWindow._slide_id resolves the display index and all TimelineController mutations receive SlideId.
- LINKS: M-GUI-TIMELINE-CTRL, M-GUI-MAIN, V-REF-GUI-ADAPTER

### F-0067 — Set-frame clears the canonical image reference after writing the file
- Date: 2026-07-12
- Area: ui
- Finding: MainWindow writes a frame with cv2.imwrite and then invokes clear_slide_image instead of a canonical set-image operation.
- Symptom/Reproduction: Screenshot exists on disk but reopened project has no matching ArtifactRef.
- Impact: Representative frame is lost from canonical project state.
- Resolution/Status: Resolved. Domain Project.set_image and TimelineController.set_slide_image persist an existing project-relative ArtifactRef and survive reopen.
- LINKS: M-GUI-TIMELINE-CTRL, M-DOMAIN-PROJECT, V-REF-GUI-ADAPTER

### F-0068 — GUI revision ownership is split across stale snapshots
- Date: 2026-07-12
- Area: ui
- Finding: ProjectController, ProjectModel, pipeline services, and TimelineController can independently load and save project revisions.
- Symptom/Reproduction: Pipeline or timeline save followed by ProjectController.save uses a stale expected revision.
- Impact: Valid GUI sequences can raise ProjectRevisionConflict or overwrite newer state.
- Resolution/Status: Resolved. Pipeline/timeline completion reloads ProjectController and projection; stale save reloads instead of surfacing ProjectRevisionConflict.
- LINKS: M-GUI-PROJECT-CTRL, M-GUI-PIPELINE-CTRL, M-GUI-TIMELINE-CTRL, V-REF-GUI-ADAPTER

### F-0069 — videoChanged assigns a Python attribute instead of Qt enabled state
- Date: 2026-07-12
- Area: ui
- Finding: MainWindow uses setattr(button, "enabled", value), which does not call QWidget.setEnabled.
- Symptom/Reproduction: videoChanged leaves Detect and Quick Preview disabled.
- Impact: Imported/opened video cannot reliably enable pipeline actions.
- Resolution/Status: Resolved. Dedicated videoChanged handler calls QWidget.setEnabled(bool); GUI regression test passes.
- LINKS: M-GUI-MAIN, V-REF-GUI-ADAPTER

### F-0070 — MainWindow Step 8 stop condition is unmet
- Date: 2026-07-12
- Area: ui
- Finding: Commit 88eaec4 leaves main_window.py above the approved 600-line stop condition.
- Symptom/Reproduction: Physical line count is 793 at the audited commit.
- Impact: Step 8 cannot be marked complete.
- Resolution/Status: Resolved. UI construction and MCP/debug hosting moved to main_window_ui.py; main_window.py is 596 physical lines.
- LINKS: M-GUI-MAIN, M-GUI-WINDOW-UI, V-REF-GUI-ADAPTER

### F-0071 — CI matrix omits the PySide6 dependency required during collection
- Date: 2026-07-12
- Area: tooling
- Finding: PR #1 standard CI test jobs run GUI-importing tests without installing PySide6.
- Symptom/Reproduction: GitHub run 29186796164 fails collection with ModuleNotFoundError: PySide6.
- Impact: Linux and Windows matrix, GUI test, and dependent acceptance jobs are red.
- Resolution/Status: CI_ENVIRONMENT fixed locally by installing the gui extra in every matrix job; GitHub acceptance pending.
- LINKS: M-CI, .github/workflows/ci.yml, V-REF-GUI-ADAPTER

### F-0072 — MCP workflows install obsolete Ubuntu Mesa package names
- Date: 2026-07-12
- Area: tooling
- Finding: MCP workflows request libegl1-mesa and libgl1-mesa-glx, unavailable on the current GitHub Ubuntu image.
- Symptom/Reproduction: Runs 29186795062 and 29186796133 fail apt with exit code 100 before tests.
- Impact: MCP E2E smoke is skipped and required unit-tests remain red.
- Resolution/Status: CI_ENVIRONMENT fixed locally by using libegl1/libgl1; GitHub acceptance pending.
- LINKS: M-CI, .github/workflows/mcp-e2e.yml, V-REF-GUI-ADAPTER

### F-0074 — GUI operation lifecycle: status destroyed by rejected second operation
- Date: 2026-07-12
- Area: ui
- Finding: MainWindow._run_pipeline starts StatusBarManager lifecycle before PipelineController accepts the operation.
  PipelineController._run checks busy state only after the caller has already overwritten the status bar.
  Consequence: clicking Quick Preview while Detect is running first erases Detect status, then shows
  "Pipeline failed: A pipeline operation is already running" — making it look like Detect failed.
- Symptom/Reproduction:
  1. Open project with video
  2. Click Detect
  3. Status shows "Detect... 0%"
  4. Immediately click Quick Preview
  5. Status shows "Preview... 0%" (overwrites Detect)
  6. Preview rejected: "Pipeline failed: A pipeline operation is already running"
  7. Status now shows "Pipeline failed" — active Detect status is destroyed
  8. Active Detect continues running but user has no visibility
- Impact: User incorrectly believes Detect failed. No cancel UI for the running operation.
  Conflicting buttons (Quick Preview, Detect, Auto) remain enabled during operation.
- Resolution/Status: Open for Step 9.5.
- LINKS: M-GUI-PIPELINE-CTRL, M-GUI-MAIN, M-GUI-STATUS

### F-0073 — E2E tooling package was absent from pytest import roots
- Date: 2026-07-12
- Area: tooling
- Finding: Real MCP characterization imported tools.mcp_e2e_runner while pytest configured only src as its Python path and tools lacked a package marker.
- Symptom/Reproduction: Direct characterization collection failed with ModuleNotFoundError: tools.
- Impact: The required 11-test GUI+MCP gate could not run from the documented pytest command.
- Resolution/Status: TEST_BUG resolved by adding the repository root to pytest pythonpath and tools/__init__.py.
- LINKS: V-REF-GUI-ADAPTER, pyproject.toml, tools/__init__.py
