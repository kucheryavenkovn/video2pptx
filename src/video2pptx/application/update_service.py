# FILE: src/video2pptx/application/update_service.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Application-layer update check logic — no Qt, no GitHub-specific imports.
#   SCOPE: UpdateChannel enum, ReleaseInfo, UpdateService (compare versions, filter by channel)
#   DEPENDS: packaging.version, M-APP-IDENTITY
#   LINKS: M-UPDATE-CHECKER
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   UpdateChannel - STABLE / BETA enum
#   ReleaseInfo - release metadata from provider
#   UpdateCheckResult - UPDATE_AVAILABLE / UP_TO_DATE / CHECK_FAILED / NO_RELEASES
#   UpdateService - compare version, filter releases, determine if update available
# END_MODULE_MAP

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum

from packaging.version import InvalidVersion, Version


class UpdateChannel(str, Enum):
    STABLE = "stable"
    BETA = "beta"


class UpdateCheckResultType(str, Enum):
    UPDATE_AVAILABLE = "update_available"
    UP_TO_DATE = "up_to_date"
    CHECK_FAILED = "check_failed"
    NO_RELEASES = "no_releases"


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    tag_name: str
    version: Version
    name: str
    body: str
    html_url: str
    prerelease: bool
    draft: bool
    assets: tuple[ReleaseAsset, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    name: str
    browser_download_url: str
    size: int


@dataclass(frozen=True, slots=True)
class UpdateCheckResult:
    result_type: UpdateCheckResultType
    current_version: Version = field(default_factory=lambda: Version("0.0.0"))
    latest_release: ReleaseInfo | None = None
    error_message: str = ""


class UpdateService:
    def __init__(self, current_version: Version, channel: UpdateChannel = UpdateChannel.STABLE) -> None:
        self._current = current_version
        self._channel = channel

    @property
    def current_version(self) -> Version:
        return self._current

    @property
    def channel(self) -> UpdateChannel:
        return self._channel

    def check(self, releases: Sequence[ReleaseInfo]) -> UpdateCheckResult:
        filtered = self._filter_releases(releases)
        if not filtered:
            return UpdateCheckResult(
                result_type=UpdateCheckResultType.NO_RELEASES,
                current_version=self._current,
            )
        latest = max(filtered, key=lambda r: r.version)
        if latest.version > self._current:
            return UpdateCheckResult(
                result_type=UpdateCheckResultType.UPDATE_AVAILABLE,
                current_version=self._current,
                latest_release=latest,
            )
        return UpdateCheckResult(
            result_type=UpdateCheckResultType.UP_TO_DATE,
            current_version=self._current,
            latest_release=latest,
        )

    def _filter_releases(self, releases: Sequence[ReleaseInfo]) -> list[ReleaseInfo]:
        result: list[ReleaseInfo] = []
        for r in releases:
            if r.draft:
                continue
            if self._channel == UpdateChannel.STABLE and r.prerelease:
                continue
            result.append(r)
        return result


def normalize_tag(tag: str) -> Version | None:
    raw = tag.lstrip("v")
    try:
        return Version(raw)
    except InvalidVersion:
        return None
