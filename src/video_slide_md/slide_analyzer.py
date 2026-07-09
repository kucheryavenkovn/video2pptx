# FILE: src/video_slide_md/slide_analyzer.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Analyze slide screenshot via LLM vision — extract visual description and on-screen text terms
#   SCOPE: Vision analysis of a single slide image, returns structured description + key terms
#   DEPENDS: llm_client, models
#   LINKS: M-SLIDE-ANALYZER
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   VISION_SYSTEM_PROMPT - system prompt for slide vision analysis
#   analyze_slide - main entry: image path + LlmClient → SlideAnalysis result
#   SlideAnalysis - dataclass with description, key_terms, raw_response
# END_MODULE_MAP

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from video_slide_md.llm_client import LlmClient
from video_slide_md.models import SlideSegment

# START_BLOCK_VISION_PROMPT
VISION_SYSTEM_PROMPT: str = """Ты — анализатор учебных слайдов. Внимательно изучи изображение слайда и верни структурированное описание.

Опиши:
1. ВСЕ тексты на слайде (заголовки, подписи, термины, формулы, код) — точно как написано
2. Что изображено (схемы, графики, диаграммы, картинки)
3. Тема/контекст слайда (о чём этот слайд?)

Формат ответа:
===
Тема: [краткая тема слайда]
Термины: [список ключевых терминов через запятую]
Текст на слайде: [точное воспроизведение всех текстов]
Визуальный контент: [описание что изображено]
Контекст: [дополнительный контекст для понимания содержимого]
===

Отвечай только в указанном формате, без лишних пояснений."""
# END_BLOCK_VISION_PROMPT


@dataclass
class SlideAnalysis:
    # START_CONTRACT: SlideAnalysis
    #   PURPOSE: Structured result of slide vision analysis
    #   INPUTS: { description: str, key_terms: list[str], raw_response: str }
    #   OUTPUTS: { SlideAnalysis }
    #   SIDE_EFFECTS: none
    #   LINKS: M-SLIDE-ANALYZER
    # END_CONTRACT: SlideAnalysis
    description: str
    key_terms: list[str]
    raw_response: str


def analyze_slide(
    seg: SlideSegment,
    image_path: str | Path,
    llm_client: LlmClient,
    slides_dir: str | Path | None = None,
) -> SlideAnalysis:
    # START_CONTRACT: analyze_slide
    #   PURPOSE: Analyze single slide image via LLM vision → structured description + terms
    #   INPUTS: {
    #       seg: SlideSegment — slide metadata for logging,
    #       image_path: str|Path — path to slide screenshot,
    #       llm_client: LlmClient — initialized LLM client,
    #       slides_dir: str|Path|None — if set, save description sidecar JSON here
    #   }
    #   OUTPUTS: SlideAnalysis with description, key_terms, raw_response
    #   SIDE_EFFECTS: may save sidecar JSON to disk, calls LLM vision API
    #   LINKS: M-SLIDE-ANALYZER
    # END_CONTRACT: analyze_slide

    path = Path(image_path)
    if not path.is_file():
        logger.error(
            f"[SlideAnalyzer][analyze_slide] Image not found | "
            f"slide=#{seg.index} path={path}"
        )
        raise FileNotFoundError(f"Slide image not found: {path}")

    logger.info(
        f"[SlideAnalyzer][analyze_slide] Analyzing slide | "
        f"slide=#{seg.index} image={path.name}"
    )

    # START_BLOCK_VISION_REQUEST
    prompt = (
        f"Проанализируй слайд #{seg.index} лекции "
        f"(таймкод: {_fmt_ts(seg.start)} – {_fmt_ts(seg.end)}):\n\n"
        f"Что изображено и написано на этом слайде? "
        f"Выпиши все ключевые термины точно как они написаны."
    )

    raw_response = llm_client.vision(path, prompt=prompt)
    # END_BLOCK_VISION_REQUEST

    # START_BLOCK_PARSE_RESPONSE
    analysis = _parse_vision_response(raw_response)
    # END_BLOCK_PARSE_RESPONSE

    # START_BLOCK_SAVE_SIDECAR
    if slides_dir:
        sidecar_path = Path(slides_dir) / f"slide_{seg.index:03d}_analysis.json"
        sidecar_data = {
            "slide_index": seg.index,
            "timestamp_range": {"start": seg.start, "end": seg.end},
            "description": analysis.description,
            "key_terms": analysis.key_terms,
            "raw_response": analysis.raw_response,
        }
        sidecar_path.write_text(json.dumps(sidecar_data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(
            f"[SlideAnalyzer][analyze_slide] Saved analysis sidecar | "
            f"slide=#{seg.index} path={sidecar_path}"
        )
    # END_BLOCK_SAVE_SIDECAR

    logger.info(
        f"[SlideAnalyzer][analyze_slide] Analysis complete | "
        f"slide=#{seg.index} description_len={len(analysis.description)} "
        f"terms={len(analysis.key_terms)}"
    )

    return analysis


def _parse_vision_response(raw: str) -> SlideAnalysis:
    # START_CONTRACT: _parse_vision_response
    #   PURPOSE: Parse structured vision response into SlideAnalysis dataclass
    #   INPUTS: { raw: str — LLM response in format:
    #       ===
    #       Тема: ...
    #       Термины: ...
    #       Текст на слайде: ...
    #       Визуальный контент: ...
    #       Контекст: ...
    #       ===
    #   }
    #   OUTPUTS: SlideAnalysis
    #   SIDE_EFFECTS: none
    #   LINKS: M-SLIDE-ANALYZER
    # END_CONTRACT: _parse_vision_response

    if not raw or not raw.strip():
        logger.warning("[SlideAnalyzer][_parse_vision_response] Empty response from LLM")
        return SlideAnalysis(
            description="No description available",
            key_terms=[],
            raw_response=raw or "",
        )

    # Extract the block between === markers
    content = raw
    if "===" in raw:
        parts = raw.split("===")
        if len(parts) >= 3:
            content = parts[1] if parts[0].strip() == "" else parts[-2]
        elif len(parts) >= 2:
            content = parts[-1]

    lines = content.strip().split("\n")
    description_parts: list[str] = []
    key_terms: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("Термины:") or line.startswith("Термины :"):
            terms_str = line.split(":", 1)[1].strip()
            key_terms = [t.strip() for t in terms_str.split(",") if t.strip()]
        elif line.startswith("Тема:") or line.startswith("Тема :"):
            description_parts.append(line)
        elif line.startswith("Текст на слайде:") or line.startswith("Текст на слайде :"):
            description_parts.append(line)
        elif line.startswith("Визуальный контент:") or line.startswith("Визуальный контент :"):
            description_parts.append(line)
        elif line.startswith("Контекст:") or line.startswith("Контекст :"):
            description_parts.append(line)

    description = "\n".join(description_parts) if description_parts else raw.strip()

    if not key_terms:
        logger.debug(
            "[SlideAnalyzer][_parse_vision_response] No terms parsed, using fallback"
        )

    return SlideAnalysis(
        description=description,
        key_terms=key_terms,
        raw_response=raw,
    )


def _fmt_ts(seconds: float) -> str:
    # START_CONTRACT: _fmt_ts
    #   PURPOSE: Format seconds to MM:SS timestamp string
    #   INPUTS: { seconds: float }
    #   OUTPUTS: str — format "M:SS"
    #   SIDE_EFFECTS: none
    #   LINKS: M-SLIDE-ANALYZER
    # END_CONTRACT: _fmt_ts

    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"
