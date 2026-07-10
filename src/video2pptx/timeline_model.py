# FILE: src/video2pptx/timeline_model.py
# VERSION: 0.2.0
# START_MODULE_CONTRACT
#   PURPOSE: QObject-based timeline model — Clip hierarchy, Track, Timeline container
#   SCOPE: Clip (base), SlideClip, SubtitleClip, MarkerClip, ScoreClip, Track(QObject), ScoreTrack, Timeline(QObject)
#   DEPENDS: abc, uuid, PySide6.QtCore, video2pptx.models
#   LINKS: M-TIMELINE-MODEL
#   ROLE: DATA_LAYER
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   Clip - Base class for timeline elements with time bounds
#   SlideClip - Slide segment clip
#   SubtitleClip - Subtitle cue clip
#   MarkerClip - User marker clip
#   ScoreClip - Score/similarity clip
#   Track - Named container for clips with signals
#   ScoreTrack - Track with score range + waveform
#   Timeline - Root container: multiple tracks with duration
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v0.2.0 - Preserve SlideSegment UID across timeline conversions
# END_CHANGE_SUMMARY

from __future__ import annotations

import uuid
from abc import ABC

from PySide6.QtCore import QObject, Signal

from video2pptx.models import SlideSegment


class Clip(ABC):
    """Base class for any timeline element with time bounds."""

    def __init__(self, start_sec: float = 0.0, end_sec: float = 0.0) -> None:
        self.uid: str = uuid.uuid4().hex[:8]
        self.start_sec: float = start_sec
        self.end_sec: float = end_sec

    @property
    def duration(self) -> float:
        return max(0.0, self.end_sec - self.start_sec)

    def contains(self, t: float) -> bool:
        return self.start_sec <= t <= self.end_sec

    def overlaps(self, other: Clip) -> bool:
        return self.start_sec < other.end_sec and other.start_sec < self.end_sec


class SlideClip(Clip):
    """Slide segment with transcript, notes, image, and LLM metadata."""

    def __init__(self, start_sec: float = 0.0, end_sec: float = 0.0) -> None:
        super().__init__(start_sec, end_sec)
        self.index: int = 0
        self.image_path: str = ""
        self.transcript: str = ""
        self.raw_cues: list[str] = []
        self.notes: str = ""
        self.llm_description: str = ""
        self.manual: bool = False
        self.representative_timestamp: float = 0.0

    def to_segment(self) -> SlideSegment:
        return SlideSegment(
            uid=self.uid,
            index=self.index,
            start=self.start_sec,
            end=self.end_sec,
            duration=self.duration,
            representative_timestamp=self.representative_timestamp,
            image=f"slides/slide_{self.index:03d}.png" if self.image_path else "",
            transcript=self.transcript,
            llm_description=self.llm_description,
            manual=self.manual,
        )

    @classmethod
    def from_segment(cls, seg: SlideSegment) -> SlideClip:
        clip = cls(start_sec=seg.start, end_sec=seg.end)
        clip.uid = seg.uid
        clip.index = seg.index
        clip.image_path = seg.image or ""
        clip.transcript = seg.transcript or ""
        clip.notes = getattr(seg, "notes", "") or ""
        clip.llm_description = seg.llm_description or ""
        clip.manual = seg.manual or False
        return clip

    def extract_subtitles(self, subtitles: list[SubtitleClip]) -> None:
        self.raw_cues = [s.plaintext for s in subtitles if self.contains(s.start_sec)]

    def process_notes(self, mode: str = "basic") -> None:
        from video2pptx.notes_processor import process_notes
        seg = self.to_segment()
        processed = process_notes(seg, mode=mode)
        self.notes = processed or self._basic_cleanup()

    @staticmethod
    def _basic_cleanup(transcript: str = "") -> str:
        if not transcript:
            return ""
        lines = transcript.replace("\n", "\n").split("\n")
        cleaned = " ".join(l.strip() for l in lines if l.strip())
        return cleaned


class SubtitleClip(Clip):
    """Subtitle cue clip with plaintext."""

    def __init__(self, start_sec: float = 0.0, end_sec: float = 0.0, plaintext: str = "") -> None:
        super().__init__(start_sec, end_sec)
        self.plaintext: str = plaintext


class MarkerClip(Clip):
    """User-created marker with snap info."""

    def __init__(self, start_sec: float = 0.0, snapped_ts: float = 0.0, snap_mode: str = "") -> None:
        super().__init__(start_sec, start_sec)
        self.snapped_ts: float = snapped_ts
        self.snap_mode: str = snap_mode


class ScoreClip(Clip):
    """Score/confidence data point."""

    def __init__(self, start_sec: float = 0.0, value: float = 0.0, method: str = "") -> None:
        super().__init__(start_sec, start_sec)
        self.value: float = value
        self.method: str = method


class Track(QObject):
    """Named container for clips with signal emission on changes."""

    clipAdded = Signal(str)     # clip uid
    clipRemoved = Signal(str)   # clip uid
    clipChanged = Signal(str)   # clip uid

    def __init__(self, name: str = "", height: int = 40) -> None:
        super().__init__()
        self._name: str = name
        self._height: int = height
        self._clips: list[Clip] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def height(self) -> int:
        return self._height

    @height.setter
    def height(self, value: int) -> None:
        self._height = max(20, value)

    def clips(self) -> list[Clip]:
        return list(self._clips)

    def add_clip(self, clip: Clip) -> None:
        self._clips.append(clip)
        self.clipAdded.emit(clip.uid)

    def remove_clip(self, uid: str) -> None:
        self._clips = [c for c in self._clips if c.uid != uid]
        self.clipRemoved.emit(uid)

    def sort(self) -> None:
        self._clips.sort(key=lambda c: c.start_sec)

    def reindex(self) -> None:
        idx = 1
        for c in self._clips:
            if isinstance(c, SlideClip):
                c.index = idx
                idx += 1


class ScoreTrack(Track):
    """Track for score data with value range and waveform path."""

    def __init__(self, name: str = "scores", height: int = 60) -> None:
        super().__init__(name, height)
        self.min_value: float = 0.0
        self.max_value: float = 1.0
        self.method: str = ""
        self._waveform_path: str = ""

    def build_waveform_path(self, width: int) -> str:
        if not self._clips:
            return ""
        clips = [c for c in self._clips if isinstance(c, ScoreClip)]
        if not clips:
            return ""
        xs = [c.start_sec for c in clips]
        ys = [c.value for c in clips]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        if max_x == min_x:
            return ""
        if max_y == min_y:
            max_y = min_y + 0.01
        self.min_value = min_y
        self.max_value = max_y
        h = self._height
        path_parts = []
        for c in clips:
            px = int((c.start_sec - min_x) / (max_x - min_x) * width)
            py = int(h - (c.value - min_y) / (max_y - min_y) * h)
            path_parts.append(f"{'M' if not path_parts else 'L'}{px},{py}")
        return " ".join(path_parts)


_TRACK_CONFIG = {
    "slides": {"cls": SlideClip, "height": 40, "label": "Slides"},
    "subtitles": {"cls": SubtitleClip, "height": 30, "label": "Subtitles"},
    "markers": {"cls": MarkerClip, "height": 30, "label": "Markers"},
    "scores": {"cls": ScoreClip, "height": 60, "label": "Scores"},
}


class Timeline(QObject):
    """Root container holding multiple named tracks."""

    trackAdded = Signal(str)
    trackRemoved = Signal(str)
    durationChanged = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self._tracks: dict[str, Track] = {}
        self._duration: float = 0.0
        self.px_per_sec: float = 50.0

    @property
    def duration(self) -> float:
        return self._duration

    @duration.setter
    def duration(self, value: float) -> None:
        if value != self._duration:
            self._duration = value
            self.durationChanged.emit(value)

    def create_track(self, name: str) -> Track:
        if name in self._tracks:
            return self._tracks[name]
        cfg = _TRACK_CONFIG.get(name, {})
        if name == "scores":
            track = ScoreTrack(name=name, height=cfg.get("height", 40))
        else:
            track = Track(name=name, height=cfg.get("height", 40))
        self._tracks[name] = track
        self.trackAdded.emit(name)
        return track

    def remove_track(self, name: str) -> None:
        if name in self._tracks:
            del self._tracks[name]
            self.trackRemoved.emit(name)

    def track(self, name: str) -> Track | None:
        return self._tracks.get(name)

    def track_names(self) -> list[str]:
        return list(self._tracks.keys())

    def clear(self) -> None:
        self._tracks.clear()
        self._duration = 0.0

    def all_clips(self) -> dict[str, list[Clip]]:
        return {name: track.clips() for name, track in self._tracks.items()}

    def clips_in_range(self, start: float, end: float) -> dict[str, list[Clip]]:
        result: dict[str, list[Clip]] = {}
        for name, track in self._tracks.items():
            result[name] = [c for c in track.clips() if c.overlaps(Clip(start, end))]
        return result
