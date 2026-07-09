"""
Decompile Python 3.14 .pyc files by reconstructing source from bytecode.
"""
import dis
import marshal
import struct
import sys
import types
from pathlib import Path

def read_pyc(path):
    with open(path, 'rb') as f:
        magic = f.read(4)
        flags = f.read(4)
        timestamp = struct.unpack('I', f.read(4))[0]
        size = struct.unpack('I', f.read(4))[0]
        code = marshal.load(f)
    return code


def decompile(code, indent=0):
    """Decompile a code object to Python source text."""
    prefix = '    ' * indent
    lines = []
    
    if indent == 0:
        lines.extend(decompile_module(code))
        return '\n'.join(lines), code.co_consts
    
    # For nested code objects (functions/classes)
    if code.co_name == '<module>':
        lines.extend(decompile_module(code))
    elif code.co_name.startswith('<lambda>'):
        lines.extend(decompile_lambda(code, prefix))
    else:
        lines.extend(decompile_function_or_class(code, prefix))
    
    return '\n'.join(lines), code.co_consts


def decompile_module(code):
    """Decompile a module-level code object."""
    lines = []
    
    # Track what classes/functions were defined
    defined_names = {}
    
    # Analyze all instruction blocks
    for block in split_basic_blocks(code):
        lines.extend(decompile_basic_block(block, ''))
    
    return lines


def split_basic_blocks(code):
    """Split bytecode into logical basic blocks."""
    instructions = list(dis.get_instructions(code))
    blocks = []
    current = []
    
    for i, instr in enumerate(instructions):
        current.append(instr)
        # Split on RETURN_VALUE, STORE_NAME, or before LOAD_BUILD_CLASS
        if instr.opname in ('RETURN_VALUE', 'POP_TOP'):
            # Check if next is a significant boundary
            if i + 1 < len(instructions):
                next_instr = instructions[i + 1]
                if next_instr.opname in ('LOAD_BUILD_CLASS', 'LOAD_CONST'):
                    blocks.append(current)
                    current = []
    
    if current:
        blocks.append(current)
    
    return blocks


def decompile_basic_block(instructions, prefix):
    """Decompile a block of instructions."""
    lines = []
    i = 0
    
    while i < len(instructions):
        instr = instructions[i]
        
        if instr.opname == 'RESUME':
            i += 1
            continue
        
        elif instr.opname == 'LOAD_SMALL_INT':
            # Start of IMPORT_FROM chain
            import_block = []
            j = i
            while j < len(instructions):
                ij = instructions[j]
                if ij.opname == 'LOAD_CONST':
                    # Check if next is IMPORT_NAME
                    if j + 1 < len(instructions) and instructions[j+1].opname == 'IMPORT_NAME':
                        pass
                    else:
                        break
                import_block.append(ij)
                if ij.opname == 'POP_TOP':
                    break
                j += 1
            
            result = decompile_import_block(import_block)
            if result:
                lines.append(prefix + result)
            i = j + 1
        
        elif instr.opname == 'LOAD_BUILD_CLASS':
            # Class definition: LOAD_BUILD_CLASS, PUSH_NULL, LOAD_CONST(<code>), MAKE_FUNCTION, LOAD_CONST(<name>), LOAD_NAME(<base>)*, CALL(N)
            cls_block = []
            j = i
            depth = 0
            name_const = None
            code_const = None
            bases = []
            
            # Capture the class building sequence
            while j < len(instructions):
                ij = instructions[j]
                cls_block.append(ij)
                
                if ij.opname == 'PUSH_NULL':
                    pass
                elif ij.opname == 'LOAD_CONST':
                    const = get_const(ij, instructions)
                    if isinstance(const, types.CodeType):
                        code_const = const
                    elif isinstance(const, str) and name_const is None:
                        name_const = const
                    # Could be a base class name too
                elif ij.opname == 'LOAD_NAME':
                    bases.append(get_const(ij, instructions))
                elif ij.opname == 'CALL':
                    # CALL with n args: the first is the class body func, rest are bases
                    # n includes self and bases, so total = 1 + len(bases) + 1(self)
                    break
                elif ij.opname == 'STORE_NAME':
                    pass  # Will be handled
                    break
                
                j += 1
            
            if code_const and name_const:
                class_src = decompile_class(code_const, name_const, bases, prefix)
                lines.append(class_src)
            
            i = j + 1
        
        elif instr.opname == 'STORE_NAME':
            i += 1
            continue
        
        elif instr.opname == 'LOAD_CONST' and instr.arg is not None:
            const = get_const(instr, instructions)
            if const is None:
                i += 1
                continue
            i += 1
            continue
        
        elif instr.opname == 'RETURN_VALUE':
            break
        
        else:
            i += 1
    
    return lines


def get_const(instr, instructions):
    """Get the constant value for an instruction."""
    # We need access to the original consts tuple
    # This is handled differently - we'll pass code object around
    return instr.arg  # Will be resolved later


def decompile_import_block(instructions):
    """Decompile an import block."""
    import_lines = []
    i = 0
    current_from = None
    current_names = []
    
    while i < len(instructions):
        instr = instructions[i]
        
        if instr.opname == 'LOAD_SMALL_INT':
            pass  # from __future__ marker
        elif instr.opname == 'LOAD_CONST':
            pass  # Import specifiers
        elif instr.opname == 'IMPORT_NAME':
            pass  # Module name
        elif instr.opname == 'IMPORT_FROM':
            pass  # Specific import
        elif instr.opname == 'STORE_NAME':
            pass  # Local name
        elif instr.opname == 'POP_TOP':
            break
        
        i += 1
    
    return None  # Simplified - will handle differently


def decompile_class(code, name, bases, prefix):
    """Decompile a class code object."""
    lines = []
    class_prefix = prefix + '    '
    
    # Extract class-level assignments (__doc__, attributes, etc.)
    body_instructions = list(dis.get_instructions(code))
    
    # Check for class docstring
    docstring = None
    for const in code.co_consts:
        if isinstance(const, str) and const not in ('', ):
            if 'Base class' in const or 'A ' in const[:30] or 'Track' in const:
                docstring = const
                break
    
    # Get base classes from CALL instruction context
    base_str = ''
    if bases:
        base_str = '(' + ', '.join(bases) + ')'
    
    if name == 'Clip':
        base_str = '(ABC)'
    elif name in ('Track', 'Timeline'):
        base_str = '(QObject)'
    elif name == 'ScoreTrack':
        base_str = '(Track)'
    elif name == 'SlideClip':
        base_str = '(Clip)'
    elif name in ('SubtitleClip', 'MarkerClip', 'ScoreClip'):
        base_str = '(Clip)'
    
    lines.append(f'\n{prefix}class {name}{base_str}:')
    if docstring:
        lines.append(f'{prefix}    """{docstring}"""')
    
    # Decompile methods
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            if const.co_name == '<lambda>':
                continue
            method_lines = decompile_method(const, class_prefix, code)
            lines.extend(method_lines)
    
    return '\n'.join(lines)


def decompile_method(code, prefix, class_code=None):
    """Decompile a method/function."""
    lines = []
    name = code.co_name
    
    if name == '__annotate__':
        return []
    
    # Skip __firstlineno__, __static_attributes__ assignments
    if name in ('__firstlineno__', '__static_attributes__'):
        return []
    
    # Get annotations info
    is_property = False
    is_static = False
    is_classmethod = False
    is_abstract = False
    
    # Check for @property, @staticmethod etc by looking at class_CODE consts
    if class_code:
        body_instructions = list(dis.get_instructions(class_code))
        for i, instr in enumerate(body_instructions):
            if instr.opname == 'LOAD_NAME' and instr.arg is not None:
                pass  # We'll need consts for this
    
    # Build signature
    args = list(code.co_varnames[:code.co_argcount])
    if name == '__init__':
        signature = f'def {name}(self'
        if len(args) > 1:
            # Skip self
            for a in args[1:]:
                signature += f', {a}'
        signature += ') -> None:'
    else:
        signature = f'def {name}(self' if args and args[0] == 'self' else f'def {name}('
        for a in (args[1:] if args and args[0] == 'self' else args):
            signature += f', {a}'
        signature += '):'
    
    lines.append(f'{prefix}{signature}')
    
    # Get docstring
    docstring = None
    for const in code.co_consts:
        if isinstance(const, str) and const not in ('', 'Clip', 'SlideClip', 'SubtitleClip', 'MarkerClip', 'ScoreClip', 'Track', 'ScoreTrack', 'Timeline'):
            if len(const) > 10 and const[0].isupper():
                docstring = const
                break
    
    if docstring and docstring not in ('__init__', '__name__', '__qualname__'):
        lines.append(f'{prefix}    """{docstring}"""')
    
    # Generate pass for now - we'll fill in method bodies later
    lines.append(f'{prefix}    ...')
    
    return lines


# ================ Manual reconstruction based on bytecode analysis ================

def reconstruct_timeline_model():
    """Reconstruct timeline_model.py from bytecode analysis."""
    return '''# FILE: src/video2pptx/timeline_model.py
# VERSION: 0.1.0
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

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger
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

    def to_segment(self) -> SlideSegment:
        return SlideSegment(
            index=self.index,
            start=self.start_sec,
            end=self.end_sec,
            duration=self.duration,
            image=f"slides/slide_{self.index:03d}.png" if self.image_path else "",
            transcript=self.transcript,
            llm_description=self.llm_description,
            manual=self.manual,
        )

    @classmethod
    def from_segment(cls, seg: SlideSegment) -> SlideClip:
        clip = cls(start_sec=seg.start, end_sec=seg.end)
        clip.index = seg.index
        clip.image_path = seg.image or ""
        clip.transcript = seg.transcript or ""
        clip.notes = seg.notes or ""
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
        lines = transcript.replace("\\n", "\\n").split("\\n")
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
'''


def reconstruct_project_model():
    """Reconstruct project_model.py from bytecode analysis."""
    return '''# FILE: src/video2pptx/project_model.py
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
            self._timeline.duration = self._project.video_duration or 0.0
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
'''


def reconstruct_log_bridge():
    """Reconstruct log_bridge.py from bytecode analysis."""
    return '''# FILE: src/video2pptx/gui/log_bridge.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Loguru sink that captures log entries + emits Qt signal for live MCP log streaming
#   SCOPE: Singleton LogBridge with newLog Signal(Qt), recent(n) method, auto-installed Loguru sink
#   DEPENDS: PySide6.QtCore, loguru
#   LINKS: M-GUI-LOG-BRIDGE
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   LogBridge - Singleton capturing Loguru entries as structured dicts with Qt signal
# END_MODULE_MAP

from __future__ import annotations

from datetime import datetime
from typing import Any

from loguru import logger
from PySide6.QtCore import QObject, Signal


class LogBridge(QObject):
    """Singleton capturing Loguru entries for MCP live streaming."""

    newLog = Signal(str, str, str)  # level, time, message

    _instance: LogBridge | None = None

    def __init__(self) -> None:
        super().__init__()
        self._entries: list[dict[str, Any]] = []
        self._max_entries: int = 500
        self._sink_id: int | None = None
        self._install_sink()

    def _sink(self, message: Any) -> None:
        record = message.record
        entry = {
            "level": record["level"].name,
            "time": record["time"].strftime("%H:%M:%S.%f")[:-3],
            "message": record["message"],
            "file": record["file"].name if record.get("file") else "",
            "line": record["line"],
            "function": record["function"],
        }
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]
        self.newLog.emit(entry["level"], entry["time"], entry["message"])

    def recent(self, n: int = 50) -> list[dict[str, Any]]:
        return self._entries[-n:]

    def close(self) -> None:
        if self._sink_id is not None:
            try:
                logger.remove(self._sink_id)
            except ValueError:
                pass
            self._sink_id = None

    @classmethod
    def instance(cls) -> LogBridge:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _install_sink(self) -> None:
        self._sink_id = logger.add(
            self._sink,
            level="DEBUG",
            format="{message}",
            catch=True,
        )
'''


def main():
    pyc_dir = Path(__file__).parent.parent.parent
    
    files = {
        'src/video2pptx/timeline_model.py': reconstruct_timeline_model,
        'src/video2pptx/project_model.py': reconstruct_project_model,
        'src/video2pptx/gui/log_bridge.py': reconstruct_log_bridge,
    }
    
    for path, reconstruct_fn in files.items():
        full_path = pyc_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        content = reconstruct_fn()
        full_path.write_text(content, encoding='utf-8')
        print(f'Written: {full_path} ({len(content)} chars)')
    
    # Also restore test files
    tests = {
        'tests/test_timeline_model.py': '''# FILE: tests/test_timeline_model.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit tests for timeline_model classes
#   SCOPE: Clip hierarchy, Track operations, Timeline container
#   DEPENDS: video2pptx.timeline_model, pytest
#   LINKS: V-M-TIMELINE-MODEL
# END_MODULE_CONTRACT

from __future__ import annotations

import pytest
from video2pptx.timeline_model import (
    Clip, SlideClip, SubtitleClip, MarkerClip, ScoreClip,
    Track, ScoreTrack, Timeline,
)


class TestClip:
    def test_uid_generated(self) -> None:
        c = Clip(0, 10)
        assert c.uid
        assert len(c.uid) == 8

    def test_duration(self) -> None:
        c = Clip(5, 15)
        assert c.duration == 10

    def test_contains(self) -> None:
        c = Clip(10, 20)
        assert c.contains(10)
        assert c.contains(15)
        assert c.contains(20)
        assert not c.contains(5)

    def test_overlaps(self) -> None:
        a = Clip(0, 10)
        b = Clip(5, 15)
        c = Clip(15, 20)
        assert a.overlaps(b)
        assert b.overlaps(a)
        assert not a.overlaps(c)


class TestSlideClip:
    def test_to_from_segment(self) -> None:
        from video2pptx.models import SlideSegment
        seg = SlideSegment(index=1, start=10.0, end=30.0, transcript="Hello")
        clip = SlideClip.from_segment(seg)
        assert clip.index == 1
        assert clip.start_sec == 10.0
        assert clip.transcript == "Hello"
        back = clip.to_segment()
        assert back.index == 1
        assert back.start == 10.0


class TestTrack:
    def test_add_remove_clip(self, qtbot) -> None:
        track = Track("test")
        clip = SlideClip(0, 5)
        track.add_clip(clip)
        assert len(track.clips()) == 1
        assert track.name == "test"
        track.remove_clip(clip.uid)
        assert len(track.clips()) == 0

    def test_sort(self) -> None:
        track = Track("test")
        track.add_clip(SlideClip(10, 15))
        track.add_clip(SlideClip(0, 5))
        track.sort()
        assert track.clips()[0].start_sec == 0


class TestTimeline:
    def test_create_track(self) -> None:
        tl = Timeline()
        track = tl.create_track("slides")
        assert tl.track("slides") is track
        assert "slides" in tl.track_names()

    def test_duration_signal(self, qtbot) -> None:
        tl = Timeline()
        with qtbot.waitSignal(tl.durationChanged, timeout=1000):
            tl.duration = 120.0
        assert tl.duration == 120.0
''',
        'tests/test_project_model.py': '''# FILE: tests/test_project_model.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit tests for ProjectModel
#   SCOPE: Lifecycle, slide CRUD, timeline sync, signal emission
#   DEPENDS: video2pptx.project_model, video2pptx.timeline_model, pytest
#   LINKS: V-M-PROJECT-MODEL
# END_MODULE_CONTRACT

from __future__ import annotations

import pytest
from video2pptx.project_model import ProjectModel
from video2pptx.timeline_model import SlideClip, Timeline


class TestProjectModel:
    def test_initial_state(self) -> None:
        model = ProjectModel()
        assert not model.is_open
        assert model.timeline is not None
        assert isinstance(model.timeline, Timeline)

    def test_add_slide(self) -> None:
        model = ProjectModel()
        model.add_slide(10.0)
        slides = model.slides
        assert len(slides) == 1
        assert slides[0].start_sec == 10.0
        assert slides[0].manual is True

    def test_delete_slide(self) -> None:
        model = ProjectModel()
        model.add_slide(0.0)
        model.add_slide(10.0)
        assert len(model.slides) == 2
        model.delete_slide(1)
        assert len(model.slides) == 1
        assert model.slides[0].index == 1

    def test_move_slide(self) -> None:
        model = ProjectModel()
        model.add_slide(0.0)
        model.move_slide(1, 5.0, 15.0)
        assert model.slides[0].start_sec == 5.0
        assert model.slides[0].end_sec == 15.0

    def test_close_clears_all(self) -> None:
        model = ProjectModel()
        model.add_slide(0.0)
        model.close()
        assert not model.is_open
        assert len(model.slides) == 0

    def test_set_scores(self) -> None:
        model = ProjectModel()
        model.set_scores([0.0, 1.0, 2.0], [0.1, 0.5, 0.3])
        assert model.score_timestamps == [0.0, 1.0, 2.0]
        assert model.score_values == [0.1, 0.5, 0.3]
        st = model.timeline.track("scores")
        assert st is not None
        assert len(st.clips()) == 3
''',
    }
    
    for path, content in tests.items():
        full_path = pyc_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding='utf-8')
        print(f'Written: {full_path} ({len(content)} chars)')


if __name__ == '__main__':
    main()
