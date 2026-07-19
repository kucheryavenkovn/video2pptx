# FILE: src/video2pptx/gui/main_window.py
# VERSION: 0.5.0
# START_MODULE_CONTRACT
#   PURPOSE: Main GUI window — QMainWindow with menu bar, video player, subtitle overlay, always-visible timeline, marker panel, project lifecycle, detection
#   SCOPE: Adapt Qt events to canonical project, pipeline, and timeline controllers.
#   DEPENDS: PySide6, M-PROJECT-MODEL, M-GUI-PROJECT-CTRL, M-GUI-PIPELINE-CTRL, M-GUI-TIMELINE-CTRL, M-GUI-WINDOW-UI
#   LINKS: M-GUI-MAIN
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   MainWindow - QMainWindow subclass with full integration, always-visible timeline, marker panel
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v0.5.0 - Step 8.5 canonical state, async pipeline, SlideId boundary, and UI extraction
#   v0.4.1 - Reset Auto and Auto Align controls when a project closes
#   v0.4.0 - Refactor to use ProjectModel (QObject with signals) instead of Project (Pydantic data bag)
#   v0.3.1 - Fix _on_slide_resized duplicate save + missing timeline refresh
#   v0.3.1 - Fix closeEvent not clearing timeline (now calls _on_close_project)
#   v0.3.1 - Fix _on_detect_finished / _on_notes_finished pass force=True to load_slides_into_project
# END_CHANGE_SUMMARY

from __future__ import annotations

from pathlib import Path

import pysubs2
from loguru import logger
from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox

from video2pptx.backends import BACKENDS
from video2pptx.gui.app_config import add_recent_project, load_app_config, save_app_config
from video2pptx.gui.status_manager import StatusBarManager
from video2pptx.project_model import ProjectModel


class MainWindow(QMainWindow):
    # START_CONTRACT: MainWindow
    #   PURPOSE: Main application window integrating all GUI modules for slide detection workflow
    #   INPUTS: none (creates empty window)
    #   OUTPUTS: none (Qt event loop)
    #   SIDE_EFFECTS: creates GUI window, starts event loop, connects all subcomponents
    #   LINKS: M-GUI-MAIN
    # END_CONTRACT: MainWindow

    project_changed = Signal(object)  # Project (legacy, kept for MCP)
    _PIPELINE_BUTTONS: list = []  # populated by setup_main_window_ui

    def __init__(self) -> None:
        super().__init__()
        from video2pptx.bootstrap.application import ApplicationServices
        self._app_svcs = ApplicationServices()
        self._model = ProjectModel(self)
        from video2pptx.gui.controllers import (
            PipelineController,
            ProjectController,
            TimelineController,
        )
        self._project_ctrl = ProjectController(services=self._app_svcs, parent=self)
        self._pipeline_ctrl = PipelineController(services=self._app_svcs, parent=self)
        self._timeline_ctrl = TimelineController(services=self._app_svcs, parent=self)
        self._syncing_projection = False
        self._subs: pysubs2.SSAFile | None = None
        self._app_config = load_app_config()
        self._status = StatusBarManager(self)
        from video2pptx.gui.main_window_ui import (
            MainWindowHost,
            connect_main_window_signals,
            setup_main_window_ui,
        )
        setup_main_window_ui(self)
        connect_main_window_signals(self)
        self._host = MainWindowHost(self, self._model)
        self._host.start()
        self._try_restore_last_project()

    # START_BLOCK_MODEL_SIGNALS
    def _on_model_slides_changed(self) -> None:
        proj = self._model.project_data
        if proj and proj.slides:
            self._timeline.set_slides(proj.slides)
            self._timeline.set_video_duration(max(proj.slides[-1].end, self._video_player.duration()))
            self._timeline.set_project(proj)
            self._timeline.zoom_fit()
        has = bool(proj and proj.slides)
        self._btn_export.setEnabled(has)
        self._btn_process_notes.setEnabled(has and bool(proj and proj.subtitles))

    def _on_model_subtitles_changed(self) -> None:
        self._load_subs_from_model()
        self._timeline.set_subtitles(self._subs)
        project = self._model.project_data
        text = Path(project.subtitles).name if project and project.subtitles else "—"
        self._subs_label.setText(f"Subtitles: {text}")

    def _on_model_video_changed(self, path: str) -> None:
        self._video_label.setText(f"Video: {Path(path).name}" if path else "Video: —")
        if path:
            self._video_player.load_video(path)
        self._btn_detect.setEnabled(bool(path))
        self._btn_quick_preview.setEnabled(bool(path))

    def _reset_ui(self) -> None:
        self._video_player.clear_video()
        self._video_player.set_subtitle_text(None)
        self._subs = None
        self._timeline.set_subtitles(None)
        self._timeline.set_slides([])
        self._timeline.set_markers([])
        self._timeline.clear_scores()
        for lbl, txt in ((self._video_label, "Video: —"), (self._subs_label, "Subtitles: —")):
            lbl.setText(txt)
        for btn in (self._btn_detect, self._btn_quick_preview, self._btn_auto, self._btn_auto_align, self._btn_export, self._btn_process_notes, self._btn_save):
            btn.setEnabled(False)
        self.setWindowTitle("video2pptx")
        self.statusBar().showMessage("Project closed")
    # END_BLOCK_MODEL_SIGNALS

    def _confirm(self, title: str, text: str) -> bool:
        return self._host.active or QMessageBox.question(self, title, text, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    # START_BLOCK_RECENT_PROJECTS
    def _refresh_recent_projects(self) -> None:
        self._app_config = load_app_config()
        self._menu_bar.set_recent_projects(self._app_config.recent_projects)
    # END_BLOCK_RECENT_PROJECTS

    def _on_video_position_changed(self, s: float) -> None:
        self._video_player.set_subtitle_text(self._get_subtitle_at(s))
        self._video_player.hide_slide_image()
        self._timeline.set_position(s)

    def _on_video_duration_changed(self, s: float) -> None:
        if s > 0:
            self._timeline.set_video_duration(s)
            proj = self._model.project_data
            if proj and proj.slides:
                from PySide6.QtCore import QTimer
                QTimer.singleShot(100, self._timeline.zoom_fit)

    def _get_subtitle_at(self, s: float) -> str | None:
        if self._subs is None:
            return None
        ms = int(s * 1000)
        for ev in self._subs.events:
            if ev.start <= ms < ev.end and ev.plaintext.strip():
                return ev.plaintext.strip()
        return None

    def _load_subs_from_model(self) -> None:
        proj = self._model.project_data
        self._subs = None
        if proj and proj.subtitles:
            p = Path(proj.subtitles)
            if p.is_file():
                try:
                    self._subs = pysubs2.load(str(p), encoding="utf-8")
                except Exception:
                    pass

    # START_BLOCK_PROJECT_LIFECYCLE
    def _on_new_project(self) -> None:
        proj_dir = QFileDialog.getExistingDirectory(self, "Select Project Directory")
        if not proj_dir:
            return
        import os
        folder_name = os.path.basename(os.path.normpath(proj_dir))
        parent_dir = str(Path(proj_dir).parent)
        self._project_ctrl.create(parent_dir, folder_name)

    def _on_open_project(self) -> None:
        proj_dir = QFileDialog.getExistingDirectory(self, "Open Project Directory")
        if not proj_dir:
            return
        self._project_ctrl.open(proj_dir)

    def _on_open_recent_project(self, path: str) -> None:
        proj_dir = Path(path).resolve()
        if not proj_dir.is_dir():
            QMessageBox.critical(self, "Error", f"Project directory not found:\n{path}")
            if path in self._app_config.recent_projects:
                self._app_config.recent_projects.remove(path)
                save_app_config(self._app_config)
            self._refresh_recent_projects()
            return
        self._project_ctrl.open(str(proj_dir))

    def _on_project_opened(self) -> None:
        if self._project_ctrl.project_dir:
            self._syncing_projection = True
            try:
                self._model.open(self._project_ctrl.project_dir)
            finally:
                self._syncing_projection = False
        proj = self._model.project_data
        if proj is None:
            return
        self._video_label.setText(f"Video: {Path(proj.video).name}" if proj.video else "Video: —")
        if proj.video:
            self._video_player.load_video(proj.video)
        self._load_subs_from_model()
        self._subs_label.setText(f"Subtitles: {Path(proj.subtitles).name}" if proj.subtitles else "Subtitles: —")
        self._btn_detect.setEnabled(bool(proj.video))
        self._btn_quick_preview.setEnabled(bool(proj.video))
        self._btn_auto.setEnabled(bool(proj.video))
        has_slides = bool(proj.slides)
        self._btn_export.setEnabled(has_slides)
        self._btn_process_notes.setEnabled(has_slides and bool(proj.subtitles))
        self._btn_auto_align.setEnabled(has_slides and bool(proj.subtitles) and getattr(proj.state, 'detect_done', False))
        self._btn_save.setEnabled(True)
        self.setWindowTitle(f"video2pptx — {proj.name}")
        dur = max(getattr(proj, "video_duration", 0) or 0, proj.slides[-1].end if proj.slides else 0)
        if proj.slides:
            self._timeline.set_slides(proj.slides)
        self._timeline.set_video_duration(dur)
        self._timeline.set_subtitles(self._subs)
        self._timeline.set_project(proj)
        if proj.score_timestamps and proj.score_values:
            self._timeline.set_scores(proj.score_timestamps, proj.score_values)
        self.project_changed.emit(proj)
        d = self._model.output_dir or getattr(proj, "project_dir", "")
        if d:
            self._app_config = add_recent_project(d, self._app_config)
            save_app_config(self._app_config)
            self._menu_bar.set_recent_projects(self._app_config.recent_projects)
        logger.info("[GUI-Main][_on_project_opened] Project loaded | name={}", proj.name)

    def _on_close_project(self) -> None:
        if self._model.is_open:
            self._project_ctrl.close()
            self._model.close()

    def _on_save_project(self) -> None:
        if self._project_ctrl.save():
            self.statusBar().showMessage("Project saved")

    def _on_import_video(self) -> None:
        if not self._model.is_open:
            return
        p, _ = QFileDialog.getOpenFileName(self, "Import Video", "", "Video Files (*.mp4 *.mkv *.mov *.webm);;All Files (*)")
        if not p:
            return
        try:
            self._model.import_video(p)
            m = self._model.project_data
            if m and m.subtitles:
                self._load_subs_from_model()
                self._subs_label.setText(f"Subtitles: {Path(m.subtitles).name}")
                self._timeline.set_subtitles(self._subs)
            self.statusBar().showMessage(f"Video imported, subs auto-detected: {Path(m.subtitles).name}" if m and m.subtitles else f"Video imported: {Path(p).name}")
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_import_srt(self) -> None:
        if not self._model.is_open:
            return
        p, _ = QFileDialog.getOpenFileName(self, "Import Subtitles", "", "Subtitle Files (*.srt *.vtt);;All Files (*)")
        if not p:
            return
        try:
            self._model.load_subtitles(p)
            self.statusBar().showMessage(f"Subtitles imported: {Path(p).name}")
        except FileNotFoundError as e:
            QMessageBox.critical(self, "Error", str(e))

    # START_BLOCK_PROJECT_RESTORE
    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        try:
            cfg = load_app_config()
            cfg.last_project_path = self._model.output_dir
            save_app_config(cfg)
        except Exception:
            pass
        self._project_ctrl.close()
        self._model.close()
        super().closeEvent(event)

    def _try_restore_last_project(self) -> None:
        try:
            cfg = load_app_config()
            if cfg.restore_last_project and cfg.last_project_path and (Path(cfg.last_project_path) / "project.json").is_file():
                from PySide6.QtCore import QTimer
                QTimer.singleShot(0, lambda: self._do_restore_project(str(cfg.last_project_path)))
        except Exception:
            pass

    def _do_restore_project(self, project_path: str) -> None:
        import os
        if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
            return
        try:
            r = QMessageBox.question(self, "Restore", f"Open previous project?\n\n{Path(project_path).name}", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if r == QMessageBox.StandardButton.Yes:
                self._model.open(project_path)
        except Exception:
            pass
    # END_BLOCK_PROJECT_RESTORE

    # START_BLOCK_PIPELINE
    def _run_pipeline(self, stage: str, **params) -> None:
        proj = self._model.project_data
        if not proj:
            return
        project_dir = self._project_ctrl.project_dir or proj.output_dir
        if not project_dir:
            return
        result = getattr(self._pipeline_ctrl, f"run_{stage}")(project_dir, **params)
        if result is None:
            return
        if result.accepted:
            self._status.start(stage, stage.capitalize())
        else:
            self._on_operation_rejected(stage, result.active_stage or "")

    def _on_operation_rejected(self, requested: str, active: str) -> None:
        cap = active.capitalize()
        self.statusBar().showMessage(f"{cap} is already running")
        QMessageBox.information(self, "Operation in Progress", f"{cap} is already running. Wait for it to finish.")

    def _on_busy_changed(self, busy: bool) -> None:
        for btn in self._PIPELINE_BUTTONS:
            btn.setEnabled(not busy)

    def _on_pipeline_finished(self, result) -> None:
        key = result.stage
        self._status.finish(f"{key.capitalize()} complete", operation_key=key)
        self._reload_project_state()
        if result.stage in ("detect", "preview"):
            proj = self._model.project_data
            if proj:
                self._btn_auto_align.setEnabled(bool(proj.subtitles) and bool(proj.slides))
        if result.stage in ("export",):
            out = result.data.get("output_path", "")
            if out:
                self._offer_open_file(Path(out))

    def _on_pipeline_error(self, msg: str) -> None:
        stage = self._pipeline_ctrl.active_stage or "pipeline"
        self._status.finish(f"{stage.capitalize()} failed: {msg}", operation_key=stage)
        QMessageBox.critical(self, "Error", msg)

    def _on_detect(self) -> None:
        proj = self._model.project_data
        if not proj:
            return
        if proj.slides and not self._confirm("Re-detect?", "Overwrite slides.json and screenshots?"):
            return
        self._run_pipeline("detect")

    def _on_quick_detect(self) -> None:
        proj = self._model.project_data
        if not proj:
            return
        if proj.slides and not self._confirm("Re-run?", "Overwrite slides?"):
            return
        self._run_pipeline("preview")

    def _on_process_notes(self) -> None:
        proj = self._model.project_data
        if not proj:
            return
        if proj.state.notes_done and not self._confirm("Re-process?", "Notes already processed."):
            return
        self._btn_process_notes.setEnabled(False)
        self._run_pipeline("notes")

    def _on_auto_align(self) -> None:
        proj = self._model.project_data
        if not proj:
            return
        self._run_pipeline("align")

    def _on_auto(self) -> None:
        proj = self._model.project_data
        if not proj or not proj.video:
            return
        self._run_pipeline("auto")

    def _on_export_md(self) -> None:
        proj = self._model.project_data
        if not proj:
            return
        out = Path(proj.output_dir) / "deck.md"
        if out.exists() and not self._confirm("Overwrite?", f"{out.name} already exists."):
            return
        self._run_pipeline("export", format="markdown", output_path=str(out))

    def _on_export_pptx(self) -> None:
        proj = self._model.project_data
        if not proj:
            return
        out = Path(proj.output_dir) / "deck.pptx"
        if out.exists() and not self._confirm("Overwrite?", f"{out.name} already exists."):
            return
        self._run_pipeline("export", format="pptx", output_path=str(out))

    def _on_add_marker_at_position(self) -> None:
        if not self._model.is_open:
            QMessageBox.information(self, "Add Slide", "Open a project first")
            return
        ts = self._video_player._player.position() / 1000.0
        self._on_add_manual_slide(ts)
    # END_BLOCK_PIPELINE

    @staticmethod
    def _offer_open_file(path: Path) -> None:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        r = QMessageBox.question(None, "Export complete", f"File saved:\n{path}\n\nOpen?",
                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if r == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _on_project_ctrl_error(self, msg: str) -> None:
        QMessageBox.critical(self, "Error", msg)
    # END_BLOCK_PROJECT_LIFECYCLE

    # START_BLOCK_SETTINGS_MENU
    def _on_project_settings(self) -> None:
        project = self._project_ctrl.project
        if project is None:
            QMessageBox.information(self, "Project Settings", "Open a project first")
            return
        from video2pptx.gui.settings_project import run_project_settings_flow

        grabber = None
        vp = getattr(self, "_video_player", None)
        if vp is not None and getattr(vp, "_view", None) is not None:
            grabber = lambda: vp._view.grab()  # noqa: E731
        run_project_settings_flow(
            self,
            project,
            save_fn=self._project_ctrl.save,
            status_fn=lambda m: self.statusBar().showMessage(m),
            frame_grabber=grabber,
            reload_fn=lambda: self._project_ctrl.reload(emit=True),
        )

    def _on_app_settings(self) -> None:
        from video2pptx.gui.settings_app import AppSettingsDialog
        dlg = AppSettingsDialog(self._app_config, self)
        if dlg.exec():
            logger.info("[GUI-Main][_on_app_settings] App settings updated")
            self.statusBar().showMessage("App settings updated")

    # END_BLOCK_SETTINGS_MENU

    # START_BLOCK_TIMELINE_MARKERS
    def _project_dir(self):
        return self._project_ctrl.project_dir or (self._model.output_dir if self._model.is_open else None)

    def _with_timeline(self, action: str, *a, msg="", confirm="", **kw):
        d = self._project_dir()
        if not d:
            return
        if confirm and not self._confirm("Confirm", confirm):
            return
        getattr(self._timeline_ctrl, action)(d, *a, **kw)
        self._reload_project_state()
        self._sync_timeline()
        if msg:
            self.statusBar().showMessage(msg)

    def _on_add_manual_slide(self, ts: float) -> None:
        self._with_timeline("add_slide", ts, msg=f"Manual slide added at {ts:.1f}s")

    def _on_set_slide_frame(self, slide_index: int) -> None:
        d = self._project_dir()
        if not d:
            return
        pos_sec = self._video_player._player.position() / 1000.0
        try:
            import cv2
            proj = self._model.project_data
            if not proj:
                return
            from video2pptx.video_decode import VideoDecoder
            decoder = VideoDecoder(proj.video, sample_fps=1.0)
            for vf in decoder.iter_frames():
                if vf.timestamp >= pos_sec:
                    img = cv2.cvtColor(vf.image, cv2.COLOR_RGB2BGR)
                    (Path(d) / "slides").mkdir(parents=True, exist_ok=True)
                    image_path = Path(d) / "slides" / f"slide_{slide_index:03d}.png"
                    cv2.imwrite(str(image_path), img)
                    slide_id = self._slide_id(slide_index)
                    if slide_id is None:
                        return
                    from video2pptx.domain.artifacts import ArtifactRef
                    self._timeline_ctrl.set_slide_image(d, slide_id, ArtifactRef.parse(image_path.relative_to(d)))
                    self._reload_project_state()
                    self._sync_timeline()
                    self.statusBar().showMessage(f"Slide {slide_index} image set from {pos_sec:.1f}s")
                    break
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to capture frame: {e}")

    def _on_clear_slide_image(self, slide_index: int) -> None:
        slide_id = self._slide_id(slide_index)
        if slide_id is not None:
            self._with_timeline("clear_slide_image", slide_id, msg=f"Slide {slide_index} image cleared")

    def _on_delete_slide(self, slide_index: int) -> None:
        slide_id = self._slide_id(slide_index)
        if slide_id is not None:
            self._with_timeline("delete_slide", slide_id, msg=f"Slide {slide_index} deleted", confirm=f"Delete slide #{slide_index}?")

    def _on_slide_moved(self, index: int, new_start: float, new_end: float) -> None:
        d = self._project_dir()
        if not d:
            return
        slide_id = self._slide_id(index)
        if slide_id is None:
            return
        self._timeline_ctrl.move_slide(d, slide_id, new_start, new_end)
        self._reload_project_state()
        QTimer.singleShot(0, self._sync_timeline)
        self.statusBar().showMessage(f"Slide {index} moved: {new_start:.1f}s – {new_end:.1f}s")

    def _on_slide_resized(self, index: int, new_start: float, new_end: float) -> None:
        d = self._project_dir()
        if not d:
            return
        slide_id = self._slide_id(index)
        if slide_id is None:
            return
        self._timeline_ctrl.resize_slide(d, slide_id, new_end)
        self._reload_project_state()
        QTimer.singleShot(0, self._sync_timeline)
        self.statusBar().showMessage(f"Slide {index} resized: {new_start:.1f}s – {new_end:.1f}s")

    def _on_open_subtitle_editor(self, slide_index: int) -> None:
        proj = self._model.project_data
        if not proj or slide_index >= len(proj.slides):
            return
        from video2pptx.gui.controllers.subtitle_editor_handler import open_subtitle_editor
        if open_subtitle_editor(proj.slides[slide_index], self._subs, self._model.output_dir or "", self):
            if self._project_ctrl.save():
                self.statusBar().showMessage(f"Slide {slide_index} saved")
    # END_BLOCK_TIMELINE_MARKERS

    def _sync_timeline(self) -> None:
        proj = self._model.project_data
        if proj:
            if proj.slides:
                self._timeline.set_slides(proj.slides)
                self._timeline.set_project(proj)
            self._timeline.set_subtitles(self._subs)
            self._timeline.zoom_fit()

    def _slide_id(self, display_index: int):
        project = self._project_ctrl.project
        if project is None or not 0 <= display_index < len(project.slides):
            return None
        return project.slides[display_index].slide_id

    def _reload_project_state(self) -> None:
        self._project_ctrl.reload(emit=False)
        if self._project_ctrl.project_dir:
            self._model.open(self._project_ctrl.project_dir)

    def _on_seek_to_marker(self, ts: float) -> None:
        self._video_player._player.pause()
        self._video_player._player.setPosition(int(ts * 1000))
        self.statusBar().showMessage(f"Seeked to {ts:.1f}s")

    def _on_open_timeline_image(self, path: str, slide_index: int = 0) -> None:
        if not path:
            self.statusBar().showMessage(f"Slide #{slide_index}: no image set")
            return
        full = str(Path(self._model.output_dir) / path) if self._model.project_data else path
        self._video_player.show_slide_image(full, f"Slide #{slide_index}" if slide_index else "")
        self.statusBar().showMessage(f"Slide #{slide_index}: {path}")

    def _on_open_marker_panel(self) -> None:
        proj = self._model.project_data
        if not proj:
            QMessageBox.information(self, "Markers", "Open a project first")
            return
        self.statusBar().showMessage(f"Slides: {len(proj.slides)}")

    def _show_backend_info(self) -> None:
        try:
            avail = [n for n, i in BACKENDS.items() if i["available"]]
            self._backend_label.setText(f"Backend: {', '.join(avail) if avail else 'none'}")
        except Exception:
            self._backend_label.setText("Backend: auto")

    def _on_worker_progress_msg(self, pct: int, msg: str) -> None:
        key = self._pipeline_ctrl.active_stage or self._status.key()
        self._status.update(pct, msg, operation_key=key)
