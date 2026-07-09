# FILE: src/video2pptx/notes_processor.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Process raw subtitle transcript into clean speaker notes for PPTX export
#   SCOPE: Basic text cleanup + LLM rephrase pipeline with LM Studio integration
#   DEPENDS: models, loguru
#   LINKS: M-NOTES-PROCESSOR
#   ROLE: RUNTIME
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   process_notes - main entry: raw text + cues → clean speaker notes
#   SYSTEM_PROMPT_REPHRASE - system prompt template for LLM-based rephrasing
# END_MODULE_MAP

from __future__ import annotations

import re

from loguru import logger

from video2pptx.models import SlideSegment

# START_BLOCK_SYSTEM_PROMPT
SYSTEM_PROMPT_REPHRASE: str = """Ты — редактор расшифровок лекций. Преобразуй сырой текст субтитров в качественный текст докладчика для заметок к слайду презентации.

Правила:
1. Перефразируй каждое предложение, сохраняя точный смысл и все факты
2. Не сокращай объём — каждое предложение должно быть переписано, но все детали сохранены
3. Исправляй оговорки, повторы, обрывы фраз
4. Расставляй правильную пунктуацию, заглавные буквы
5. Сохраняй терминологию (1С, Python, API, имена собственные)
6. Разбивай на абзацы по смысловым блокам
7. Пиши грамотно, но сохраняй устный стиль лектора (не канцелярит)
8. Ничего не добавляй от себя — только то, что было в исходном тексте

Формат вывода: Только переписанный текст, без предисловий и пояснений."""
# END_BLOCK_SYSTEM_PROMPT

# START_BLOCK_LLM_REQUEST_TEMPLATE
LLM_REQUEST_TEMPLATE: str = """Отредактируй следующий текст субтитров лекции для слайда ({start} – {end}):

{text}

Перепиши каждое предложение, сохраняя смысл и объём. Только текст, без пояснений."""

LLM_REQUEST_TEMPLATE_WITH_CONTEXT: str = """Отредактируй следующий текст субтитров лекции для слайда ({start} – {end}).

Контекст слайда (термины, текст на слайде):
{slide_context}

Содержимое слайда:
{slide_description}

{subtitle_text}

Перепиши каждое предложение, сохраняя смысл и объём. Исправляй оговорки, повторы, и неточности транскрипции, особенно в терминах, сверяясь с контекстом слайда. Только текст, без пояснений."""
# END_BLOCK_LLM_REQUEST_TEMPLATE


def process_notes(
    seg: SlideSegment,
    mode: str = "basic",
    llm_client=None,
    slide_description: str | None = None,
    slide_context: str | None = None,
) -> str:
    # START_CONTRACT: process_notes
    #   PURPOSE: Transform raw segment transcript into clean speaker notes
    #   INPUTS: {
    #       seg: SlideSegment — contains transcript + subtitle_cues,
    #       mode: str — "basic" (regex cleanup) or "llm" (AI rephrase),
    #       llm_client: optional LLM client for rephrase mode,
    #       slide_description: str | None — LLM vision description of slide,
    #       slide_context: str | None — key terms extracted from slide
    #   }
    #   OUTPUTS: str — cleaned speaker notes text
    #   SIDE_EFFECTS: none (in basic mode); LLM call in llm mode
    #   LINKS: M-NOTES-PROCESSOR
    # END_CONTRACT: process_notes

    raw = _build_raw_text(seg)

    if mode == "llm" and llm_client is not None:
        return _llm_rephrase(raw, seg, llm_client, slide_description=slide_description, slide_context=slide_context)

    return _basic_cleanup(raw)


def _build_raw_text(seg: SlideSegment) -> str:
    # START_CONTRACT: _build_raw_text
    #   PURPOSE: Build continuous raw text from cues or transcript
    #   INPUTS: { seg: SlideSegment }
    #   OUTPUTS: str
    #   SIDE_EFFECTS: none
    #   LINKS: M-NOTES-PROCESSOR
    # END_CONTRACT: _build_raw_text

    if seg.subtitle_cues:
        return " ".join(c.text.strip() for c in seg.subtitle_cues)
    return seg.transcript or ""


def _basic_cleanup(text: str) -> str:
    # START_CONTRACT: _basic_cleanup
    #   PURPOSE: Clean raw subtitle text: join fragments, fix punctuation, capitalize
    #   INPUTS: { text: str }
    #   OUTPUTS: str
    #   SIDE_EFFECTS: none
    #   LINKS: M-NOTES-PROCESSOR
    # END_CONTRACT: _basic_cleanup

    if not text:
        return ""

    # Collapse whitespace
    t = re.sub(r'\s+', ' ', text).strip()

    # Fix comma-space: ",word" → ", word"
    t = re.sub(r'([,.:;!?])([^\s\d])', r'\1 \2', t)

    # Fix space-before-punctuation: "word ," → "word,"
    t = re.sub(r'\s+([,.:;!?])', r'\1', t)

    # Remove leading punctuation artifacts
    t = re.sub(r'^[,.:;!?\s]+', '', t)

    # Capitalize first letter of each sentence
    t = re.sub(r'(^|[.!?]\s+)([а-яa-z])', lambda m: m.group(1) + m.group(2).upper(), t)

    # Capitalize first letter overall
    if t and t[0].islower():
        t = t[0].upper() + t[1:]

    # Remove orphan single-word lines caused by subtitle fragmentation
    # by joining short lines with their neighbors
    parts = t.split("\n")
    merged: list[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        word_count = len(p.split())
        if merged and word_count <= 3 and len(p) < 50:
            merged[-1] += " " + p
        else:
            merged.append(p)
    t = "\n".join(merged)

    # Deduplicate repeated adjacent words from SRT overlap
    t = re.sub(r'\b(\w+)\s+\1\b', r'\1', t, flags=re.IGNORECASE)
    t = re.sub(r'\b(\w{3,})\s+\1\s+\1\b', r'\1', t, flags=re.IGNORECASE)

    return t.strip()


def _llm_rephrase(
    text: str,
    seg: SlideSegment,
    client,
    slide_description: str | None = None,
    slide_context: str | None = None,
) -> str:
    # START_CONTRACT: _llm_rephrase
    #   PURPOSE: Send text to LLM for sentence-level rephrasing with optional slide context
    #   INPUTS: {
    #       text: str — raw transcript,
    #       seg: SlideSegment — for timestamp context,
    #       client: LLM client with .chat(messages) method,
    #       slide_description: str | None — vision description of slide content,
    #       slide_context: str | None — key terms from slide
    #   }
    #   OUTPUTS: str — rephrased text
    #   SIDE_EFFECTS: calls external LLM API
    #   LINKS: M-NOTES-PROCESSOR
    # END_CONTRACT: _llm_rephrase

    from video2pptx.pptx_export import _fmt_time

    start_str = _fmt_time(seg.start)
    end_str = _fmt_time(seg.end)

    # START_BLOCK_BUILD_PROMPT
    if slide_description or slide_context:
        prompt = LLM_REQUEST_TEMPLATE_WITH_CONTEXT.format(
            start=start_str,
            end=end_str,
            slide_context=slide_context or "(нет данных)",
            slide_description=slide_description or "(нет данных)",
            subtitle_text=text,
        )
        logger.info(
            f"[NotesProcessor][_llm_rephrase] Using context-enhanced prompt | "
            f"segment=#{seg.index} has_description={slide_description is not None} "
            f"has_context={slide_context is not None}"
        )
    else:
        prompt = LLM_REQUEST_TEMPLATE.format(start=start_str, end=end_str, text=text)
    # END_BLOCK_BUILD_PROMPT

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_REPHRASE},
        {"role": "user", "content": prompt},
    ]

    logger.info(
        f"[NotesProcessor][_llm_rephrase] Sending to LLM | "
        f"segment=#{seg.index} chars={len(text)}"
    )

    result = client.chat(messages, temperature=0.3, max_tokens=4096)

    logger.info(
        f"[NotesProcessor][_llm_rephrase] LLM response | "
        f"segment=#{seg.index} chars={len(result)}"
    )
    return result
