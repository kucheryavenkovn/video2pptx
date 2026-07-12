# FILE: src/video2pptx/project_model.py
# VERSION: 0.4.0
# START_MODULE_CONTRACT
#   PURPOSE: QObject-based project model — bridges CLI project manager with GUI signals
#   SCOPE: create/open/save/close lifecycle, canonical schema 2.0 projection persistence, slide CRUD, subtitle/marker management, score waveform
#   DEPENDS: PySide6.QtCore, video2pptx.project_manager, video2pptx.timeline_model, video2pptx.subtitles
#   LINKS: M-PROJECT-MODEL
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ProjectModel - QObject wrapping project state with Qt signals for GUI binding
#   ProjectModel._legacy_project_from_v2 - map canonical persistence to the legacy GUI model
#   ProjectModel._save_canonical_projection - persist GUI slide edits through FileProjectRepository
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v0.4.0 - Preserve canonical schema during GUI open, save, and slide CRUD
#   v0.3.0 - Refresh schema 2.0 persistence through a legacy GUI compatibility mapping
#   v0.2.0 - Persist UID-based slide CRUD consistently to project, slides document, and timeline
# END_CHANGE_SUMMARY

from __future__ import annotations

import json
from pathlib import Path

import pysubs2
from loguru import logger
from PySide6.QtCore import QObject, Signal

from video2pptx.models import SlidesDocument, SlideSegment
from video2pptx.project_manager import (
    Project,
    create_project,
    import_subtitles_to_project,
    import_video_to_project,
    load_slides_into_project,
    open_project,
    save_project,
    update_project_state,
)
from video2pptx.timeline_model import (
    MarkerClip,
    ScoreClip,
    SlideClip,
    SubtitleClip,
    Timeline,
)


class ProjectModel(QObject):
    """Qt model wrapping Project state with signal emission for all mutations."""

    slidesChanged = Signal()
    subtitlesChanged = Signal()
    markersChanged = Signal()
    scoresChanged = Signal()
    videoChanged = Signal(str)
    projectOpened = Signal()
    projectClosed = Signal()
    stateChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._project: Project | None = None
        self._subs: pysubs2.SSAFile | None = None
        self._timeline: Timeline = Timeline()
        self._score_timestamps: list[float] = []
        self._score_values: list[float] = []
        self._project_path: str | None = None

    @property
    def project_path(self) -> str | None:
        return self._project_path

    @property
    def timeline(self) -> Timeline:
        return self._timeline

    @property
    def slides(self) -> list[SlideClip]:
        track = self._timeline.track("slides")
        return [c for c in track.clips() if isinstance(c, SlideClip)] if track else []

    @property
    def subtitles(self) -> list[SubtitleClip]:
        track = self._timeline.track("subtitles")
        return [c for c in track.clips() if isinstance(c, SubtitleClip)] if track else []

    @property
    def markers(self) -> list[MarkerClip]:
        track = self._timeline.track("markers")
        return [c for c in track.clips() if isinstance(c, MarkerClip)] if track else []

    @property
    def output_dir(self) -> str:
        return str(self._project.output_dir) if self._project else ""

    @property
    def project_dir(self) -> str:
        return str(self._project.project_dir) if self._project else ""

    @property
    def is_open(self) -> bool:
        return self._project is not None

    @property
    def project_data(self) -> Project | None:
        return self._project

    @property
    def score_timestamps(self) -> list[float]:
        return list(self._score_timestamps)

    @property
    def score_values(self) -> list[float]:
        return list(self._score_values)

    def create(self, path: str, name: str = "Untitled") -> None:
        out_dir = Path(path) / name
        self._project = create_project(str(out_dir), name=name)
        self._project_path = str(out_dir)
        self._subs = None
        self._timeline.clear()
        self._sync_subtitles_to_timeline() if self._subs else None
        self.videoChanged.emit("")
        self.projectOpened.emit()

    def open(self, path: str) -> None:
        project_path = Path(path)
        raw = json.loads((project_path / "project.json").read_text(encoding="utf-8"))
        if str(raw.get("schema_version", "1.0")) == "2.0":
            self._project = self._legacy_project_from_v2(raw, project_path)
        else:
            self._project = open_project(path)
        self._project_path = path
        self._subs = self._load_subs_if_needed()
        self._timeline.clear()
        if self._project:
            self._timeline.duration = getattr(self._project, "video_duration", 0) or 0
            self._sync_project_to_ui()
            if self._project.video:
                self.videoChanged.emit(self._project.video)
        self.projectOpened.emit()
        logger.info(f"[ProjectModel][open] Opened | path={path} name={self._project.name if self._project else '?'}")

    def save(self) -> None:
        if not self._project or not self._project_path:
            return
        project_path = Path(self._project_path)
        if self._is_canonical_project(project_path):
            self._save_canonical_projection(project_path, slides_changed=False)
        else:
            save_project(self._project)

    def close(self) -> None:
        self._close_internal()
        self.projectClosed.emit()

    def refresh_from_disk(self) -> None:
        """Re-read legacy or canonical project data and refresh GUI state."""
        if not self._project or not self._project_path:
            return
        try:
            project_path = Path(self._project_path)
            raw = json.loads((project_path / "project.json").read_text(encoding="utf-8"))
            if str(raw.get("schema_version", "1.0")) == "2.0":
                self._project = self._legacy_project_from_v2(raw, project_path)
            else:
                self._project = open_project(project_path)
            self._subs = self._load_subs_if_needed()
            self._timeline.clear()
            self._timeline.duration = getattr(self._project, "video_duration", 0) or 0
            self._sync_project_to_ui()
            logger.info("[ProjectModel][refresh_from_disk] Refreshed from disk")
        except Exception as exc:
            logger.error(f"[ProjectModel][refresh_from_disk] Failed | error={exc}")

    @staticmethod
    def _legacy_project_from_v2(data: dict, project_path: Path) -> Project:
        """Map canonical schema 2.0 data to the legacy GUI Project model."""
        stages = data.get("pipeline", {}).get("stages", {})

        def has_status(stage: str, status: str) -> bool:
            return stages.get(stage, {}).get("status") == status

        slides = []
        for slide in data.get("slides", []):
            item = dict(slide)
            item["duration"] = float(item["end"]) - float(item["start"])
            item["image"] = item.get("image") or ""
            slides.append(item)

        scores = data.get("scores", {})
        return Project.model_validate(
            {
                "version": "2.0",
                "name": data.get("name", "Untitled"),
                "video": data.get("video_path", ""),
                "subtitles": data.get("subtitle_path"),
                "state": {
                    "preview_done": has_status("preview", "succeeded"),
                    "detect_done": has_status("detect", "succeeded"),
                    "align_done": has_status("align", "succeeded"),
                    "notes_done": has_status("notes", "succeeded"),
                    "llm_done": has_status("llm", "succeeded"),
                    "md_exported": has_status("markdown_export", "succeeded"),
                    "pptx_exported": has_status("pptx_export", "succeeded"),
                    "auto_done": has_status("auto", "succeeded"),
                    "detect_stale": has_status("detect", "stale"),
                    "align_stale": has_status("align", "stale"),
                    "notes_stale": has_status("notes", "stale"),
                    "md_stale": has_status("markdown_export", "stale"),
                    "pptx_stale": has_status("pptx_export", "stale"),
                },
                "slides_json": "slides.json",
                "slides": slides,
                "output_dir": str(project_path),
                "score_timestamps": scores.get("timestamps", []),
                "score_values": scores.get("values", []),
            }
        )

    def _sync_project_to_ui(self) -> None:
        """Sync current project state to timeline and emit signals."""
        if not self._project:
            return
        self._sync_slides_to_timeline()
        self._sync_subtitles_to_timeline()
        self._score_timestamps = list(self._project.score_timestamps)
        self._score_values = list(self._project.score_values)
        if self._score_timestamps and self._score_values:
            self._sync_scores_to_timeline()
            self.scoresChanged.emit()
        self.slidesChanged.emit()
        self.projectOpened.emit()

    def _close_internal(self) -> None:
        self._project = None
        self._subs = None
        self._timeline.clear()
        self._score_timestamps.clear()
        self._score_values.clear()
        self._project_path = None

    def add_slide(self, ts: float) -> str:
        if self._project:
            if ts < 0:
                raise ValueError("Slide timestamp must be non-negative")
            containing = next(
                (
                    slide
                    for slide in self._project.slides
                    if slide.start < ts < slide.end
                ),
                None,
            )
            if containing is not None:
                old_end = containing.end
                containing.end = ts
                containing.duration = containing.end - containing.start
                slide = SlideSegment(
                    index=len(self._project.slides) + 1,
                    start=ts,
                    end=old_end,
                    duration=old_end - ts,
                    representative_timestamp=(ts + old_end) / 2,
                    manual=True,
                )
            else:
                next_start = min(
                    (
                        item.start
                        for item in self._project.slides
                        if item.start > ts
                    ),
                    default=ts + 5.0,
                )
                if next_start <= ts:
                    raise ValueError("No interval available for manual slide")
                slide = SlideSegment(
                    index=len(self._project.slides) + 1,
                    start=ts,
                    end=next_start,
                    duration=next_start - ts,
                    representative_timestamp=(ts + next_start) / 2,
                    manual=True,
                )
                self._validate_slide_interval(slide.uid, slide.start, slide.end)
            self._project.slides.append(slide)
            self._commit_slide_changes()
            return slide.uid

        track = self._timeline.create_track("slides")
        slide = SlideClip(start_sec=ts, end_sec=ts + 5.0)
        slide.index = len(self.slides) + 1
        slide.manual = True
        track.add_clip(slide)
        self.slidesChanged.emit()
        if self._project:
            self._sync_slides_to_timeline()
        return slide.uid

    def delete_slide(self, uid_or_index: str | int) -> None:
        if self._project:
            slide = self._resolve_slide(uid_or_index)
            if slide is None:
                raise KeyError(f"Slide not found: {uid_or_index}")
            self._project.slides.remove(slide)
            self._commit_slide_changes()
            return

        track = self._timeline.track("slides")
        if track is None:
            return
        for c in track.clips():
            if isinstance(c, SlideClip) and c.index == uid_or_index:
                track.remove_clip(c.uid)
                track.reindex()
                self.slidesChanged.emit()
                if self._project:
                    self._sync_slides_to_timeline()
                return

    def delete_slide_by_uid(self, uid: str) -> None:
        if self._project:
            self.delete_slide(uid)
            return
        track = self._timeline.track("slides")
        if track is None:
            return
        for c in track.clips():
            if isinstance(c, SlideClip) and c.uid == uid:
                track.remove_clip(c.uid)
                track.reindex()
                self.slidesChanged.emit()
                if self._project:
                    self._sync_slides_to_timeline()
                return

    def move_slide(self, uid_or_index: str | int, start: float, end: float) -> None:
        if self._project:
            slide = self._resolve_slide(uid_or_index)
            if slide is None:
                raise KeyError(f"Slide not found: {uid_or_index}")
            self._validate_slide_interval(slide.uid, start, end)
            slide.start = start
            slide.end = end
            slide.duration = end - start
            if not start <= slide.representative_timestamp <= end:
                slide.representative_timestamp = (start + end) / 2
            self._commit_slide_changes()
            return

        track = self._timeline.track("slides")
        if track is None:
            return
        for c in track.clips():
            if isinstance(c, SlideClip) and c.index == uid_or_index:
                c.start_sec = start
                c.end_sec = end
                self.slidesChanged.emit()
                return

    def resize_slide(self, uid_or_index: str | int, end: float) -> None:
        slide = self._resolve_slide(uid_or_index) if self._project else None
        if slide is not None:
            self.move_slide(uid_or_index, slide.start, end)
            return
        raise KeyError(f"Slide not found: {uid_or_index}")

    def set_slide_frame(self, uid_or_index: str | int) -> None:
        if not self._project or not self._project.video:
            raise RuntimeError("Project video is required")
        slide = self._resolve_slide(uid_or_index)
        if slide is None:
            raise KeyError(f"Slide not found: {uid_or_index}")

        import cv2

        timestamp = slide.representative_timestamp or (
            slide.start + slide.end
        ) / 2
        capture = cv2.VideoCapture(self._project.video)
        try:
            capture.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
            ok, frame = capture.read()
        finally:
            capture.release()
        if not ok:
            raise RuntimeError(f"Could not decode frame at {timestamp:.3f}s")

        slides_dir = Path(self._project.output_dir) / "slides"
        slides_dir.mkdir(parents=True, exist_ok=True)
        image_path = slides_dir / f"slide_{slide.index:03d}.png"
        if not cv2.imwrite(str(image_path), frame):
            raise RuntimeError(f"Could not write slide image: {image_path}")
        slide.image = f"slides/{image_path.name}"
        slide.representative_timestamp = timestamp
        self._commit_slide_changes()

    def clear_slide_image(self, uid_or_index: str | int) -> None:
        if self._project:
            slide = self._resolve_slide(uid_or_index)
            if slide is None:
                raise KeyError(f"Slide not found: {uid_or_index}")
            slide.image = ""
            self._commit_slide_changes()
            return

        track = self._timeline.track("slides")
        if track is None:
            return
        for c in track.clips():
            if not isinstance(c, SlideClip):
                continue
            if (isinstance(uid_or_index, str) and c.uid == uid_or_index) or \
               (isinstance(uid_or_index, int) and c.index == uid_or_index):
                c.image_path = ""
                self.slidesChanged.emit()
                return

    def _resolve_slide(self, uid_or_index: str | int) -> SlideSegment | None:
        if not self._project:
            return None
        if isinstance(uid_or_index, str):
            return next(
                (
                    slide
                    for slide in self._project.slides
                    if slide.uid == uid_or_index
                ),
                None,
            )
        if 1 <= uid_or_index <= len(self._project.slides):
            return self._project.slides[uid_or_index - 1]
        return None

    def _validate_slide_interval(
        self,
        uid: str,
        start: float,
        end: float,
    ) -> None:
        if start < 0 or end <= start:
            raise ValueError("Slide interval must satisfy 0 <= start < end")
        if not self._project:
            return
        for slide in self._project.slides:
            if slide.uid == uid:
                continue
            if start < slide.end and slide.start < end:
                raise ValueError(f"Slide interval overlaps slide {slide.uid}")

    @staticmethod
    def _is_canonical_project(project_path: Path) -> bool:
        try:
            data = json.loads(
                (project_path / "project.json").read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return False
        return str(data.get("schema_version", "1.0")) == "2.0"

    def _save_canonical_projection(
        self,
        project_path: Path,
        *,
        slides_changed: bool,
    ) -> None:
        """Persist the GUI projection without downgrading canonical storage."""
        from video2pptx.domain.slide import Slide
        from video2pptx.infrastructure.persistence.file_project_repository import (
            FileProjectRepository,
        )

        repo = FileProjectRepository()
        loaded = repo.load(project_path)
        if slides_changed:
            slides = [
                Slide.from_dict(slide.model_dump(mode="json"))
                for slide in self._project.slides
            ]
            loaded.project.replace_detected_slides(slides)
            loaded.project.score_timestamps = list(self._project.score_timestamps)
            loaded.project.score_values = list(self._project.score_values)
        repo.save(
            loaded.project,
            loaded.location,
            expected_revision=loaded.revision,
        )

    def _commit_slide_changes(self) -> None:
        if not self._project:
            return
        self._project.slides.sort(key=lambda slide: (slide.start, slide.end))
        for index, slide in enumerate(self._project.slides, start=1):
            slide.index = index
            slide.duration = slide.end - slide.start
        self._project.state.mark_stale_downstream("detect")

        project_path = Path(self._project_path) if self._project_path else None
        if project_path and self._is_canonical_project(project_path):
            self._save_canonical_projection(project_path, slides_changed=True)
        else:
            if self._project.slides_json:
                slides_path = (
                    Path(self._project.output_dir) / self._project.slides_json
                )
                if slides_path.is_file():
                    from video2pptx.utils.json_io import write_json_atomic

                    document = SlidesDocument.model_validate_json(
                        slides_path.read_text(encoding="utf-8")
                    )
                    document.slides = list(self._project.slides)
                    write_json_atomic(
                        slides_path,
                        document.model_dump(mode="json"),
                        indent=2,
                    )
            save_project(self._project)
        self._sync_slides_to_timeline()

    def load_subtitles(self, path: str) -> None:
        if not self._project:
            return
        import_subtitles_to_project(self._project, path)
        self._subs = self._load_subs_if_needed()
        self._sync_subtitles_to_timeline()
        self.subtitlesChanged.emit()

    def _sync_subtitles_to_timeline(self) -> None:
        track = self._timeline.create_track("subtitles")
        for c in list(track.clips()):
            track.remove_clip(c.uid)
        if self._subs is None:
            return
        for ev in self._subs.events:
            start = ev.start / 1000.0
            end = ev.end / 1000.0
            text = ev.plaintext.strip()
            if text:
                clip = SubtitleClip(start_sec=start, end_sec=end, plaintext=text)
                track.add_clip(clip)
        self.subtitlesChanged.emit()

    def clear_subtitles(self) -> None:
        self._subs = None
        self._timeline.remove_track("subtitles")
        self.subtitlesChanged.emit()

    def _load_subs_if_needed(self) -> pysubs2.SSAFile | None:
        if not self._project or not self._project.subtitles:
            return None
        try:
            return pysubs2.load(self._project.subtitles, encoding="utf-8")
        except Exception:
            return None

    def import_video(self, path: str) -> None:
        if not self._project:
            return
        import_video_to_project(self._project, path)
        self.videoChanged.emit(path)

    def add_marker(self, ts: float) -> None:
        track = self._timeline.create_track("markers")
        marker = MarkerClip(start_sec=ts, snapped_ts=ts, snap_mode="manual")
        track.add_clip(marker)
        self.markersChanged.emit()

    def delete_marker(self, ts: float) -> None:
        track = self._timeline.track("markers")
        if track is None:
            return
        for c in track.clips():
            if isinstance(c, MarkerClip) and abs(c.start_sec - ts) < 0.01:
                track.remove_clip(c.uid)
                self.markersChanged.emit()
                return

    def load_slides_from_json(self, path: str) -> None:
        if not self._project:
            return
        update_project_state(self._project, detect_done=True, slides_json=path)
        load_slides_into_project(self._project, force=True)
        self._sync_slides_to_timeline()
        self.slidesChanged.emit()

    def _sync_slides_to_timeline(self) -> None:
        track = self._timeline.create_track("slides")
        for c in list(track.clips()):
            track.remove_clip(c.uid)
        if not self._project or not self._project.slides:
            return
        for seg in self._project.slides:
            clip = SlideClip.from_segment(seg)
            clip.image_path = str(Path(self._project.output_dir) / seg.image) if seg.image else ""
            track.add_clip(clip)
        track.reindex()
        self.slidesChanged.emit()

    def _sync_scores_to_timeline(self) -> None:
        track = self._timeline.create_track("scores")
        for c in list(track.clips()):
            track.remove_clip(c.uid)
        for ts, val in zip(self._score_timestamps, self._score_values):
            clip = ScoreClip(start_sec=ts, value=val, method="quick")
            track.add_clip(clip)

    def set_scores(self, timestamps: list[float], values: list[float]) -> None:
        self._score_timestamps = list(timestamps)
        self._score_values = list(values)
        self._sync_scores_to_timeline()
        self.scoresChanged.emit()

    def clear_scores(self) -> None:
        self._score_timestamps.clear()
        self._score_values.clear()
        self._timeline.remove_track("scores")
        self.scoresChanged.emit()

    def update_state(self, **kwargs: bool) -> None:
        if self._project:
            update_project_state(self._project, **kwargs)
        self.stateChanged.emit()
