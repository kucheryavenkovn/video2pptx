# FILE: src/video2pptx/application/identity.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Neutral application identity model — version, build info, repository coordinates.
#   SCOPE: ApplicationIdentity, BuildInfo, BuildType enum. Single source of truth for version metadata.
#   DEPENDS: packaging.version, video2pptx.__version__
#   LINKS: M-APP-IDENTITY, M-GUI-ABOUT
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ApplicationIdentity - application identity with version, build, repo, runtime info
#   BuildType - SOURCE / STANDALONE / INSTALLER
#   application_identity() - cached global identity instance
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Initial identity model for Phase 17.0
# END_CHANGE_SUMMARY

from __future__ import annotations

import platform
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from packaging.version import Version

from video2pptx import __version__


class BuildType(str, Enum):
    SOURCE = "source"
    STANDALONE = "standalone"
    INSTALLER = "installer"


@dataclass(frozen=True, slots=True)
class BuildInfo:
    """Build-time metadata injected during packaging."""
    commit_sha: str = ""
    build_type: BuildType = BuildType.SOURCE
    packaging_tool: str = ""
    build_time: datetime | None = None


@dataclass(frozen=True, slots=True)
class ApplicationIdentity:
    """Canonical application identity — single source of all product metadata.

    Does not import PySide6, Qt, or any GUI module.
    Does not call `git` at runtime.
    """
    name: str = "Video2PPTX"
    description: str = "Video to Presentation"
    version_str: str = __version__
    version: Version = field(default_factory=lambda: Version(__version__))
    build: BuildInfo = field(default_factory=BuildInfo)
    repository_owner: str = "kucheryavenkovn"
    repository_name: str = "video2pptx"
    license_name: str = "MIT"
    author: str = "Vladimir Kucheryavenko"

    @property
    def repository_url(self) -> str:
        return f"https://github.com/{self.repository_owner}/{self.repository_name}"

    @property
    def release_url(self) -> str:
        return f"{self.repository_url}/releases/tag/v{self.version}"

    @property
    def is_frozen(self) -> bool:
        return getattr(sys, "frozen", False)

    def runtime_info(self) -> dict[str, Any]:
        """Collect runtime environment diagnostics (no secrets)."""
        info: dict[str, Any] = {
            "os": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "architecture": platform.machine(),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "is_frozen": self.is_frozen,
            "executable": str(Path(sys.executable).name),
        }
        return info

    def diagnostic_text(self) -> str:
        """Multi-line diagnostic string for About dialog and logs."""
        lines = [
            f"Application: {self.name}",
            f"Version: {self.version_str}",
            f"Build: {self.build.commit_sha or 'unknown'}",
            f"Build type: {self.build.build_type.value}",
        ]
        if self.build.packaging_tool:
            lines.append(f"Packaging: {self.build.packaging_tool}")
        if self.build.build_time:
            lines.append(f"Built: {self.build.build_time.isoformat()}")
        lines.append("")
        lines.append(f"OS: {platform.system()} {platform.release()} ({platform.machine()})")
        lines.append(f"Python: {platform.python_version()} ({platform.python_implementation()})")
        lines.append(f"Frozen: {self.is_frozen}")
        return "\n".join(lines)


_IDENTITY: ApplicationIdentity | None = None


def application_identity() -> ApplicationIdentity:
    """Return cached global ApplicationIdentity singleton."""
    global _IDENTITY
    if _IDENTITY is None:
        build = _detect_build_info()
        _IDENTITY = ApplicationIdentity(build=build)
    return _IDENTITY


def _detect_build_info() -> BuildInfo:
    """Detect build info from environment and injected metadata."""
    build_type = BuildType.INSTALLER if getattr(sys, "frozen", False) else BuildType.SOURCE
    commit_sha = ""
    packaging_tool = ""
    build_time = None
    build_meta = _try_load_build_meta()
    if build_meta:
        commit_sha = build_meta.get("commit_sha", "")
        build_type_str = build_meta.get("build_type", "")
        if build_type_str:
            try:
                build_type = BuildType(build_type_str)
            except ValueError:
                pass
        packaging_tool = build_meta.get("packaging_tool", "")
        build_time_str = build_meta.get("build_time", "")
        if build_time_str:
            try:
                from datetime import datetime
                build_time = datetime.fromisoformat(build_time_str)
            except (ValueError, TypeError):
                pass
    return BuildInfo(
        commit_sha=commit_sha,
        build_type=build_type,
        packaging_tool=packaging_tool,
        build_time=build_time,
    )


def _try_load_build_meta() -> dict[str, str]:
    """Try to import generated build_meta module (may not exist in dev mode)."""
    try:
        from video2pptx.build_meta import BUILD_META  # type: ignore[import-untyped]
        return dict(BUILD_META)
    except (ImportError, ModuleNotFoundError, AttributeError):
        return {}
