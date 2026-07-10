# FILE: src/video2pptx/domain/artifacts.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Portable relative-path reference to a project artifact (slide image, deck, report).
#   SCOPE: ArtifactRef with POSIX normalization, traversal rejection, resolve, legacy migration
#   DEPENDS: video2pptx.domain.errors
#   LINKS: M-DOMAIN-VALUE
#   ROLE: TYPES
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   ArtifactRef - frozen validated relative path to a project artifact
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Initial ArtifactRef implementation
# END_CHANGE_SUMMARY

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from video2pptx.domain.errors import ValidationError


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    """Immutable reference to a project artifact stored as a portable relative path.

    The path is always normalized to POSIX separators.
    Absolute paths, empty paths, and parent-traversal (``..``) are rejected.
    """

    relative_path: PurePosixPath

    def __post_init__(self) -> None:
        if not self.relative_path or str(self.relative_path) == ".":
            raise ValidationError("ArtifactRef path must not be empty")
        parts = self.relative_path.parts
        for part in parts:
            if part == "..":
                raise ValidationError(
                    f"ArtifactRef must not contain parent traversal: {self.relative_path}"
                )
        if self.relative_path.is_absolute():
            raise ValidationError(
                f"ArtifactRef must not be absolute: {self.relative_path}"
            )

    @classmethod
    def parse(cls, raw: str | Path) -> ArtifactRef:
        """Construct an ArtifactRef from a raw string or Path.

        - Windows backslashes are normalized to forward slashes.
        - Double prefixes like ``slides/slides/`` are detected and rejected.
        - Parent traversal (``..``) is rejected.
        - Absolute paths are rejected.
        """
        if not raw or not str(raw).strip():
            raise ValidationError("ArtifactRef path must not be empty")

        text = str(raw).replace("\\", "/").strip()

        if PurePosixPath(text).is_absolute():
            raise ValidationError(f"ArtifactRef must not be absolute: {text}")

        if len(text) >= 2 and text[1] == ":":
            raise ValidationError(f"ArtifactRef must not be absolute (drive letter): {text}")

        normalized = PurePosixPath(text)
        parts = normalized.parts

        if any(part == ".." for part in parts):
            raise ValidationError(
                f"ArtifactRef must not contain parent traversal: {text}"
            )

        if len(parts) >= 2 and parts[0] == parts[1]:
            raise ValidationError(
                f"ArtifactRef double-prefix detected: {text}"
            )

        return cls(normalized)

    def as_posix(self) -> str:
        """Return the portable POSIX string representation."""
        return self.relative_path.as_posix()

    def resolve(self, project_root: str | Path) -> Path:
        """Resolve this reference against a project root directory."""
        return Path(project_root) / self.as_posix()

    def within(self, directory: str | Path) -> ArtifactRef:
        """Return a new ArtifactRef prefixed by *directory*."""
        return ArtifactRef.parse(
            PurePosixPath(str(directory).replace("\\", "/"))
            / self.relative_path
        )

    def __str__(self) -> str:
        return self.as_posix()


def migrate_legacy_artifact(
    raw: str,
    project_root: str | Path,
) -> ArtifactRef:
    """Attempt to convert a legacy image path to a portable ArtifactRef.

    Strategy:
        1. If the raw path is already a valid relative POSIX path, parse it.
        2. If it is an absolute path inside the project root, compute the relative portion.
        3. If it is an absolute path outside the project root, raise ValidationError.
        4. If it is a bare filename like ``slide_001.png`` and a ``slides/`` directory
           exists in the project root, prepend ``slides/``.
        5. Otherwise attempt a direct parse.
    """
    if not raw or not raw.strip():
        raise ValidationError("Cannot migrate empty artifact path")

    text = str(raw).strip()
    root = Path(project_root)

    abs_path = Path(text)
    if abs_path.is_absolute():
        try:
            rel = abs_path.relative_to(root)
            return ArtifactRef.parse(rel)
        except ValueError:
            raise ValidationError(
                f"Legacy artifact path is outside project root: {raw}"
            ) from None

    normalized = text.replace("\\", "/")
    posix_path = PurePosixPath(normalized)

    if len(posix_path.parts) == 1 and not posix_path.is_absolute():
        candidate = root / "slides" / normalized
        if candidate.is_file():
            return ArtifactRef.parse(f"slides/{normalized}")

    return ArtifactRef.parse(normalized)
