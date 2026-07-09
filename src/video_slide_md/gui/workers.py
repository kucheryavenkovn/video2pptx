# FILE: src/video_slide_md/gui/workers.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: QThread-based background workers for detect, notes, and LLM operations
#   SCOPE: DetectWorker, NotesWorker, LlmWorker with progress/finished/error signals
#   DEPENDS: PySide6, M-DETECT-SLIDES, M-NOTES, M-LLM-ORCHESTRATOR, M-PROJECT
#   LINKS: M-GUI-WORKER
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   DetectWorker - run detect-slides on project in background thread
#   NotesWorker - run notes processing in background thread
#   LlmWorker - run LLM enrichment in background thread
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject, Signal

from video_slide_md.config import AppConfig
from video_slide_md.detect_slides import run_detect_slides
from video_slide_md.notes_pipeline import run_notes
from video_slide_md.project_manager import Project, update_project_state


class DetectWorker(QObject):
    # START_CONTRACT: DetectWorker
    #   PURPOSE: Run detect-slides on a project in a background thread
    #   INPUTS: { project: Project }
    #   OUTPUTS: signals: progress(int, str), finished(str), error(str)
    #   SIDE_EFFECTS: runs video detection, writes slides.json and images
    #   LINKS: M-GUI-WORKER
    # END_CONTRACT: DetectWorker

    progress = Signal(int, str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, project: Project, parent=None) -> None:
        super().__init__(parent)
        self._project = project

    def run(self) -> None:
        try:
            video_path = Path(self._project.video)
            if not video_path.is_file():
                self.error.emit(f"Video not found: {video_path}")
                return

            proj_dir = Path(self._project.output_dir)
            cfg = AppConfig()

            self.progress.emit(10, "Opening video...")
            doc = run_detect_slides(
                video_path=video_path,
                out_dir=proj_dir,
                cfg=cfg,
            )

            slides_json = proj_dir / "slides.json"
            update_project_state(self._project, detect_done=True, slides_json=str(slides_json))

            self.progress.emit(100, f"Detection complete: {len(doc.slides)} slides")
            self.finished.emit(str(slides_json))

        except Exception as e:
            logger.error(f"[GUI-Worker][DetectWorker] Error: {e}")
            self.error.emit(str(e))


class NotesWorker(QObject):
    # START_CONTRACT: NotesWorker
    #   PURPOSE: Run notes processing on a project in a background thread
    #   INPUTS: { project: Project }
    #   OUTPUTS: signals: progress(int, str), finished(str), error(str)
    #   SIDE_EFFECTS: updates slides.json with cleaned notes
    #   LINKS: M-GUI-WORKER
    # END_CONTRACT: NotesWorker

    progress = Signal(int, str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, project: Project, parent=None) -> None:
        super().__init__(parent)
        self._project = project

    def run(self) -> None:
        try:
            slides_json = Path(self._project.output_dir) / "slides.json"
            if not slides_json.is_file():
                self.error.emit(f"slides.json not found: {slides_json}")
                return

            subs_path = Path(self._project.subtitles) if self._project.subtitles else None

            self.progress.emit(30, "Processing notes...")
            run_notes(
                slides_json=slides_json,
                subtitles_path=subs_path,
                slides_dir=Path(self._project.output_dir) / "slides",
                notes_mode="basic",
            )

            update_project_state(self._project, notes_done=True)
            self.progress.emit(100, "Notes processing complete")
            self.finished.emit(str(slides_json))

        except Exception as e:
            logger.error(f"[GUI-Worker][NotesWorker] Error: {e}")
            self.error.emit(str(e))


class LlmWorker(QObject):
    # START_CONTRACT: LlmWorker
    #   PURPOSE: Run LLM enrichment on a project in a background thread
    #   INPUTS: { project: Project }
    #   OUTPUTS: signals: progress(int, str), finished(str), error(str)
    #   SIDE_EFFECTS: calls LM Studio API, updates slides.json
    #   LINKS: M-GUI-WORKER
    # END_CONTRACT: LlmWorker

    progress = Signal(int, str)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, project: Project, parent=None) -> None:
        super().__init__(parent)
        self._project = project

    def run(self) -> None:
        try:
            slides_json = Path(self._project.output_dir) / "slides.json"
            if not slides_json.is_file():
                self.error.emit(f"slides.json not found: {slides_json}")
                return

            self.progress.emit(10, "Initializing LLM...")
            from video_slide_md.llm_orchestrator import run_llm_pipeline
            run_llm_pipeline(
                slides_path=slides_json,
                llm_config=self._project.llm,
                slides_dir=Path(self._project.output_dir) / "slides",
                output_path=slides_json,
            )

            update_project_state(self._project, llm_done=True)
            self.progress.emit(100, "LLM processing complete")
            self.finished.emit(str(slides_json))

        except Exception as e:
            logger.error(f"[GUI-Worker][LlmWorker] Error: {e}")
            self.error.emit(str(e))
