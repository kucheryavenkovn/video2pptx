# FILE: src/video2pptx/gui/update_dialog.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Update-check result dialogs — UpdateAvailableDialog, up-to-date, and failure dialogs.
#   SCOPE: Qt dialogs only. No HTTP, no business logic.
#   DEPENDS: PySide6, M-UPDATE-CHECKER
#   LINKS: M-UPDATE-CHECKER
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   UpdateAvailableDialog - QDialog showing new version, release notes, download/github/later
#   show_up_to_date_dialog - QMessageBox "You're up to date"
#   show_check_failed_dialog - QMessageBox "Check failed"
# END_MODULE_MAP

from __future__ import annotations

from packaging.version import Version
from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from video2pptx.application.update_service import ReleaseInfo


class UpdateAvailableDialog(QDialog):
    def __init__(
        self,
        release: ReleaseInfo,
        current_version: Version,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._release = release
        self._current_version = current_version
        self._installer_asset = self._find_installer_asset()
        self.setWindowTitle("Update Available")
        self.setMinimumSize(520, 460)
        self._setup_ui()

    def _find_installer_asset(self) -> str | None:
        expected = f"Video2PPTX-{self._release.version}-Setup-x64.exe"
        for asset in self._release.assets:
            if asset.name == expected:
                return asset.browser_download_url
        return None

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)

        title = QLabel("<b>A new version of Video2PPTX is available</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        info = QLabel(
            f"Current version: {self._current_version}<br>"
            f"New version: {self._release.version}<br>"
            f"{self._release.name}"
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info)

        # Release notes
        body = self._release.body.strip() or "No release notes were provided for this version."
        notes_browser = QTextBrowser()
        notes_browser.setOpenExternalLinks(False)
        notes_browser.setHtml(self._safe_html(body))
        notes_browser.setMinimumHeight(180)
        layout.addWidget(notes_browser)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_download = QPushButton("Download Update")
        btn_download.clicked.connect(self._on_download)
        btn_layout.addWidget(btn_download)

        btn_github = QPushButton("View on GitHub")
        btn_github.clicked.connect(self._on_view_github)
        btn_layout.addWidget(btn_github)

        btn_layout.addStretch()
        btn_later = QPushButton("Later")
        btn_later.clicked.connect(self.reject)
        btn_layout.addWidget(btn_later)

        layout.addLayout(btn_layout)

    def _safe_html(self, body: str) -> str:
        import html as html_mod
        escaped = html_mod.escape(body)
        paragraphs = []
        for line in escaped.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("## "):
                paragraphs.append(f"<h3>{line[3:]}</h3>")
            elif line.startswith("- "):
                paragraphs.append(f"<li>{line[2:]}</li>")
            elif line.startswith("  - "):
                paragraphs.append(f"<li style='margin-left:20px'>{line[4:]}</li>")
            else:
                paragraphs.append(f"<p>{line}</p>")
        return "".join(paragraphs)

    def _on_download(self) -> None:
        url = self._installer_asset or self._release.html_url
        QDesktopServices.openUrl(url)
        self.accept()

    def _on_view_github(self) -> None:
        QDesktopServices.openUrl(self._release.html_url)
        self.accept()


def show_up_to_date_dialog(parent, version: str) -> None:
    from PySide6.QtWidgets import QMessageBox
    QMessageBox.information(
        parent,
        "Up to Date",
        f"Video2PPTX is up to date.\n\nCurrent version: {version}",
    )


def show_check_failed_dialog(parent, message: str | None = None) -> None:
    from PySide6.QtWidgets import QMessageBox
    text = "Unable to check for updates.\n\nCheck your Internet connection and try again."
    if message:
        text += f"\n\nDetails: {message}"
    QMessageBox.warning(parent, "Update Check Failed", text)
