# FILE: tests/test_llm_orchestrator.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit tests for LlmOrchestrator — pipeline orchestration
#   SCOPE: Verify full pipeline: load → analyze → rephrase → unload → save
#   DEPENDS: pytest, llm_orchestrator, llm_client, slide_analyzer, notes_processor, models
#   LINKS: M-LLM-ORCHESTRATOR, V-M-LLM-ORCHESTRATOR
#   ROLE: TEST
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from video2pptx.config import LlmConfig
from video2pptx.llm_orchestrator import run_llm_pipeline
from video2pptx.models import SlidesDocument, SlideSegment, SubtitleCue, VideoInfo


@pytest.fixture
def llm_config() -> LlmConfig:
    return LlmConfig(
        enabled=True,
        provider="openai-compat",
        base_url="http://localhost:1234/v1",
        model="gemma-4-26b-a4b-it@q4_k_xl",
        context_window=60000,
        temperature=0.2,
        max_tokens=4096,
        unload_when_done=True,
    )


def _create_sample_doc(tmp_path: Path, slide_count: int = 2) -> tuple[Path, Path]:
    slides = []
    for i in range(slide_count):
        idx = i + 1
        img_path = tmp_path / "slides" / f"slide_{idx:03d}.png"
        img_path.parent.mkdir(parents=True, exist_ok=True)
        img_path.write_bytes(b"fake_image_data")

        seg = SlideSegment(
            index=idx,
            start=float(i * 10),
            end=float((i + 1) * 10),
            duration=10.0,
            representative_timestamp=float(i * 10 + 5),
            image=str(img_path),
            transcript=f"Original transcript for slide {idx} with some terms.",
            subtitle_cues=[
                SubtitleCue(start=float(i * 10), end=float(i * 10 + 10), text=f"Subtitle text {idx}"),
            ],
        )
        slides.append(seg)

    doc = SlidesDocument(
        video=VideoInfo(path="test.mp4", duration=20.0, width=1920, height=1080, fps=30.0),
        slides=slides,
    )
    json_path = tmp_path / "slides.json"
    json_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")
    return json_path, tmp_path / "slides"


SAMPLE_VISION_RESPONSE = """===
Тема: Test Slide
Термины: term1, term2
Текст на слайде: Test content
Визуальный контент: Test visuals
Контекст: Test context
==="""


class TestRunLlmPipeline:
    def test_full_pipeline_success(self, llm_config: LlmConfig, tmp_path: Path):
        json_path, slides_dir = _create_sample_doc(tmp_path, slide_count=2)

        with patch("video2pptx.llm_orchestrator.LlmClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.chat.return_value = "Corrected transcript for slide."
            mock_instance.vision.return_value = SAMPLE_VISION_RESPONSE
            MockClient.return_value = mock_instance

            out = run_llm_pipeline(
                slides_path=json_path,
                llm_config=llm_config,
                slides_dir=slides_dir,
            )

            assert out == json_path
            assert json_path.is_file()

            # Verify enriched document
            enriched = SlidesDocument.model_validate_json(json_path.read_text(encoding="utf-8"))
            assert len(enriched.slides) == 2

            for seg in enriched.slides:
                assert seg.llm_description is not None
                assert "term1" in seg.slide_context
                assert "Corrected transcript" in seg.transcript

            # Verify model lifecycle
            mock_instance.load_model.assert_called_once()

    def test_pipeline_empty_document(self, llm_config: LlmConfig, tmp_path: Path):
        doc = SlidesDocument(
            video=VideoInfo(path="test.mp4", duration=0.0, width=1, height=1, fps=1.0),
            slides=[],
        )
        json_path = tmp_path / "slides.json"
        json_path.write_text(doc.model_dump_json(indent=2), encoding="utf-8")

        with patch("video2pptx.llm_orchestrator.LlmClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.chat.return_value = "Corrected"
            mock_instance.vision.return_value = SAMPLE_VISION_RESPONSE
            MockClient.return_value = mock_instance

            out = run_llm_pipeline(slides_path=json_path, llm_config=llm_config)
            assert out == json_path
            mock_instance.load_model.assert_called_once()

    def test_pipeline_missing_slides_json(self, llm_config: LlmConfig):
        with pytest.raises(FileNotFoundError):
            run_llm_pipeline(
                slides_path="/nonexistent/slides.json",
                llm_config=llm_config,
            )

    def test_pipeline_vision_failure_continues(self, llm_config: LlmConfig, tmp_path: Path):
        json_path, slides_dir = _create_sample_doc(tmp_path, slide_count=2)

        with patch("video2pptx.llm_orchestrator.LlmClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.vision.side_effect = RuntimeError("API error")
            mock_instance.chat.return_value = "Transcript without vision context."
            MockClient.return_value = mock_instance

            out = run_llm_pipeline(
                slides_path=json_path,
                llm_config=llm_config,
                slides_dir=slides_dir,
            )

            enriched = SlidesDocument.model_validate_json(out.read_text(encoding="utf-8"))
            for seg in enriched.slides:
                assert seg.llm_description is None
                assert seg.transcript != ""

    def test_pipeline_custom_output_path(self, llm_config: LlmConfig, tmp_path: Path):
        json_path, slides_dir = _create_sample_doc(tmp_path)

        with patch("video2pptx.llm_orchestrator.LlmClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.chat.return_value = "Corrected."
            mock_instance.vision.return_value = SAMPLE_VISION_RESPONSE
            MockClient.return_value = mock_instance

            out_path = tmp_path / "enriched_slides.json"
            result = run_llm_pipeline(
                slides_path=json_path,
                llm_config=llm_config,
                slides_dir=slides_dir,
                output_path=out_path,
            )

            assert result == out_path
            assert out_path.is_file()
            assert json_path.is_file()  # original preserved

    def test_pipeline_sidecars_saved(self, llm_config: LlmConfig, tmp_path: Path):
        json_path, slides_dir = _create_sample_doc(tmp_path, slide_count=2)

        with patch("video2pptx.llm_orchestrator.LlmClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.chat.return_value = "Corrected."
            mock_instance.vision.return_value = SAMPLE_VISION_RESPONSE
            MockClient.return_value = mock_instance

            run_llm_pipeline(
                slides_path=json_path,
                llm_config=llm_config,
                slides_dir=slides_dir,
            )

            for i in range(1, 3):
                sidecar = slides_dir / f"slide_{i:03d}_analysis.json"
                assert sidecar.is_file()
                data = json.loads(sidecar.read_text(encoding="utf-8"))
                assert data["slide_index"] == i
