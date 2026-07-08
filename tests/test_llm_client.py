# FILE: tests/test_llm_client.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Unit tests for LlmClient — chat, vision, model lifecycle
#   SCOPE: Verify request format, response parsing, error handling, image encoding
#   DEPENDS: pytest, llm_client, config
#   LINKS: M-LLM-CLIENT, V-M-LLM-CLIENT
#   ROLE: TEST
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from video_slide_md.config import LlmConfig
from video_slide_md.llm_client import LlmClient


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


@pytest.fixture
def mock_response() -> dict:
    return {
        "choices": [
            {
                "message": {
                    "content": "This is a test response from the LLM."
                }
            }
        ]
    }


class TestLlmClientInit:
    def test_init_creates_httpx_client(self, llm_config: LlmConfig):
        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MagicMock()
            client = LlmClient(llm_config)
            assert client.config == llm_config
            mock_client_cls.assert_called_once()

    def test_init_sets_correct_base_url(self, llm_config: LlmConfig):
        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value = MagicMock()
            client = LlmClient(llm_config)
            _, kwargs = mock_client_cls.call_args
            assert "http://localhost:1234/v1/" in str(kwargs.get("base_url", ""))


class TestLlmClientChat:
    def test_chat_sends_correct_payload(self, llm_config: LlmConfig, mock_response: dict):
        mock_httpx = MagicMock()
        mock_httpx.post.return_value.json.return_value = mock_response
        mock_httpx.post.return_value.raise_for_status.return_value = None

        with patch("httpx.Client", return_value=mock_httpx):
            client = LlmClient(llm_config)
            messages = [{"role": "user", "content": "Hello"}]
            result = client.chat(messages)

            assert result == "This is a test response from the LLM."
            mock_httpx.post.assert_called_once()
            url = mock_httpx.post.call_args[0][0]
            assert url == "chat/completions"
            payload = mock_httpx.post.call_args[1]["json"]
            assert payload["model"] == "gemma-4-26b-a4b-it@q4_k_xl"
            assert payload["messages"] == messages
            assert payload["temperature"] == 0.2
            assert payload["max_tokens"] == 4096

    def test_chat_with_overrides(self, llm_config: LlmConfig, mock_response: dict):
        mock_httpx = MagicMock()
        mock_httpx.post.return_value.json.return_value = mock_response
        mock_httpx.post.return_value.raise_for_status.return_value = None

        with patch("httpx.Client", return_value=mock_httpx):
            client = LlmClient(llm_config)
            result = client.chat(
                [{"role": "user", "content": "Hi"}],
                temperature=0.5,
                max_tokens=2048,
            )
            assert result == "This is a test response from the LLM."
            payload = mock_httpx.post.call_args[1]["json"]
            assert payload["temperature"] == 0.5
            assert payload["max_tokens"] == 2048

    def test_chat_http_error(self, llm_config: LlmConfig):
        mock_httpx = MagicMock()
        mock_httpx.post.return_value.raise_for_status.side_effect = \
            httpx.HTTPStatusError("400", request=MagicMock(), response=MagicMock(status_code=400))

        with patch("httpx.Client", return_value=mock_httpx):
            client = LlmClient(llm_config)
            with pytest.raises(httpx.HTTPStatusError):
                client.chat([{"role": "user", "content": "Hi"}])

    def test_chat_connection_error(self, llm_config: LlmConfig):
        mock_httpx = MagicMock()
        mock_httpx.post.side_effect = httpx.RequestError("Connection refused")

        with patch("httpx.Client", return_value=mock_httpx):
            client = LlmClient(llm_config)
            with pytest.raises(httpx.RequestError):
                client.chat([{"role": "user", "content": "Hi"}])


class TestLlmClientVision:
    def test_vision_sends_image(self, llm_config: LlmConfig, mock_response: dict, tmp_path: Path):
        image_file = tmp_path / "test.png"
        image_file.write_bytes(b"fake_png_data")

        mock_httpx = MagicMock()
        mock_httpx.post.return_value.json.return_value = mock_response
        mock_httpx.post.return_value.raise_for_status.return_value = None

        with patch("httpx.Client", return_value=mock_httpx):
            client = LlmClient(llm_config)
            result = client.vision(image_file, prompt="What is on this slide?")

            assert result == "This is a test response from the LLM."
            payload = mock_httpx.post.call_args[1]["json"]
            assert payload["model"] == "gemma-4-26b-a4b-it@q4_k_xl"
            content = payload["messages"][0]["content"]
            assert isinstance(content, list)
            assert len(content) == 2
            assert content[0]["type"] == "text"
            assert content[0]["text"] == "What is on this slide?"
            assert content[1]["type"] == "image_url"
            assert "data:image/png;base64," in content[1]["image_url"]["url"]

    def test_vision_file_not_found(self, llm_config: LlmConfig):
        mock_httpx = MagicMock()
        with patch("httpx.Client", return_value=mock_httpx):
            client = LlmClient(llm_config)
            with pytest.raises(FileNotFoundError):
                client.vision("/nonexistent/image.png")

    def test_vision_with_jpg(self, llm_config: LlmConfig, mock_response: dict, tmp_path: Path):
        image_file = tmp_path / "slide.jpg"
        image_file.write_bytes(b"fake_jpeg_data")

        mock_httpx = MagicMock()
        mock_httpx.post.return_value.json.return_value = mock_response
        mock_httpx.post.return_value.raise_for_status.return_value = None

        with patch("httpx.Client", return_value=mock_httpx):
            client = LlmClient(llm_config)
            result = client.vision(image_file)
            payload = mock_httpx.post.call_args[1]["json"]
            content = payload["messages"][0]["content"]
            assert "data:image/jpeg;base64," in content[1]["image_url"]["url"]


class TestLlmClientModelLifecycle:
    def test_load_model_success(self, llm_config: LlmConfig):
        mock_httpx = MagicMock()
        mock_httpx.post.return_value.status_code = 200

        with patch("httpx.Client", return_value=mock_httpx):
            client = LlmClient(llm_config)
            result = client.load_model()
            assert result is True
            assert client._model_loaded is True
            mock_httpx.post.assert_called_once()
            url = mock_httpx.post.call_args[0][0]
            assert url == "model/load"
            payload = mock_httpx.post.call_args[1]["json"]
            assert payload["model"] == "gemma-4-26b-a4b-it@q4_k_xl"

    def test_load_model_already_loaded(self, llm_config: LlmConfig):
        mock_httpx = MagicMock()
        with patch("httpx.Client", return_value=mock_httpx):
            client = LlmClient(llm_config)
            client._model_loaded = True
            result = client.load_model()
            assert result is True
            mock_httpx.post.assert_not_called()

    def test_load_model_endpoint_not_available(self, llm_config: LlmConfig):
        mock_httpx = MagicMock()
        mock_httpx.post.side_effect = httpx.RequestError("Connection refused")

        with patch("httpx.Client", return_value=mock_httpx):
            client = LlmClient(llm_config)
            result = client.load_model()
            assert result is True
            assert client._model_loaded is True

    def test_unload_model_success(self, llm_config: LlmConfig):
        mock_httpx = MagicMock()
        mock_httpx.post.return_value.status_code = 200

        with patch("httpx.Client", return_value=mock_httpx):
            client = LlmClient(llm_config)
            client._model_loaded = True
            result = client.unload_model()
            assert result is True
            assert client._model_loaded is False
            mock_httpx.post.assert_called_once_with("model/unload", timeout=60.0)

    def test_unload_model_not_loaded(self, llm_config: LlmConfig):
        mock_httpx = MagicMock()
        with patch("httpx.Client", return_value=mock_httpx):
            client = LlmClient(llm_config)
            result = client.unload_model()
            assert result is True
            mock_httpx.post.assert_not_called()

    def test_unload_model_endpoint_not_available(self, llm_config: LlmConfig):
        mock_httpx = MagicMock()
        mock_httpx.post.side_effect = httpx.RequestError("Connection refused")

        with patch("httpx.Client", return_value=mock_httpx):
            client = LlmClient(llm_config)
            client._model_loaded = True
            result = client.unload_model()
            assert result is False

    def test_context_manager_unloads_on_exit(self, llm_config: LlmConfig):
        mock_httpx = MagicMock()
        mock_httpx.post.return_value.status_code = 200

        with patch("httpx.Client", return_value=mock_httpx):
            client = LlmClient(llm_config)
            client._model_loaded = True
            with client as c:
                assert c is client
            # Should have called unload and close
            unload_calls = [call for call in mock_httpx.post.call_args_list
                          if call[0][0] == "model/unload"]
            assert len(unload_calls) == 1

    def test_context_manager_no_unload_if_disabled(self, llm_config: LlmConfig):
        llm_config.unload_when_done = False
        mock_httpx = MagicMock()

        with patch("httpx.Client", return_value=mock_httpx):
            client = LlmClient(llm_config)
            client._model_loaded = True
            with client:
                pass
            unload_calls = [call for call in mock_httpx.post.call_args_list
                          if call[0][0] == "model/unload"]
            assert len(unload_calls) == 0
