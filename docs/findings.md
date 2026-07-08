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
