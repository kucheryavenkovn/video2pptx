# FILE: src/video2pptx/project_model.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: QObject-based project model — bridges CLI project manager with GUI signals
#   SCOPE: create/open/save/close lifecycle, slide CRUD, subtitle/marker management, score waveform
#   DEPENDS: PySide6.QtCore, video2pptx.project_manager, video2pptx.timeline_model, video2pptx.subtitles
#   LINKS: M-PROJECT-MODEL
#   ROLE: DATA_LAYER
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ProjectModel - QObject wrapping project state with Qt signals for GUI binding
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

import pysubs2
from loguru import logger
from PySide6.QtCore import QObject, Signal

from video2pptx.project_manager import (
    Project,
    create_project,
    open_project,
    save_project,
    import_video_to_project,
    import_subtitles_to_project,
    load_slides_into_project,
    update_project_state,
)
from video2pptx.timeline_model import (
    Clip,
    MarkerClip,
    ScoreClip,
    ScoreTrack,
    SlideClip,
    SubtitleClip,
    Timeline,
    Track,
)


class ProjectModel(QObject):
    """Qt model wrapping Project state with signal emission for all mutations."""

    slidesChanged = Signal()
    subtitlesChanged = Signal()
    markersChanged = Signal()
    scoresChanged = Signal()
    videoChanged = Signal(str)
    projectClosed = Signal()
    stateChanged = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._project: Project | None = None
        self._subs: pysubs2.SSAFile | None = None
        self._timeline: Timeline = Timeline()
        self._score_timestamps: list[float] = []
        self._score_values: list[float] = []

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
        self._project = create_project(str(out_dir), name)
        self._subs = None
        self._timeline.clear()
        self._sync_subtitles_to_timeline() if self._subs else None
        self.videoChanged.emit("")

    def open(self, path: str) -> None:
        self._project = open_project(path)
        self._subs = self._load_subs_if_needed()
        self._timeline.clear()
        if self._project:
            dur = getattr(self._project, "video_duration", 0) or 0
            self._timeline.duration = dur
            load_slides_into_project(self._project)
            self._sync_slides_to_timeline()
            self._sync_subtitles_to_timeline()
            if self._project.video:
                self.videoChanged.emit(self._project.video)
        logger.info(f"[ProjectModel][open] Opened | path={path} name={self._project.name if self._project else '?'}")

    def save(self) -> None:
        if self._project:
            save_project(self._project)

    def close(self) -> None:
        self._close_internal()
        self.projectClosed.emit()

    def _close_internal(self) -> None:
        self._project = None
        self._subs = None
        self._timeline.clear()
        self._score_timestamps.clear()
        self._score_values.clear()

    def add_slide(self, ts: float) -> None:
        track = self._timeline.create_track("slides")
        slide = SlideClip(start_sec=ts, end_sec=ts + 5.0)
        slide.index = len(self.slides) + 1
        slide.manual = True
        track.add_clip(slide)
        self.slidesChanged.emit()
        if self._project:
            self._sync_slides_to_timeline()

    def delete_slide(self, index: int) -> None:
        track = self._timeline.track("slides")
        if track is None:
            return
        for c in track.clips():
            if isinstance(c, SlideClip) and c.index == index:
                track.remove_clip(c.uid)
                track.reindex()
                self.slidesChanged.emit()
                if self._project:
                    self._sync_slides_to_timeline()
                return

    def move_slide(self, index: int, start: float, end: float) -> None:
        track = self._timeline.track("slides")
        if track is None:
            return
        for c in track.clips():
            if isinstance(c, SlideClip) and c.index == index:
                c.start_sec = start
                c.end_sec = end
                self.slidesChanged.emit()
                return

    def resize_slide(self, index: int, start: float, end: float) -> None:
        self.move_slide(index, start, end)

    def set_slide_frame(self, index: int) -> None:
        pass  # Frame capture is done at GUI level via cv2

    def clear_slide_image(self, index: int) -> None:
        track = self._timeline.track("slides")
        if track is None:
            return
        for c in track.clips():
            if isinstance(c, SlideClip) and c.index == index:
                c.image_path = ""
                self.slidesChanged.emit()
                return

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
