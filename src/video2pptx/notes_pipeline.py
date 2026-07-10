# FILE: src/video2pptx/notes_pipeline.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Post-process notes pipeline — load slides.json, align subtitles, optional vision context, save enriched slides.json
#   SCOPE: ONE function: run_notes(). Loads existing slides.json (no video re-decode), parses SRT/VTT, aligns cues to segments, runs notes_processor, optionally runs slide_analyzer for visual context, saves updated slides.json.
#   DEPENDS: models, subtitles, notes_processor, slide_analyzer, llm_client
#   LINKS: M-NOTES
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   run_notes - main entry: slides.json + subtitles path + options → enriched slides.json with cleaned notes
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

from loguru import logger

from video2pptx.config import LlmConfig
from video2pptx.models import SlidesDocument
from video2pptx.notes_processor import process_notes
from video2pptx.subtitles import parse_subtitles, align_cues_to_segments


def run_notes(
    slides_json: Path,
    subtitles_path: Path | None,
    slides_dir: Path | None,
    notes_mode: str = "basic",
    llm_config: LlmConfig | None = None,
) -> SlidesDocument:
    # START_CONTRACT: run_notes
    #   PURPOSE: Load slides.json, align subtitles, build context-aware notes, save enriched document
    #   INPUTS: {
    #       slides_json: Path — path to existing slides.json,
    #       subtitles_path: Path | None — optional SRT/VTT file,
    #       slides_dir: Path | None — directory with slide screenshots for vision context,
    #       notes_mode: str — "basic" or "llm",
    #       llm_config: LlmConfig | None — LLM config for vision analysis (required in llm mode)
    #   }
    #   OUTPUTS: SlidesDocument — updated slides.json saved to disk
    #   SIDE_EFFECTS: overwrites slides.json, reads screenshots if vision context requested
    #   LINKS: M-NOTES
    # END_CONTRACT: run_notes

    # START_BLOCK_LOAD_DOCUMENT
    doc = SlidesDocument.model_validate_json(slides_json.read_text(encoding="utf-8"))
    logger.info(f"[Notes][run_notes] Document loaded | slides={len(doc.slides)}")
    # END_BLOCK_LOAD_DOCUMENT

    # START_BLOCK_ALIGN_SUBTITLES
    if subtitles_path is not None:
        raw = subtitles_path.read_text(encoding="utf-8")
        cues = parse_subtitles(raw)
        align_cues_to_segments(doc.slides, cues)
        logger.info(f"[Notes][run_notes] Subtitles aligned | cues={len(cues)}")
    else:
        logger.info("[Notes][run_notes] No subtitles provided, skipping alignment")
    # END_BLOCK_ALIGN_SUBTITLES

    # START_BLOCK_PROCESS_NOTES
    llm_client = None
    if notes_mode == "llm" and llm_config is not None:
        from video2pptx.llm_client import LlmClient
        logger.info("[Notes][run_notes] LLM mode — initializing client")
        llm_client = LlmClient(llm_config)

    try:
        for i, seg in enumerate(doc.slides):
            desc = seg.llm_description
            ctx = seg.slide_context

            if notes_mode == "llm" and llm_client is not None:
                # Vision analysis if not yet done
                if not desc and slides_dir is not None and seg.image:
                    from video2pptx.paths import resolve_artifact_path
                    img_path = resolve_artifact_path(slides_dir, seg.image)
                    if img_path.is_file():
                        logger.info(f"[Notes][run_notes] Vision analysis | slide={i + 1}/{len(doc.slides)}")
                        try:
                            raw = llm_client.vision(str(img_path), prompt=llm_config.vision_prompt)
                            from video2pptx.slide_analyzer import _parse_vision_response
                            analysis = _parse_vision_response(raw)
                            desc = analysis.description
                            ctx = ", ".join(analysis.key_terms)
                            seg.llm_description = desc
                            seg.slide_context = ctx
                        except Exception as e:
                            logger.warning(f"[Notes][run_notes] Vision failed for slide {i + 1}: {e}")

            cleaned = process_notes(seg, mode=notes_mode, llm_client=llm_client,
                                    slide_description=desc, slide_context=ctx)
            seg.transcript = cleaned
    finally:
        if llm_client is not None:
            try:
                if llm_config and llm_config.unload_when_done:
                    llm_client.unload_model()
                llm_client.close()
                logger.info("[Notes][run_notes] LLM client closed")
            except Exception as e:
                logger.warning(f"[Notes][run_notes] Client cleanup failed: {e}")

    logger.info(f"[Notes][run_notes] Notes processed | mode={notes_mode} slides={len(doc.slides)}")
    # END_BLOCK_PROCESS_NOTES

    # START_BLOCK_SAVE
    slides_json.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    logger.info(f"[Notes][run_notes] Enriched document saved | path={slides_json}")
    # END_BLOCK_SAVE

    return doc
