# FILE: src/video2pptx/gui/update_controller.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: GUI adapter for update checking — orchestrate HTTP fetch, service compare, dialog show.
#   SCOPE: UpdateController. Does NOT contain business logic — delegates to UpdateService.
#   DEPENDS: PySide6, M-UPDATE-CHECKER, M-APP-IDENTITY, M-GUI-APPCONFIG
#   LINKS: M-UPDATE-CHECKER
#   ROLE: UI_COMPONENT
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   UpdateController - QObject that orchestrates update checks and shows dialogs
# END_MODULE_MAP

from __future__ import annotations

from loguru import logger
from PySide6.QtCore import QObject, QTimer

from video2pptx.application.identity import application_identity
from video2pptx.application.update_service import (
    UpdateChannel,
    UpdateCheckResultType,
    UpdateService,
)
from video2pptx.gui.app_config import load_app_config
from video2pptx.gui.update_dialog import (
    UpdateAvailableDialog,
    show_check_failed_dialog,
    show_up_to_date_dialog,
)


class UpdateController(QObject):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._identity = application_identity()
        self._service: UpdateService | None = None
        self._provider = None

    def _ensure_service(self) -> UpdateService:
        if self._service is None:
            cfg = load_app_config()
            channel = UpdateChannel(cfg.update_channel) if cfg.update_channel else UpdateChannel.STABLE
            self._service = UpdateService(self._identity.version, channel)
        return self._service

    def _ensure_provider(self):
        if self._provider is None:
            from video2pptx.infrastructure.github_release_provider import GitHubReleaseProvider
            self._provider = GitHubReleaseProvider(
                owner=self._identity.repository_owner,
                repo=self._identity.repository_name,
            )
        return self._provider

    def schedule_startup_check(self, parent_window) -> None:
        cfg = load_app_config()
        if not cfg.check_updates_on_startup:
            logger.debug("[UpdateController] Startup update check disabled")
            return
        QTimer.singleShot(2000, lambda: self._run_startup_check(parent_window))

    def _run_startup_check(self, parent_window) -> None:
        try:
            provider = self._ensure_provider()
            releases = provider.fetch_releases()
            service = self._ensure_service()
            result = service.check(releases)
            if result.result_type == UpdateCheckResultType.UPDATE_AVAILABLE:
                dlg = UpdateAvailableDialog(result.latest_release, result.current_version, parent_window)
                dlg.exec()
            elif result.result_type == UpdateCheckResultType.UP_TO_DATE:
                logger.debug("[UpdateController] Startup check: up to date")
            elif result.result_type == UpdateCheckResultType.CHECK_FAILED:
                logger.warning("[UpdateController] Startup check failed | {}", result.error_message)
            elif result.result_type == UpdateCheckResultType.NO_RELEASES:
                logger.debug("[UpdateController] Startup check: no releases")
        except Exception as exc:
            logger.warning("[UpdateController] Startup check error | {}", exc)

    def manual_check(self, parent_window) -> None:
        try:
            provider = self._ensure_provider()
            releases = provider.fetch_releases()
            service = self._ensure_service()
            result = service.check(releases)
            if result.result_type == UpdateCheckResultType.UPDATE_AVAILABLE:
                dlg = UpdateAvailableDialog(result.latest_release, result.current_version, parent_window)
                dlg.exec()
            elif result.result_type == UpdateCheckResultType.UP_TO_DATE:
                show_up_to_date_dialog(parent_window, str(result.current_version))
            elif result.result_type == UpdateCheckResultType.CHECK_FAILED:
                show_check_failed_dialog(parent_window, result.error_message)
            elif result.result_type == UpdateCheckResultType.NO_RELEASES:
                show_check_failed_dialog(parent_window, "No releases found.")
        except Exception as exc:
            logger.error("[UpdateController] Manual check error | {}", exc)
            show_check_failed_dialog(parent_window, str(exc))
