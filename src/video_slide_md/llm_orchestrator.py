# FILE: src/video_slide_md/llm_orchestrator.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Coordinate full LLM processing pipeline: load model, analyze all slides, rephrase transcript, unload model, save enriched slides.json
#   SCOPE: Orchestrate vision analysis + transcript correction for all slides in a document
#   DEPENDS: llm_client, slide_analyzer, notes_processor, models
#   LINKS: M-LLM-ORCHESTRATOR
#   ROLE: CORE_LOGIC
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   run_llm_pipeline - main entry: slides.json path → enriched slides.json
# END_MODULE_MAP

from __future__ import annotations

from pathlib import Path

from loguru import logger

from video_slide_md.config import LlmConfig
from video_slide_md.llm_client import LlmClient
from video_slide_md.models import SlidesDocument
from video_slide_md.notes_processor import process_notes
from video_slide_md.slide_analyzer import analyze_slide


def run_llm_pipeline(
    slides_path: str | Path,
    llm_config: LlmConfig,
    slides_dir: str | Path | None = None,
    output_path: str | Path | None = None,
) -> Path:
    # START_CONTRACT: run_llm_pipeline
    #   PURPOSE: Run full LLM pipeline — load model, analyze slides, correct transcript, save enriched JSON
    #   INPUTS: {
    #       slides_path: str|Path — path to slides.json,
    #       llm_config: LlmConfig — LLM provider settings,
    #       slides_dir: str|Path|None — directory with slide images (default: next to slides.json),
    #       output_path: str|Path|None — enriched output path (default: overwrite slides.json)
    #   }
    #   OUTPUTS: Path — path to enriched slides.json
    #   SIDE_EFFECTS: loads/unloads LLM model, writes enriched slides.json, saves analysis sidecars
    #   LINKS: M-LLM-ORCHESTRATOR
    # END_CONTRACT: run_llm_pipeline

    slides_path = Path(slides_path)
    if not slides_path.is_file():
        logger.error(f"[LlmOrchestrator][run_llm_pipeline] File not found | path={slides_path}")
        raise FileNotFoundError(f"slides.json not found: {slides_path}")

    if slides_dir is None:
        slides_dir = slides_path.parent / "slides"
    else:
        slides_dir = Path(slides_dir)

    out_path = Path(output_path) if output_path else slides_path

    # START_BLOCK_LOAD_DOCUMENT
    logger.info(
        f"[LlmOrchestrator][run_llm_pipeline] Loading document | "
        f"path={slides_path}"
    )
    doc = SlidesDocument.model_validate_json(slides_path.read_text(encoding="utf-8"))
    logger.info(
        f"[LlmOrchestrator][run_llm_pipeline] Document loaded | "
        f"slides={len(doc.slides)}"
    )
    # END_BLOCK_LOAD_DOCUMENT

    # START_BLOCK_INIT_CLIENT
    client = LlmClient(llm_config)
    # END_BLOCK_INIT_CLIENT

    # START_BLOCK_LOAD_MODEL
    logger.info("[LlmOrchestrator][run_llm_pipeline] Loading model...")
    client.load_model()
    logger.info("[LlmOrchestrator][run_llm_pipeline] Model ready")
    # END_BLOCK_LOAD_MODEL

    # START_BLOCK_PROCESS_SLIDES
    total = len(doc.slides)
    for i, seg in enumerate(doc.slides):
        logger.info(
            f"[LlmOrchestrator][run_llm_pipeline] Processing slide | "
            f"index={i + 1}/{total} slide=#{seg.index}"
        )

        # START_BLOCK_ANALYZE_SLIDE
        image_path = Path(seg.image) if Path(seg.image).is_absolute() else slides_dir / Path(seg.image).name
        if not image_path.is_file():
            logger.warning(
                f"[LlmOrchestrator][run_llm_pipeline] Slide image not found, skipping vision | "
                f"slide=#{seg.index} path={image_path}"
            )
            seg.llm_description = None
            seg.slide_context = None
        else:
            try:
                analysis = analyze_slide(
                    seg=seg,
                    image_path=image_path,
                    llm_client=client,
                    slides_dir=slides_dir,
                )
                seg.llm_description = analysis.description
                seg.slide_context = ", ".join(analysis.key_terms) if analysis.key_terms else None
                logger.info(
                    f"[LlmOrchestrator][run_llm_pipeline] Vision analysis done | "
                    f"slide=#{seg.index} terms={len(analysis.key_terms)}"
                )
            except Exception as e:
                logger.error(
                    f"[LlmOrchestrator][run_llm_pipeline] Vision analysis failed | "
                    f"slide=#{seg.index} error={e}"
                )
                seg.llm_description = None
                seg.slide_context = None
        # END_BLOCK_ANALYZE_SLIDE

        # START_BLOCK_REPHRASE_TRANSCRIPT
        if seg.transcript or seg.subtitle_cues:
            try:
                corrected = process_notes(
                    seg,
                    mode="llm",
                    llm_client=client,
                    slide_description=seg.llm_description,
                    slide_context=seg.slide_context,
                )
                seg.transcript = corrected
                logger.info(
                    f"[LlmOrchestrator][run_llm_pipeline] Transcript corrected | "
                    f"slide=#{seg.index} chars={len(corrected)}"
                )
            except Exception as e:
                logger.error(
                    f"[LlmOrchestrator][run_llm_pipeline] Transcript correction failed | "
                    f"slide=#{seg.index} error={e}"
                )
        # END_BLOCK_REPHRASE_TRANSCRIPT

    # END_BLOCK_PROCESS_SLIDES

    # START_BLOCK_SAVE_RESULT
    out_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    logger.info(
        f"[LlmOrchestrator][run_llm_pipeline] Enriched document saved | "
        f"path={out_path}"
    )
    # END_BLOCK_SAVE_RESULT

    return out_path
