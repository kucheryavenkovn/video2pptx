# FILE: src/video2pptx/llm_client.py
# VERSION: 0.1.0
# START_MODULE_CONTRACT
#   PURPOSE: Generic LLM client abstraction over OpenAI-compatible API (LM Studio) with vision support and model lifecycle management
#   SCOPE: Chat completion, vision analysis, model load/unload via LM Studio HTTP API
#   DEPENDS: config (LlmConfig), httpx
#   LINKS: M-LLM-CLIENT
#   ROLE: INTEGRATION
#   MAP_MODE: EXPORTS
# END_MODULE_CONTRACT
#
# START_MODULE_MAP
#   LlmClient - main client class with chat(), vision(), load_model(), unload_model()
# END_MODULE_MAP

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from loguru import logger

from video2pptx.config import LlmConfig

try:
    import httpx
    _HAS_HTTPX = True
except ImportError:  # noqa: F841
    httpx = None  # type: ignore[assignment]
    _HAS_HTTPX = False


class LlmClient:
    # START_CONTRACT: LlmClient
    #   PURPOSE: OpenAI-compatible LLM client with chat, vision, and model lifecycle
    #   INPUTS: { config: LlmConfig }
    #   OUTPUTS: { LlmClient instance }
    #   SIDE_EFFECTS: none (HTTP calls on method invocation)
    #   LINKS: M-LLM-CLIENT
    # END_CONTRACT: LlmClient

    def __init__(self, config: LlmConfig) -> None:
        if not _HAS_HTTPX:
            raise ImportError(
                "httpx is required for LLM features. Install it: pip install httpx"
            )
        self.config = config
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if config.api_token:
            headers["Authorization"] = f"Bearer {config.api_token}"
        self._client = httpx.Client(
            base_url=config.base_url.rstrip("/") + "/",
            timeout=httpx.Timeout(120.0, connect=10.0),
            headers=headers,
        )
        self._model_loaded = False
        logger.info(
            f"[LlmClient][init] Client initialized | "
            f"provider={config.provider} model={config.model} "
            f"base_url={config.base_url} context_window={config.context_window}"
        )

    # START_BLOCK_TEST_CONNECTION
    def test_connection(self) -> tuple[bool, str]:
        # START_CONTRACT: test_connection
        #   PURPOSE: Verify connectivity to LLM API by fetching model list
        #   INPUTS: none
        #   OUTPUTS: (success: bool, message: str)
        #   SIDE_EFFECTS: HTTP GET to LLM API
        #   LINKS: M-LLM-CLIENT
        # END_CONTRACT: test_connection

        logger.info(
            f"[LlmClient][test_connection] Testing connection | "
            f"base_url={self.config.base_url}"
        )
        try:
            resp = self._client.get("models", timeout=15.0)
            if resp.status_code == 401:
                return False, "Authentication failed (401) — check API token"
            resp.raise_for_status()
            data = resp.json()
            models = data.get("data", [])
            model_names = [m.get("id", "?") for m in models]
            logger.info(
                f"[LlmClient][test_connection] Connection OK | "
                f"models={model_names}"
            )
            return True, f"Connected. Models: {', '.join(model_names[:5])}"
        except httpx.TimeoutException:
            return False, f"Connection timeout — {self.config.base_url} unreachable"
        except httpx.HTTPStatusError as e:
            return False, f"HTTP {e.response.status_code}: {e.response.text[:200]}"
        except httpx.RequestError as e:
            return False, f"Connection failed: {e}"
    # END_BLOCK_TEST_CONNECTION

    # START_BLOCK_FETCH_MODELS
    def fetch_models(self) -> list[str]:
        # START_CONTRACT: fetch_models
        #   PURPOSE: Fetch available model names from the LLM API
        #   INPUTS: none
        #   OUTPUTS: list[str] — model IDs, empty on failure
        #   SIDE_EFFECTS: HTTP GET to models endpoint
        #   LINKS: M-LLM-CLIENT
        # END_CONTRACT: fetch_models

        models_url = self.config.models_url.strip() or f"{self.config.base_url.rstrip('/')}/models"
        logger.info(
            f"[LlmClient][fetch_models] Fetching models | url={models_url}"
        )
        try:
            resp = self._client.get(models_url, timeout=15.0)
            resp.raise_for_status()
            data = resp.json()
            models = [m.get("id", "") for m in data.get("data", []) if m.get("id")]
            logger.info(
                f"[LlmClient][fetch_models] Retrieved {len(models)} models | "
                f"models={models[:5]}"
            )
            return models
        except Exception as e:
            logger.warning(f"[LlmClient][fetch_models] Failed | error={e}")
            return []
    # END_BLOCK_FETCH_MODELS

    # START_BLOCK_CHAT
    def chat(self, messages: list[dict[str, str]], **kwargs: Any) -> str:
        # START_CONTRACT: chat
        #   PURPOSE: Send chat completion request to LLM and return response text
        #   INPUTS: {
        #       messages: list[dict] — OpenAI-format messages,
        #       **kwargs: override default temperature, max_tokens
        #   }
        #   OUTPUTS: str — response text
        #   SIDE_EFFECTS: HTTP POST to LLM API
        #   LINKS: M-LLM-CLIENT
        # END_CONTRACT: chat

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.config.temperature),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }

        logger.info(
            f"[LlmClient][chat] Sending chat request | "
            f"model={self.config.model} messages={len(messages)} "
            f"tokens_hint={sum(len(m.get('content', '')) for m in messages)}"
        )

        try:
            resp = self._client.post("chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            result = data["choices"][0]["message"]["content"]

            logger.info(
                f"[LlmClient][chat] Received response | "
                f"model={self.config.model} chars={len(result)}"
            )
            return result
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[LlmClient][chat] HTTP error | status={e.response.status_code} "
                f"body={e.response.text[:500]}"
            )
            raise
        except httpx.RequestError as e:
            logger.error(
                f"[LlmClient][chat] Connection error | "
                f"base_url={self.config.base_url} detail={e}"
            )
            raise
    # END_BLOCK_CHAT

    # START_BLOCK_VISION
    def vision(self, image_path: str | Path, prompt: str = "Describe this image") -> str:
        # START_CONTRACT: vision
        #   PURPOSE: Send image for vision analysis and return description
        #   INPUTS: {
        #       image_path: str|Path — path to image file,
        #       prompt: str — instruction for vision model
        #   }
        #   OUTPUTS: str — vision model response
        #   SIDE_EFFECTS: reads image file, HTTP POST to LLM API
        #   LINKS: M-LLM-CLIENT
        # END_CONTRACT: vision

        path = Path(image_path)
        if not path.is_file():
            raise FileNotFoundError(f"Image not found: {path}")

        image_bytes = path.read_bytes()
        b64 = base64.b64encode(image_bytes).decode("utf-8")
        ext = path.suffix.lower().lstrip(".")
        if ext == "jpg":
            ext = "jpeg"
        data_uri = f"data:image/{ext};base64,{b64}"

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            }
        ]

        logger.info(
            f"[LlmClient][vision] Sending vision request | "
            f"image={path.name} size={len(image_bytes)} bytes"
        )

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        try:
            resp = self._client.post("chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()
            result = data["choices"][0]["message"]["content"]

            logger.info(
                f"[LlmClient][vision] Vision response received | "
                f"image={path.name} chars={len(result)}"
            )
            return result
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[LlmClient][vision] HTTP error | status={e.response.status_code} "
                f"body={e.response.text[:500]}"
            )
            raise
        except httpx.RequestError as e:
            logger.error(
                f"[LlmClient][vision] Connection error | "
                f"base_url={self.config.base_url} detail={e}"
            )
            raise
    # END_BLOCK_VISION

    # START_BLOCK_LOAD_MODEL
    def load_model(self) -> bool:
        # START_CONTRACT: load_model
        #   PURPOSE: Load model via LM Studio API (POST /v1/model/load)
        #   INPUTS: none
        #   OUTPUTS: bool — True if model loaded successfully
        #   SIDE_EFFECTS: HTTP POST to LM Studio, may block while model loads into VRAM
        #   LINKS: M-LLM-CLIENT
        # END_CONTRACT: load_model

        if self._model_loaded:
            logger.info(f"[LlmClient][load_model] Model already loaded | model={self.config.model}")
            return True

        payload = {"model": self.config.model}

        logger.info(
            f"[LlmClient][load_model] Loading model | "
            f"model={self.config.model} base_url={self.config.base_url}"
        )

        try:
            resp = self._client.post("model/load", json=payload, timeout=300.0)
            if resp.status_code == 200:
                self._model_loaded = True
                logger.info(f"[LlmClient][load_model] Model loaded successfully | model={self.config.model}")
                return True

            logger.warning(
                f"[LlmClient][load_model] Model load returned non-200 | "
                f"status={resp.status_code} body={resp.text[:300]}"
            )
            return False
        except httpx.RequestError as e:
            logger.warning(
                f"[LlmClient][load_model] Load endpoint not supported or unavailable | "
                f"detail={e} — continuing (model may already be loaded)"
            )
            self._model_loaded = True
            return True
    # END_BLOCK_LOAD_MODEL

    # START_BLOCK_UNLOAD_MODEL
    def unload_model(self) -> bool:
        # START_CONTRACT: unload_model
        #   PURPOSE: Unload model via LM Studio API (POST /v1/model/unload) to free VRAM
        #   INPUTS: none
        #   OUTPUTS: bool — True if model unloaded successfully
        #   SIDE_EFFECTS: HTTP POST to LM Studio, frees GPU VRAM
        #   LINKS: M-LLM-CLIENT
        # END_CONTRACT: unload_model

        if not self._model_loaded:
            logger.info("[LlmClient][unload_model] No model loaded, skipping unload")
            return True

        logger.info(
            f"[LlmClient][unload_model] Unloading model | "
            f"model={self.config.model}"
        )

        try:
            resp = self._client.post("model/unload", timeout=60.0)
            if resp.status_code == 200:
                self._model_loaded = False
                logger.info("[LlmClient][unload_model] Model unloaded successfully")
                return True

            logger.warning(
                f"[LlmClient][unload_model] Unload returned non-200 | "
                f"status={resp.status_code} body={resp.text[:300]}"
            )
            return False
        except httpx.RequestError as e:
            logger.warning(
                f"[LlmClient][unload_model] Unload endpoint not available | "
                f"detail={e}"
            )
            return False
    # END_BLOCK_UNLOAD_MODEL

    # START_BLOCK_CLOSE
    def close(self) -> None:
        self._client.close()
        logger.info("[LlmClient][close] HTTP client closed")
    # END_BLOCK_CLOSE

    def __enter__(self) -> LlmClient:
        return self

    def __exit__(self, *args: Any) -> None:
        if self.config.unload_when_done and self._model_loaded:
            self.unload_model()
        self.close()
