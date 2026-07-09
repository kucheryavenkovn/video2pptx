# FILE: tests/test_slide_analyzer.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit tests for SlideAnalyzer — vision analysis and response parsing
#   SCOPE: Verify vision request format, response parsing, sidecar saving, error handling
#   DEPENDS: pytest, slide_analyzer, llm_client, models
#   LINKS: M-SLIDE-ANALYZER, V-M-SLIDE-ANALYZER
#   ROLE: TEST
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from video_slide_md.llm_client import LlmClient
from video_slide_md.models import SlideSegment
from video_slide_md.slide_analyzer import (
    VISION_SYSTEM_PROMPT,
    SlideAnalysis,
    analyze_slide,
    _parse_vision_response,
    _fmt_ts,
)


@pytest.fixture
def sample_seg() -> SlideSegment:
    return SlideSegment(
        index=1,
        start=0.0,
        end=10.0,
        duration=10.0,
        representative_timestamp=5.0,
        image="slides/slide_001.png",
    )


SAMPLE_VISION_RESPONSE = """===
Тема: Введение в Python
Термины: Python, интерпретатор, динамическая типизация, PEP 8
Текст на слайде: Python — интерпретируемый язык программирования с динамической типизацией
Визуальный контент: Логотип Python, пример кода print('Hello')
Контекст: Первый слайд лекции по основам Python
==="""


class TestFmtTs:
    def test_zero(self):
        assert _fmt_ts(0.0) == "0:00"

    def test_basic(self):
        assert _fmt_ts(65.0) == "1:05"

    def test_hour_mark(self):
        assert _fmt_ts(3661.0) == "61:01"


class TestParseVisionResponse:
    def test_parse_full_response(self):
        result = _parse_vision_response(SAMPLE_VISION_RESPONSE)
        assert isinstance(result, SlideAnalysis)
        assert "Python" in result.description
        assert "Python" in result.key_terms
        assert "интерпретатор" in result.key_terms
        assert "PEP 8" in result.key_terms

    def test_parse_empty_response(self):
        result = _parse_vision_response("")
        assert result.description == "No description available"
        assert result.key_terms == []

    def test_parse_whitespace_only(self):
        result = _parse_vision_response("   \n\n  ")
        assert result.description == "No description available"

    def test_parse_response_without_markers(self):
        raw = "Просто текстовый ответ без маркеров"
        result = _parse_vision_response(raw)
        assert "Просто текстовый" in result.description
        assert result.raw_response == raw

    def test_parse_partial_response(self):
        raw = "===\nТема: Test\nТермины: term1, term2\n==="
        result = _parse_vision_response(raw)
        assert result.description != "No description available"
        assert "term1" in result.key_terms

    def test_parse_response_with_extra_spaces_in_labels(self):
        raw = "===\nТема : Test\nТермины : a, b\n==="
        result = _parse_vision_response(raw)
        assert result.description != ""
        assert "a" in result.key_terms


class TestAnalyzeSlide:
    def test_analyze_slide_success(self, sample_seg: SlideSegment, tmp_path: Path):
        image_file = tmp_path / "slide_001.png"
        image_file.write_bytes(b"fake_png")

        mock_llm = MagicMock(spec=LlmClient)
        mock_llm.vision.return_value = SAMPLE_VISION_RESPONSE

        result = analyze_slide(sample_seg, image_file, mock_llm, slides_dir=tmp_path)

        assert isinstance(result, SlideAnalysis)
        assert "Python" in result.description
        assert len(result.key_terms) > 0
        mock_llm.vision.assert_called_once()

        # Check sidecar saved
        sidecar = tmp_path / "slide_001_analysis.json"
        assert sidecar.is_file()
        data = json.loads(sidecar.read_text(encoding="utf-8"))
        assert data["slide_index"] == 1
        assert "Python" in data["description"]

    def test_analyze_slide_missing_image(self, sample_seg: SlideSegment):
        mock_llm = MagicMock(spec=LlmClient)
        with pytest.raises(FileNotFoundError):
            analyze_slide(sample_seg, "/nonexistent/image.png", mock_llm)

    def test_analyze_slide_no_sidecar(self, sample_seg: SlideSegment, tmp_path: Path):
        image_file = tmp_path / "slide_001.png"
        image_file.write_bytes(b"fake_png")

        mock_llm = MagicMock(spec=LlmClient)
        mock_llm.vision.return_value = SAMPLE_VISION_RESPONSE

        result = analyze_slide(sample_seg, image_file, mock_llm, slides_dir=None)

        assert isinstance(result, SlideAnalysis)
        assert "Python" in result.description

    def test_analyze_slide_empty_vision_response(self, sample_seg: SlideSegment, tmp_path: Path):
        image_file = tmp_path / "slide_001.png"
        image_file.write_bytes(b"fake_png")

        mock_llm = MagicMock(spec=LlmClient)
        mock_llm.vision.return_value = ""

        result = analyze_slide(sample_seg, image_file, mock_llm, slides_dir=tmp_path)

        assert result.description == "No description available"
        assert result.key_terms == []

    def test_vision_system_prompt_exists(self):
        assert len(VISION_SYSTEM_PROMPT) > 50
        assert "Термины" in VISION_SYSTEM_PROMPT
