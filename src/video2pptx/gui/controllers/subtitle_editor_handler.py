# Helper: open subtitle editor dialog from MainWindow.
# Extracted to reduce main_window.py line count.

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialog

from video2pptx.gui.subtitle_editor import SubtitleEditorDialog


def open_subtitle_editor(
    slide,
    subs,
    output_dir: str,
    parent=None,
) -> bool:
    """Open SubtitleEditorDialog for a slide. Returns True if saved."""
    img_path = str(Path(output_dir) / slide.image) if slide.image else ""
    raw_cues: list[str] = []
    if subs is not None:
        for ev in subs.events:
            if ev.start >= slide.start * 1000 and ev.end <= slide.end * 1000:
                text = ev.plaintext.strip()
                if text:
                    raw_cues.append(text)
    dlg = SubtitleEditorDialog(
        slide_index=slide.index,
        start_sec=slide.start,
        end_sec=slide.end,
        image_path=img_path,
        transcript=slide.transcript or "",
        subtitle_cues=raw_cues,
        llm_config=getattr(slide, "llm", None),
        parent=parent,
    )
    if dlg.exec() == QDialog.DialogCode.Accepted:
        slide.transcript = dlg.transcript()
        desc = dlg.description()
        if desc.strip():
            slide.llm_description = desc.strip()
        return True
    return False
