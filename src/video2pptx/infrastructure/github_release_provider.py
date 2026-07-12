# FILE: src/video2pptx/infrastructure/github_release_provider.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: GitHub Releases API client — fetch releases, parse into ReleaseInfo.
#   SCOPE: GitHubReleaseProvider. No Qt, no GUI. Uses httpx for HTTP.
#   DEPENDS: httpx, packaging.version, M-APP-IDENTITY
#   LINKS: M-UPDATE-CHECKER
#   ROLE: INTEGRATION
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   GitHubReleaseProvider - fetches releases from GitHub Releases API
# END_MODULE_MAP

from __future__ import annotations

from video2pptx.application.update_service import ReleaseAsset, ReleaseInfo, normalize_tag


class GitHubReleaseProvider:
    API_BASE = "https://api.github.com"

    def __init__(self, owner: str, repo: str, timeout: float = 15.0) -> None:
        self._owner = owner
        self._repo = repo
        self._timeout = timeout

    @property
    def api_url(self) -> str:
        return f"{self.API_BASE}/repos/{self._owner}/{self._repo}/releases"

    def fetch_releases(self) -> list[ReleaseInfo]:
        import httpx
        response = httpx.get(self.api_url, timeout=self._timeout, follow_redirects=True)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise ValueError(f"Expected list, got {type(data).__name__}")
        return [self._parse_release(item) for item in data]

    def _parse_release(self, item: dict) -> ReleaseInfo:
        tag_name: str = item.get("tag_name", "")
        version = normalize_tag(tag_name)
        if version is None:
            raise ValueError(f"Invalid version tag: {tag_name}")
        assets_raw: list[dict] = item.get("assets", []) or []
        assets = tuple(
            ReleaseAsset(
                name=a.get("name", ""),
                browser_download_url=a.get("browser_download_url", ""),
                size=a.get("size", 0),
            )
            for a in assets_raw
        )
        return ReleaseInfo(
            tag_name=tag_name,
            version=version,
            name=item.get("name", "") or "",
            body=item.get("body", "") or "",
            html_url=item.get("html_url", ""),
            prerelease=bool(item.get("prerelease", False)),
            draft=bool(item.get("draft", False)),
            assets=assets,
        )
