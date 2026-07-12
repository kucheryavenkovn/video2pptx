# FILE: tests/test_update_service.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for UpdateService, normalize_tag, UpdateChannel filtering
#   DEPENDS: M-UPDATE-CHECKER
#   ROLE: TEST
#   MAP_MODE: NONE
# END_MODULE_CONTRACT

from __future__ import annotations

from packaging.version import Version

from video2pptx.application.update_service import (
    ReleaseInfo,
    UpdateChannel,
    UpdateCheckResultType,
    UpdateService,
    normalize_tag,
)


def _release(tag: str, prerelease: bool = False, draft: bool = False) -> ReleaseInfo:
    v = normalize_tag(tag)
    assert v is not None
    return ReleaseInfo(
        tag_name=tag,
        version=v,
        name=f"Release {v}",
        body="",
        html_url=f"https://github.com/test/repo/releases/tag/{tag}",
        prerelease=prerelease,
        draft=draft,
    )


class TestNormalizeTag:
    def test_strip_v_prefix(self) -> None:
        v = normalize_tag("v0.5.0")
        assert v == Version("0.5.0")

    def test_no_prefix(self) -> None:
        v = normalize_tag("0.5.0")
        assert v == Version("0.5.0")

    def test_prerelease(self) -> None:
        v = normalize_tag("v0.6.0b1")
        assert v == Version("0.6.0b1")
        assert v.is_prerelease

    def test_rc(self) -> None:
        v = normalize_tag("v1.0.0rc1")
        assert v == Version("1.0.0rc1")
        assert v.is_prerelease

    def test_invalid_tag_returns_none(self) -> None:
        assert normalize_tag("not-a-version") is None

    def test_empty_tag(self) -> None:
        assert normalize_tag("") is None


class TestUpdateService:
    def test_no_releases(self) -> None:
        svc = UpdateService(Version("0.5.0"))
        result = svc.check([])
        assert result.result_type == UpdateCheckResultType.NO_RELEASES

    def test_current_is_latest(self) -> None:
        svc = UpdateService(Version("0.5.0"))
        result = svc.check([_release("v0.5.0")])
        assert result.result_type == UpdateCheckResultType.UP_TO_DATE

    def test_latest_greater(self) -> None:
        svc = UpdateService(Version("0.5.0"))
        result = svc.check([_release("v0.6.0"), _release("v0.5.0")])
        assert result.result_type == UpdateCheckResultType.UPDATE_AVAILABLE
        assert result.latest_release is not None
        assert result.latest_release.version == Version("0.6.0")

    def test_latest_less(self) -> None:
        svc = UpdateService(Version("0.7.0"))
        result = svc.check([_release("v0.6.0")])
        assert result.result_type == UpdateCheckResultType.UP_TO_DATE

    def test_multiple_releases(self) -> None:
        svc = UpdateService(Version("0.5.0"))
        releases = [_release("v0.4.0"), _release("v0.5.0"), _release("v0.6.0"), _release("v0.3.0")]
        result = svc.check(releases)
        assert result.result_type == UpdateCheckResultType.UPDATE_AVAILABLE
        assert result.latest_release.version == Version("0.6.0")

    def test_invalid_tag_ignored(self) -> None:
        svc = UpdateService(Version("0.5.0"))
        valid_releases = [_release("v0.6.0")]
        result = svc.check(valid_releases)
        assert result.result_type == UpdateCheckResultType.UPDATE_AVAILABLE

    def test_draft_ignored(self) -> None:
        svc = UpdateService(Version("0.5.0"))
        result = svc.check([_release("v0.6.0", draft=True), _release("v0.5.0")])
        assert result.result_type == UpdateCheckResultType.UP_TO_DATE

    def test_stable_ignores_prerelease(self) -> None:
        svc = UpdateService(Version("0.5.0"), channel=UpdateChannel.STABLE)
        result = svc.check([_release("v0.6.0b1", prerelease=True), _release("v0.5.0")])
        assert result.result_type == UpdateCheckResultType.UP_TO_DATE

    def test_beta_includes_prerelease(self) -> None:
        svc = UpdateService(Version("0.5.0"), channel=UpdateChannel.BETA)
        result = svc.check([_release("v0.6.0b1", prerelease=True), _release("v0.5.0")])
        assert result.result_type == UpdateCheckResultType.UPDATE_AVAILABLE
        assert result.latest_release.version == Version("0.6.0b1")

    def test_beta_picks_latest_prerelease(self) -> None:
        svc = UpdateService(Version("0.5.0"), channel=UpdateChannel.BETA)
        result = svc.check([
            _release("v0.6.0b1", prerelease=True),
            _release("v0.6.0b2", prerelease=True),
            _release("v0.5.0"),
        ])
        assert result.result_type == UpdateCheckResultType.UPDATE_AVAILABLE
        assert result.latest_release.version == Version("0.6.0b2")

    def test_0_10_0_greater_than_0_9_0(self) -> None:
        svc = UpdateService(Version("0.9.0"))
        result = svc.check([_release("v0.10.0")])
        assert result.result_type == UpdateCheckResultType.UPDATE_AVAILABLE

    def test_stable_newer_than_prerelease(self) -> None:
        svc = UpdateService(Version("0.6.0b1"), channel=UpdateChannel.STABLE)
        result = svc.check([_release("v0.6.0b2", prerelease=True), _release("v0.6.0")])
        # Stable channel: prerelease ignored, so 0.6.0 > 0.6.0b1
        assert result.result_type == UpdateCheckResultType.UPDATE_AVAILABLE
        assert result.latest_release.version == Version("0.6.0")

    def test_beta_sees_stable_and_prerelease(self) -> None:
        svc = UpdateService(Version("0.5.0"), channel=UpdateChannel.BETA)
        result = svc.check([
            _release("v0.6.0b1", prerelease=True),
            _release("v0.6.0"),
        ])
        assert result.result_type == UpdateCheckResultType.UPDATE_AVAILABLE
        assert result.latest_release.version == Version("0.6.0")
