# FILE: src/video2pptx/gui/subtitle_editor.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: QDialog for editing slide subtitles with LLM vision analysis and transcript correction
#   SCOPE: Shows slide image and transcript, LLM button to describe image and correct transcript
#   DEPENDS: PySide6, M-LLM-CLIENT, M-PROJECT
#   LINKS: M-GUI-SUBTITLE-EDITOR
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT

from __future__ import annotations

from pathlib import Path

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from video2pptx.config import LlmConfig
from video2pptx.llm_client import LlmClient


class SubtitleEditorDialog(QDialog):
    # START_CONTRACT: SubtitleEditorDialog
    #   PURPOSE: Edit slide subtitles — shows screenshot, editable transcript, image description, LLM button
    #   INPUTS: { slide_index, start_sec, end_sec, image_path, transcript, llm_config }
    #   OUTPUTS: accepted → transcript, description
    #   SIDE_EFFECTS: may call LLM API
    #   LINKS: M-GUI-SUBTITLE-EDITOR
    # END_CONTRACT: SubtitleEditorDialog

    def __init__(
        self,
        slide_index: int,
        start_sec: float,
        end_sec: float,
        image_path: str,
        transcript: str,
        subtitle_cues: list[str] | None = None,
        llm_config: LlmConfig | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._slide_index = slide_index
        self._start_sec = start_sec
        self._end_sec = end_sec
        self._image_path = image_path
        self._llm_config = llm_config or LlmConfig()
        self._description = ""

        self.setWindowTitle(f"Subtitle Editor — Slide #{slide_index}")
        self.resize(920, 650)
        self._setup_ui()
        self._transcript_edit.setPlainText(transcript)
        if subtitle_cues:
            self._raw_subs_edit.setPlainText("\n".join(subtitle_cues))

    def transcript(self) -> str:
        return self._transcript_edit.toPlainText()

    def description(self) -> str:
        return self._description_edit.toPlainText()

    # START_BLOCK_SETUP_UI
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Info header
        info = QLabel(f"<b>Slide #{self._slide_index}</b> &nbsp; {self._fmt_time(self._start_sec)} – {self._fmt_time(self._end_sec)}")
        layout.addWidget(info)

        # Main area: image + transcript
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: screenshot
        img_container = QWidget()
        img_layout = QVBoxLayout(img_container)
        img_layout.setContentsMargins(0, 0, 0, 0)
        self._img_label = QLabel()
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        pix = QPixmap(self._image_path)
        if not pix.isNull():
            scaled = pix.scaled(420, 340, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self._img_label.setPixmap(scaled)
        else:
            self._img_label.setText("(no image)")
        img_layout.addWidget(self._img_label)
        img_layout.addStretch()
        splitter.addWidget(img_container)

        # Right: subtitles + transcript
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        right_layout.addWidget(QLabel("<b>Raw Subtitles:</b>"))
        self._raw_subs_edit = QTextEdit()
        self._raw_subs_edit.setMaximumHeight(120)
        self._raw_subs_edit.setPlaceholderText("Raw subtitle cues for this slide...")
        right_layout.addWidget(self._raw_subs_edit)

        right_layout.addWidget(QLabel("<b>Transcript:</b>"))
        self._transcript_edit = QTextEdit()
        self._transcript_edit.setPlaceholderText("Cleaned transcript / speaker notes...")
        right_layout.addWidget(self._transcript_edit, stretch=1)
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        layout.addWidget(splitter, stretch=1)

        # Slide description
        desc_layout = QVBoxLayout()
        desc_layout.addWidget(QLabel("<b>Slide Description (LLM):</b>"))
        self._description_edit = QTextEdit()
        self._description_edit.setMaximumHeight(100)
        self._description_edit.setPlaceholderText("LLM-generated description of slide contents, key terms...")
        desc_layout.addWidget(self._description_edit)
        layout.addLayout(desc_layout)

        # Buttons
        btn_row = QHBoxLayout()
        self._llm_btn = QPushButton("LLM Process")
        self._llm_btn.setToolTip("Run LLM: analyze screenshot → correct transcript")
        self._llm_btn.clicked.connect(self._on_llm_process)
        btn_row.addWidget(self._llm_btn)
        btn_row.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        btn_row.addWidget(buttons)
        layout.addLayout(btn_row)
    # END_BLOCK_SETUP_UI

    # START_BLOCK_LLM
    def _on_llm_process(self) -> None:
        self._llm_btn.setEnabled(False)
        self._llm_btn.setText("LLM processing...")

        try:
            client = LlmClient(self._llm_config)
            image_path = self._image_path

            # Step 1: vision analysis using custom prompt
            vision_prompt = self._llm_config.vision_prompt
            if not vision_prompt.strip():
                vision_prompt = "Describe this slide image in detail."

            if Path(image_path).is_file():
                raw_desc = client.vision(image_path, prompt=vision_prompt)
                self._description_edit.setPlainText(raw_desc)
                logger.info("[GUI-SubtitleEditor] Vision analysis complete")
            else:
                raw_desc = ""
                logger.warning("[GUI-SubtitleEditor] Image not found: {}", image_path)

            # Step 2: transcript correction using custom prompt + description
            transcript = self._transcript_edit.toPlainText()
            raw_subs = self._raw_subs_edit.toPlainText()
            if (transcript.strip() or raw_subs.strip()) and raw_desc:
                correction_prompt = self._llm_config.correction_prompt
                if not correction_prompt.strip():
                    correction_prompt = ("Correct the transcript using the slide description. "
                                        "Return only the corrected transcript.")

                correction_input = (
                    f"SLIDE DESCRIPTION:\n{raw_desc}\n\n"
                    f"RAW SUBTITLES:\n{raw_subs}\n\n"
                    f"CURRENT TRANSCRIPT:\n{transcript}"
                )
                corrected = client.chat([
                    {"role": "system", "content": correction_prompt},
                    {"role": "user", "content": correction_input},
                ])
                if corrected.strip():
                    self._transcript_edit.setPlainText(corrected.strip())
                    logger.info("[GUI-SubtitleEditor] Transcript corrected")
        except Exception as e:
            logger.error(f"[GUI-SubtitleEditor][_on_llm_process] LLM error: {e}")
            QMessageBox.warning(self, "LLM Error", str(e))
        finally:
            self._llm_btn.setEnabled(True)
            self._llm_btn.setText("LLM Process")
    # END_BLOCK_LLM

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"
