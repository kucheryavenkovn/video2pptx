# FILE: src/video2pptx/gui/workers.py
# VERSION: 0.2.0
# START_MODULE_CONTRACT
#   PURPOSE: QThread-based background workers for detect, notes, LLM, and preview operations
#   SCOPE: DetectWorker, NotesWorker, LlmWorker, PreviewWorker with progress/finished/error signals
#   DEPENDS: PySide6, M-DETECT-SLIDES, M-NOTES, M-LLM-ORCHESTRATOR, M-PROJECT, M-FRAME-FEATURES, M-VIDEO-DECODE
#   LINKS: M-GUI-WORKER
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   DetectWorker - run detect-slides on project in background thread
#   PreviewWorker - run fast preview analysis (scores only) in background thread
#   NotesWorker - run notes processing in background thread
#   LlmWorker - run LLM enrichment in background thread
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

from loguru import logger
from PySide6.QtCore import QObject, Signal

from video2pptx.config import AppConfig
from video2pptx.detect_slides import run_detect_slides
from video2pptx.markdown_export import export_to_markdown
from video2pptx.notes_pipeline import run_notes
from video2pptx.pptx_export import export_to_pptx
from video2pptx.project_manager import Project, update_project_state


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
            cfg.video.sample_fps = self._project.video_config.sample_fps
            cfg.video.decoder_backend = self._project.video_config.decoder_backend if self._project.video_config.decoder_backend != "auto" else (self._project.backend or "auto")
            cfg.detection.slide_roi = self._project.detection.slide_roi
            cfg.detection.ignore_rois = self._project.detection.ignore_rois
            cfg.detection.threshold = self._project.detection.threshold
            cfg.detection.min_slide_duration = self._project.detection.min_slide_duration
            cfg.detection.min_stable_duration = self._project.detection.min_stable_duration
            cfg.detection.dedupe_enabled = self._project.detection.dedupe_enabled

            self.progress.emit(5, "Opening video...")

            def on_pass1_progress(pct: int, msg: str) -> None:
                self.progress.emit(5 + int(pct * 0.65), msg)

            doc = run_detect_slides(
                video_path=video_path,
                out_dir=proj_dir,
                cfg=cfg,
                progress_callback=on_pass1_progress,
            )

            slides_json = proj_dir / "slides.json"
            update_project_state(self._project, detect_done=True, slides_json=str(slides_json))

            # Run notes pipeline if subtitles available
            sub_path = Path(self._project.subtitles) if self._project.subtitles else None
            if sub_path and sub_path.is_file():
                from video2pptx.gui.app_config import load_app_config
                cfg = load_app_config()
                notes_mode = cfg.notes_mode
                llm_cfg = self._project.llm if notes_mode == "llm" else None
                self.progress.emit(73, f"Processing notes ({notes_mode})...")
                enriched_doc = run_notes(
                    slides_json=slides_json,
                    subtitles_path=sub_path,
                    slides_dir=proj_dir / "slides",
                    notes_mode=notes_mode,
                    llm_config=llm_cfg,
                )
                doc = enriched_doc

            # Post-detection exports
            if self._project.detection.export_md:
                self.progress.emit(75, "Exporting Markdown...")
                export_to_markdown(doc, proj_dir / "deck.md", slides_dir=str(proj_dir / "slides"))

            if self._project.detection.export_pptx:
                self.progress.emit(85, "Exporting PPTX...")
                export_to_pptx(doc, proj_dir / "deck.pptx", slides_dir=str(proj_dir / "slides"), notes_mode="basic")

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

            from video2pptx.gui.app_config import load_app_config
            cfg = load_app_config()
            notes_mode = cfg.notes_mode
            llm_cfg = self._project.llm if notes_mode == "llm" else None

            self.progress.emit(10, f"Processing notes ({notes_mode})...")
            run_notes(
                slides_json=slides_json,
                subtitles_path=subs_path,
                slides_dir=Path(self._project.output_dir) / "slides",
                notes_mode=notes_mode,
                llm_config=llm_cfg,
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
            from video2pptx.llm_orchestrator import run_llm_pipeline
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


class PreviewWorker(QObject):
    # START_CONTRACT: PreviewWorker
    #   PURPOSE: Fast preview analysis — decodes video at sample_fps, computes visual_distance scores, returns timestamps+scores
    #   INPUTS: { video_path: str, sample_fps: float, project: Project | None }
    #   OUTPUTS: signals: finished(list[float] timestamps, list[float] scores), progress(int), error(str)
    #   SIDE_EFFECTS: none (no files written)
    #   LINKS: M-GUI-WORKER
    # END_CONTRACT: PreviewWorker

    finished = Signal(list, list, float)  # timestamps, scores, video_duration
    progress = Signal(int)
    error = Signal(str)

    def __init__(
        self,
        video_path: str,
        sample_fps: float = 2.0,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._video_path = video_path
        self._sample_fps = sample_fps

    def run(self) -> None:
        try:
            from video2pptx.frame_features import extract_features, visual_distance
            from video2pptx.video_decode import VideoDecoder

            decoder = VideoDecoder(self._video_path, sample_fps=self._sample_fps)
            info = decoder.get_info()
            duration = info.duration
            if duration <= 0:
                self.error.emit("Could not determine video duration")
                return

            prev_features = None
            timestamps: list[float] = []
            scores: list[float] = []
            processed = 0

            for vf in decoder.iter_frames():
                ff = extract_features(vf.image)
                ff.timestamp = vf.timestamp
                if prev_features is not None:
                    score = visual_distance(prev_features, ff)
                    scores.append(score)
                    timestamps.append(vf.timestamp)

                prev_features = ff
                processed += 1
                pct = int((vf.timestamp / duration) * 100)
                self.progress.emit(pct)

            logger.info(
                "[GUI-Worker][PreviewWorker] Preview complete | frames={} scores={}",
                processed,
                len(scores),
            )
            self.finished.emit(timestamps, scores, duration)

        except Exception as e:
            logger.error(f"[GUI-Worker][PreviewWorker] Error: {e}")
            self.error.emit(str(e))


class QuickDetectWorker(QObject):

    progress = Signal(int, str)
    finished = Signal(str)  # path to slides.json
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

            from video2pptx.detect_slides import run_detect_slides

            proj_dir = Path(self._project.output_dir)
            cfg = AppConfig()
            cfg.video.sample_fps = 1.0
            cfg.video.decoder_backend = self._project.video_config.decoder_backend or self._project.backend or "auto"
            cfg.detection.slide_roi = self._project.detection.slide_roi
            cfg.detection.ignore_rois = self._project.detection.ignore_rois
            cfg.detection.threshold = self._project.detection.threshold
            cfg.detection.min_slide_duration = self._project.detection.min_slide_duration
            cfg.detection.min_stable_duration = self._project.detection.min_stable_duration
            cfg.detection.dedupe_enabled = False  # no dedup for quick

            def on_progress(pct: int, msg: str) -> None:
                self.progress.emit(5 + int(pct * 0.65), msg)

            self.progress.emit(2, "Quick detecting (keyframes)...")
            doc = run_detect_slides(
                video_path=video_path,
                out_dir=proj_dir,
                cfg=cfg,
                quick_mode=True,
                progress_callback=on_progress,
            )

            slides_json = proj_dir / "slides.json"
            update_project_state(self._project, detect_done=True, slides_json=str(slides_json))

            # Notes pipeline if subtitles available
            sub_path = Path(self._project.subtitles) if self._project.subtitles else None
            if sub_path and sub_path.is_file():
                from video2pptx.gui.app_config import load_app_config
                from video2pptx.notes_pipeline import run_notes
                app_cfg = load_app_config()
                notes_mode = app_cfg.notes_mode
                llm_cfg = self._project.llm if notes_mode == "llm" else None
                self.progress.emit(73, "Processing notes...")
                run_notes(
                    slides_json=slides_json,
                    subtitles_path=sub_path,
                    slides_dir=proj_dir / "slides",
                    notes_mode=notes_mode,
                    llm_config=llm_cfg,
                )

            self.progress.emit(100, f"Quick detect complete: {len(doc.slides)} slides")
            self.finished.emit(str(slides_json))

        except Exception as e:
            logger.error(f"[GUI-Worker][QuickDetectWorker] Error: {e}")
            self.error.emit(str(e))
