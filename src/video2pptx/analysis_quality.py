# FILE: src/video2pptx/analysis_quality.py
# VERSION: 1.0.0
# START_MODULE_CONTRACT
#   PURPOSE: Product analysis-quality presets mapping to analysis_max_side (Qt-free)
#   SCOPE: Preset enum, UI labels, value mapping, custom range validation helpers
#   DEPENDS: none (stdlib only)
#   LINKS: M-ANALYSIS-QUALITY, M-ANALYSIS-SCALE, Phase-20
#   ROLE: UTILITY
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   AnalysisQualityPreset - FAST / DETAILED / NATIVE / CUSTOM
#   NEW_PROJECT_ANALYSIS_MAX_SIDE - explicit default for new projects (480)
#   ANALYSIS_MAX_SIDE_MIN / MAX - custom validation bounds
#   preset_from_max_side - map stored int|None → preset
#   max_side_from_preset - map preset (+ optional custom) → int|None
#   validate_custom_max_side - raise ValueError if out of range / bad type
#   PRESET_UI_LABELS - Russian product labels (no 480p/720p)
# END_MODULE_MAP
#
# START_CHANGE_SUMMARY
#   LAST_CHANGE: v1.0.0 - Phase 20 analysis quality presets
# END_CHANGE_SUMMARY

from __future__ import annotations

from enum import Enum

# Product default for *new* projects only (not legacy missing-field load).
NEW_PROJECT_ANALYSIS_MAX_SIDE: int = 480

# Custom analysis max-side bounds (pixels on longer side).
ANALYSIS_MAX_SIDE_MIN: int = 240
ANALYSIS_MAX_SIDE_MAX: int = 2160

# Preset fixed values (except CUSTOM / NATIVE).
FAST_ANALYSIS_MAX_SIDE: int = 480
DETAILED_ANALYSIS_MAX_SIDE: int = 720


class AnalysisQualityPreset(str, Enum):
    """User-facing analysis quality modes. Domain still stores int | None."""

    FAST = "fast"
    DETAILED = "detailed"
    NATIVE = "native"
    CUSTOM = "custom"


# UI labels — product language only (no 480p/720p).
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


def preset_from_max_side(value: int | None) -> AnalysisQualityPreset:
    # START_CONTRACT: preset_from_max_side
    #   PURPOSE: Recover UI preset from stored analysis_max_side
    #   INPUTS: { value: int|None }
    #   OUTPUTS: { AnalysisQualityPreset }
    # END_CONTRACT: preset_from_max_side
    if value is None:
        return AnalysisQualityPreset.NATIVE
    if value == FAST_ANALYSIS_MAX_SIDE:
        return AnalysisQualityPreset.FAST
    if value == DETAILED_ANALYSIS_MAX_SIDE:
        return AnalysisQualityPreset.DETAILED
    return AnalysisQualityPreset.CUSTOM


def validate_custom_max_side(value: object) -> int:
    # START_CONTRACT: validate_custom_max_side
    #   PURPOSE: Accept only int in [240, 2160]; reject bool/str/float/None/OOB
    #   INPUTS: { value: object }
    #   OUTPUTS: { int }
    #   SIDE_EFFECTS: raises ValueError on invalid input
    # END_CONTRACT: validate_custom_max_side
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(
            f"analysis_max_side must be an integer in "
            f"[{ANALYSIS_MAX_SIDE_MIN}, {ANALYSIS_MAX_SIDE_MAX}], got {type(value).__name__}"
        )
    if value < ANALYSIS_MAX_SIDE_MIN or value > ANALYSIS_MAX_SIDE_MAX:
        raise ValueError(
            f"analysis_max_side must be in [{ANALYSIS_MAX_SIDE_MIN}, {ANALYSIS_MAX_SIDE_MAX}], "
            f"got {value}"
        )
    return value


def max_side_from_preset(
    preset: AnalysisQualityPreset,
    custom_value: int | None = None,
) -> int | None:
    # START_CONTRACT: max_side_from_preset
    #   PURPOSE: Map preset (+ optional custom int) to analysis_max_side
    #   INPUTS: { preset, custom_value }
    #   OUTPUTS: { int|None }
    # END_CONTRACT: max_side_from_preset
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
