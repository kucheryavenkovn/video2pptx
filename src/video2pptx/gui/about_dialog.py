# FILE: src/video2pptx/gui/about_dialog.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Product About dialog — version, build info, runtime capabilities, diagnostic info.
#   SCOPE: AboutDialog. Does NOT import domain/application infrastructure.
#   DEPENDS: PySide6, M-APP-IDENTITY
#   LINKS: M-GUI-ABOUT
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   AboutDialog - QDialog with product identity, version, build, runtime info
#   show_about_dialog - convenience function
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Initial About dialog for Phase 17.0
# END_CHANGE_SUMMARY

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from video2pptx.application.identity import ApplicationIdentity, application_identity


def show_about_dialog(parent=None) -> None:
    """Convenience: create and exec AboutDialog."""
    dlg = AboutDialog(application_identity(), parent)
    dlg.exec()


class AboutDialog(QDialog):
    """Product About dialog showing version, build, runtime, and diagnostic info."""

    def __init__(
        self,
        identity: ApplicationIdentity,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._identity = identity
        self.setWindowTitle(f"About {identity.name}")
        self.setMinimumSize(500, 420)
        self.setMaximumSize(700, 600)
        self._setup_ui()

    # START_BLOCK_SETUP_UI
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        identity = self._identity

        # Title
        title = QLabel(f"<b>{identity.name}</b>")
        title_font = QFont()
        title_font.setPointSize(16)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel(identity.description)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Version + Build
        version_label = QLabel(
            f"Version: {identity.version_str}"
            f"{'  (Beta)' if identity.version.is_prerelease else ''}"
        )
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        if identity.build.commit_sha:
            sha_short = identity.build.commit_sha[:7]
            build_label = QLabel(f"Build: {sha_short}  |  {identity.build.build_type.value}")
            build_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            build_label.setStyleSheet("color: #888;")
            layout.addWidget(build_label)

        # Author + License
        author_label = QLabel(f"{identity.author}  |  License: {identity.license_name}")
        author_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        author_label.setStyleSheet("color: #888;")
        layout.addWidget(author_label)

        # Separator
        layout.addSpacing(8)

        # Runtime info
        runtime = identity.runtime_info()
        info_text = (
            f"<b>Runtime</b><br>"
            f"OS: {runtime['os']} {runtime['os_release']} ({runtime['architecture']})<br>"
            f"Qt: {self._qt_version()}<br>"
            f"Python: {runtime['python_version']} ({runtime['python_implementation']})<br>"
            f"Executable: {runtime['executable']}"
        )
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Description
        layout.addSpacing(4)
        desc = QLabel(
            "Extract slide intervals from educational videos, "
            "link to SRT/VTT subtitles, "
            "and export Markdown/PPTX presentations."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666;")
        layout.addWidget(desc)

        layout.addStretch()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_github = QPushButton("GitHub")
        btn_github.clicked.connect(self._open_github)
        btn_layout.addWidget(btn_github)

        btn_logs = QPushButton("Open Logs")
        btn_logs.clicked.connect(self._open_logs)
        btn_layout.addWidget(btn_logs)

        btn_diag = QPushButton("Copy Info")
        btn_diag.clicked.connect(self._copy_diagnostic)
        btn_layout.addWidget(btn_diag)

        btn_layout.addStretch()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        btn_layout.addWidget(buttons)
        layout.addLayout(btn_layout)

    # END_BLOCK_SETUP_UI

    # START_BLOCK_ACTIONS
    def _open_github(self) -> None:
        QDesktopServices.openUrl(self._identity.repository_url)

    def _open_logs(self) -> None:
        log_dir = self._log_dir()
        log_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(log_dir.as_uri())

    def _copy_diagnostic(self) -> None:
        text = self._identity.diagnostic_text()
        QApplication.clipboard().setText(text)

    @staticmethod
    def _log_dir() -> Path:
        if sys.platform == "win32":
            base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        else:
            base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
        return base / "Video2PPTX" / "logs"

    @staticmethod
    def _qt_version() -> str:
        from PySide6.QtCore import qVersion
        return qVersion()
    # END_BLOCK_ACTIONS
