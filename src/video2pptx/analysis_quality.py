# FILE: src/video2pptx/analysis_quality.py
# VERSION: 1.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Product analysis-quality presets mapping to analysis_max_side (Qt-free)
#   SCOPE: Preset enum, UI labels, value mapping, product-range validation, UNSET override sentinel
#   DEPENDS: none (stdlib only)
#   LINKS: M-ANALYSIS-QUALITY, M-ANALYSIS-SCALE, Phase-20
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   AnalysisQualityPreset - FAST / DETAILED / NATIVE / CUSTOM
#   NEW_PROJECT_ANALYSIS_MAX_SIDE - explicit default for new projects (480)
#   ANALYSIS_MAX_SIDE_MIN / MAX - product bounds for project/CLI (240-2160)
#   UNSET - explicit "override absent" sentinel for application layer
#   validate_analysis_max_side - single product validator (None or int in range)
#   validate_custom_max_side - alias requiring int (no None)
#   preset_from_max_side / max_side_from_preset - UI mapping
#   parse_cli_analysis_max_side_token - parse "native"|digits for CLI
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.1.0 - Unified product validator + UNSET + CLI token parse (correction cycle)
# END_CHANGE_SUMMARY

from __future__ import annotations

from enum import Enum
from typing import Any

# Product default for *new* projects only (not legacy missing-field load).
NEW_PROJECT_ANALYSIS_MAX_SIDE: int = 480

# Product bounds for project.json / GUI / CLI (not internal Phase 19 scale tests).
ANALYSIS_MAX_SIDE_MIN: int = 240
ANALYSIS_MAX_SIDE_MAX: int = 2160

FAST_ANALYSIS_MAX_SIDE: int = 480
DETAILED_ANALYSIS_MAX_SIDE: int = 720


class UnsetType:
    """Sentinel: override not provided (use project value). Distinct from None (native)."""

    __slots__ = ()

    def __repr__(self) -> str:
        return "UNSET"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, UnsetType)


UNSET = UnsetType()


class AnalysisQualityPreset(str, Enum):
    """User-facing analysis quality modes. Domain still stores int | None."""

    FAST = "fast"
    DETAILED = "detailed"
    NATIVE = "native"
    CUSTOM = "custom"


PRESET_UI_LABELS: dict[AnalysisQualityPreset, str] = {
    AnalysisQualityPreset.FAST: "Быстрый — рекомендуется",
    AnalysisQualityPreset.DETAILED: "Повышенная детализация — экспериментально",
    AnalysisQualityPreset.NATIVE: "Исходная детализация",
    AnalysisQualityPreset.CUSTOM: "Пользовательский режим",
}

PRESET_DESCRIPTIONS: dict[AnalysisQualityPreset, str] = {
    AnalysisQualityPreset.FAST: (
        "Ускоряет поиск смены слайдов. Уменьшение применяется только во время "
        "анализа. Изображения в презентации сохраняются в исходном качестве."
    ),
    AnalysisQualityPreset.DETAILED: (
        "Анализирует более крупные кадры. Может работать медленнее. "
        "Режим пока не имеет такого же объёма benchmark evidence, как быстрый режим."
    ),
    AnalysisQualityPreset.NATIVE: (
        "Не уменьшает кадры при анализе. Работает медленнее и сохраняет "
        "историческое поведение детектора."
    ),
    AnalysisQualityPreset.CUSTOM: (
        "Задаёт максимальную сторону кадра только для анализа смены слайдов."
    ),
}

FULL_RES_NOTICE: str = (
    "Настройка влияет только на поиск смены слайдов.\n"
    "Скриншоты и изображения в PPTX сохраняются в исходном разрешении."
)

ANALYSIS_QUALITY_CHANGE_WARNING: str = (
    "Изменение качества анализа требует повторного поиска слайдов.\n"
    "Результаты последующих этапов будут пересозданы."
)


def validate_analysis_max_side(value: Any, *, allow_none: bool = True) -> int | None:
    # START_CONTRACT: validate_analysis_max_side
    #   PURPOSE: Single product-range validator for project/CLI analysis_max_side
    #   INPUTS: { value, allow_none }
    #   OUTPUTS: { int|None — None only when allow_none and value is None }
    #   SIDE_EFFECTS: raises ValueError on invalid types/range (no silent clamp)
    #   LINKS: M-ANALYSIS-QUALITY
    # END_CONTRACT: validate_analysis_max_side
    if value is None:
        if allow_none:
            return None
        raise ValueError("analysis_max_side cannot be null in this context")
    # Reject bool (subclass of int), float, str, etc.
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"analysis_max_side must be null or an integer in "
            f"[{ANALYSIS_MAX_SIDE_MIN}, {ANALYSIS_MAX_SIDE_MAX}], got {type(value).__name__}"
        )
    if value < ANALYSIS_MAX_SIDE_MIN or value > ANALYSIS_MAX_SIDE_MAX:
        raise ValueError(
            f"analysis_max_side must be in [{ANALYSIS_MAX_SIDE_MIN}, {ANALYSIS_MAX_SIDE_MAX}], "
            f"got {value}"
        )
    return value


def validate_custom_max_side(value: object) -> int:
    """Require int in product range (no None)."""
    result = validate_analysis_max_side(value, allow_none=False)
    assert result is not None
    return result


def preset_from_max_side(value: int | None) -> AnalysisQualityPreset:
    if value is None:
        return AnalysisQualityPreset.NATIVE
    if value == FAST_ANALYSIS_MAX_SIDE:
        return AnalysisQualityPreset.FAST
    if value == DETAILED_ANALYSIS_MAX_SIDE:
        return AnalysisQualityPreset.DETAILED
    return AnalysisQualityPreset.CUSTOM


def max_side_from_preset(
    preset: AnalysisQualityPreset,
    custom_value: int | None = None,
) -> int | None:
    if preset is AnalysisQualityPreset.FAST:
        return FAST_ANALYSIS_MAX_SIDE
    if preset is AnalysisQualityPreset.DETAILED:
        return DETAILED_ANALYSIS_MAX_SIDE
    if preset is AnalysisQualityPreset.NATIVE:
        return None
    if preset is AnalysisQualityPreset.CUSTOM:
        if custom_value is None:
            raise ValueError("custom preset requires custom_value")
        return validate_custom_max_side(custom_value)
    raise ValueError(f"Unknown preset: {preset}")


def parse_cli_analysis_max_side_token(token: str) -> int | None:
    # START_CONTRACT: parse_cli_analysis_max_side_token
    #   PURPOSE: Parse CLI token "native" or integer string into product analysis_max_side
    #   INPUTS: { token: str }
    #   OUTPUTS: { int|None — None means explicit native }
    #   SIDE_EFFECTS: raises ValueError on invalid token
    # END_CONTRACT: parse_cli_analysis_max_side_token
    raw = (token or "").strip()
    if not raw:
        raise ValueError("analysis_max_side token is empty")
    if raw.lower() == "native":
        return None
    # Reject floats like "480.0"
    if any(c in raw for c in ".eE+"):
        raise ValueError(f"analysis_max_side must be 'native' or an integer, got {token!r}")
    try:
        n = int(raw, 10)
    except ValueError as exc:
        raise ValueError(
            f"analysis_max_side must be 'native' or an integer "
            f"[{ANALYSIS_MAX_SIDE_MIN}-{ANALYSIS_MAX_SIDE_MAX}], got {token!r}"
        ) from exc
    return validate_analysis_max_side(n, allow_none=False)
