# FILE: tests/test_github_release_provider.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Tests for GitHubReleaseProvider with mocked HTTP transport
#   DEPENDS: M-UPDATE-CHECKER
#   ROLE: TEST
#   MAP_MODE: NONE
# END_MODULE_CONTRACT

from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest
from packaging.version import Version

from video2pptx.infrastructure.github_release_provider import GitHubReleaseProvider


def _mock_response(data, status=200):
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    if status >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError("error", request=MagicMock(), response=resp)
    return resp


def _release_item(tag: str, name: str = "", prerelease: bool = False, draft: bool = False,
                  body: str = "", assets: list | None = None) -> dict:
    return {
        "tag_name": tag,
        "name": name or f"Release {tag}",
        "body": body,
        "html_url": f"https://github.com/test/repo/releases/tag/{tag}",
        "prerelease": prerelease,
        "draft": draft,
        "assets": assets or [],
    }


class TestGitHubReleaseProvider:
    def setup_method(self) -> None:
        self.provider = GitHubReleaseProvider("testowner", "testrepo", timeout=5.0)

    @patch("httpx.get")
    def test_successful_fetch(self, mock_get) -> None:
        mock_get.return_value = _mock_response([
            _release_item("v0.6.0", "Version 0.6.0"),
            _release_item("v0.5.0", "Version 0.5.0"),
        ])
        releases = self.provider.fetch_releases()
        assert len(releases) == 2
        assert releases[0].tag_name == "v0.6.0"
        assert releases[0].version == Version("0.6.0")
        assert releases[1].tag_name == "v0.5.0"

    @patch("httpx.get")
    def test_403_error(self, mock_get) -> None:
        mock_get.return_value = _mock_response({"message": "Forbidden"}, status=403)
        with pytest.raises(httpx.HTTPStatusError):
            self.provider.fetch_releases()

    @patch("httpx.get")
    def test_404_error(self, mock_get) -> None:
        mock_get.return_value = _mock_response({"message": "Not Found"}, status=404)
        with pytest.raises(httpx.HTTPStatusError):
            self.provider.fetch_releases()

    @patch("httpx.get")
    def test_429_rate_limit(self, mock_get) -> None:
        mock_get.return_value = _mock_response({"message": "Rate limit"}, status=429)
        with pytest.raises(httpx.HTTPStatusError):
            self.provider.fetch_releases()

    @patch("httpx.get")
    def test_500_error(self, mock_get) -> None:
        mock_get.return_value = _mock_response({"message": "Server error"}, status=500)
        with pytest.raises(httpx.HTTPStatusError):
            self.provider.fetch_releases()

    @patch("httpx.get")
    def test_timeout(self, mock_get) -> None:
        mock_get.side_effect = httpx.TimeoutException("timeout", request=MagicMock())
        with pytest.raises(httpx.TimeoutException):
            self.provider.fetch_releases()

    @patch("httpx.get")
    def test_dns_error(self, mock_get) -> None:
        mock_get.side_effect = httpx.ConnectError("DNS resolution failed")
        with pytest.raises(httpx.ConnectError):
            self.provider.fetch_releases()

    @patch("httpx.get")
    def test_invalid_json(self, mock_get) -> None:
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = resp
        with pytest.raises(ValueError):
            self.provider.fetch_releases()

    @patch("httpx.get")
    def test_malformed_release(self, mock_get) -> None:
        mock_get.return_value = _mock_response([
            {"tag_name": "not-a-version", "name": "bad", "prerelease": False, "draft": False, "assets": []},
        ])
        with pytest.raises(ValueError, match="Invalid version tag"):
            self.provider.fetch_releases()

    @patch("httpx.get")
    def test_empty_assets(self, mock_get) -> None:
        mock_get.return_value = _mock_response([
            _release_item("v0.5.0", assets=[]),
        ])
        releases = self.provider.fetch_releases()
        assert len(releases) == 1
        assert releases[0].assets == ()

    @patch("httpx.get")
    def test_installer_asset_present(self, mock_get) -> None:
        assets = [
            {"name": "Video2PPTX-0.6.0-Setup-x64.exe", "browser_download_url": "https://example.com/setup.exe", "size": 50000000},
            {"name": "Video2PPTX-0.6.0-portable-x64.zip", "browser_download_url": "https://example.com/portable.zip", "size": 40000000},
        ]
        mock_get.return_value = _mock_response([
            _release_item("v0.6.0", assets=assets),
        ])
        releases = self.provider.fetch_releases()
        assert len(releases[0].assets) == 2
        installer = [a for a in releases[0].assets if "Setup" in a.name]
        assert len(installer) == 1
        assert installer[0].browser_download_url == "https://example.com/setup.exe"
