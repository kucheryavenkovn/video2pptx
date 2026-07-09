# FILE: src/video2pptx/gui/subtitle_overlay.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Parse SRT/VTT via pysubs2, render subtitle text as overlay over QVideoWidget
#   SCOPE: QLabel positioned over video, updated on positionChanged. Hidden when no subtitles or between cues.
#   DEPENDS: pysubs2, M-GUI-VIDEOPLAYER
#   LINKS: M-GUI-SUBTITLE-OVERLAY
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   SubtitleOverlayWidget - QLabel overlay updated on positionChanged, synced with video player
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

import pysubs2
from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget


class SubtitleOverlayWidget(QLabel):
    # START_CONTRACT: SubtitleOverlayWidget
    #   PURPOSE: QLabel positioned over QVideoWidget showing current subtitle text
    #   INPUTS: { subtitle_path: Path | None, video_position: float from VideoPlayerWidget.positionChanged }
    #   OUTPUTS: updates visible text
    #   SIDE_EFFECTS: none
    #   LINKS: M-GUI-SUBTITLE-OVERLAY
    # END_CONTRACT: SubtitleOverlayWidget

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._subs: pysubs2.SSAFile | None = None
        self._setup_ui()

    # START_BLOCK_SETUP_UI
    def _setup_ui(self) -> None:
        self.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        self.setFont(font)

        self.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 140);
                padding: 6px 12px;
                border-radius: 4px;
            }
        """)

        self.hide()
    # END_BLOCK_SETUP_UI

    # START_BLOCK_LOAD_SUBTITLES
    def load_subtitles(self, subtitle_path: str | Path | None) -> None:
        if subtitle_path is None:
            self._subs = None
            self.hide()
            return

        path = Path(subtitle_path)
        if not path.is_file():
            logger.warning(f"[GUI-SubtitleOverlay][load_subtitles] File not found | path={path}")
            self._subs = None
            self.hide()
            return

        try:
            self._subs = pysubs2.load(str(path), encoding="utf-8")
            logger.info(f"[GUI-SubtitleOverlay][load_subtitles] Loaded | path={path} cues={len(self._subs)}")
        except Exception as exc:
            logger.warning(f"[GUI-SubtitleOverlay][load_subtitles] Failed to parse | path={path} error={exc}")
            self._subs = None
            self.hide()
    # END_BLOCK_LOAD_SUBTITLES

    # START_BLOCK_SYNC
    def sync_to_position(self, seconds: float) -> str | None:
        if self._subs is None:
            self.hide()
            return None

        text = self._get_text_at_time(seconds)
        if text:
            self.setText(text)
            self.show()
            return text
        else:
            self.hide()
            return None
    # END_BLOCK_SYNC

    # START_BLOCK_GET_TEXT
    def _get_text_at_time(self, seconds: float) -> str | None:
        if self._subs is None:
            return None

        ms = int(seconds * 1000)
        for event in self._subs.events:
            if event.start <= ms < event.end:
                if event.plaintext.strip():
                    return event.plaintext.strip()
        return None
    # END_BLOCK_GET_TEXT

    # START_BLOCK_CLEAR
    def clear_subtitles(self) -> None:
        self._subs = None
        self.setText("")
        self.hide()
    # END_BLOCK_CLEAR
