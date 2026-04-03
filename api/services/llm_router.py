from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from services.prompts import (
    VISION_PROMPT_STREAM,
    VISION_PROMPT_PHOTO,
    INTERPRETATION_PROMPT_STREAM,
    INTERPRETATION_PROMPT_PHOTO,
    INTERPRETATION_PROMPT_VIDEO,
)

logger = logging.getLogger("dogsense.llm")

# --- Cost tracking (USD per 1M tokens, April 2025 pricing) ---
COST_PER_1M = {
    "claude": {"input": 3.00, "output": 15.00},
    "gemini": {"input": 0.10, "output": 0.40},
}

def get_vision_prompt(mode: str = "stream") -> str:
    if mode == "photo":
        return VISION_PROMPT_PHOTO
    return VISION_PROMPT_STREAM


def get_interpretation_prompt(mode: str = "stream") -> str:
    if mode == "photo":
        return INTERPRETATION_PROMPT_PHOTO
    elif mode == "video":
        return INTERPRETATION_PROMPT_VIDEO
    return INTERPRETATION_PROMPT_STREAM


class LLMUsage:
    def __init__(
        self,
        provider: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        latency_ms: int = 0,
    ):
        self.provider = provider
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.latency_ms = latency_ms

    @property
    def cost_usd(self) -> float:
        rates = COST_PER_1M.get(self.provider, {"input": 0, "output": 0})
        return (
            self.prompt_tokens * rates["input"] / 1_000_000
            + self.completion_tokens * rates["output"] / 1_000_000
        )


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def analyze_image(self, image_b64: str, mode: str = "stream") -> tuple[dict, LLMUsage]:
        """Send image to vision API, return structured JSON + usage."""

    @abstractmethod
    async def stream_interpretation(
        self, analysis_json: str, aggregate_json: str = "null", mode: str = "stream"
    ) -> AsyncIterator[tuple[str, Optional[LLMUsage]]]:
        """Stream interpretation tokens. Last yield includes usage."""


class ClaudeProvider(LLMProvider):
    name = "claude"

    def __init__(self, api_key: str):
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = "claude-sonnet-4-20250514"

    async def analyze_image(self, image_b64: str, mode: str = "stream") -> tuple[dict, LLMUsage]:
        start = time.monotonic()
        vision_prompt = get_vision_prompt(mode)
        max_tokens = 2048 if mode == "photo" else 1024
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64,
                            },
                        },
                        {"type": "text", "text": vision_prompt},
                    ],
                }
            ],
        )
        latency = int((time.monotonic() - start) * 1000)
        usage = LLMUsage(
            provider=self.name,
            prompt_tokens=response.usage.input_tokens,
            completion_tokens=response.usage.output_tokens,
            latency_ms=latency,
        )
        text = response.content[0].text
        parsed = _parse_json(text)
        return parsed, usage

    async def stream_interpretation(
        self, analysis_json: str, aggregate_json: str = "null", mode: str = "stream"
    ) -> AsyncIterator[tuple[str, Optional[LLMUsage]]]:
        start = time.monotonic()
        interp_prompt = get_interpretation_prompt(mode)
        prompt = interp_prompt.format(
            analysis_json=analysis_json,
            aggregate_json=aggregate_json,
        )
        input_tokens = 0
        output_tokens = 0

        max_tokens = 1024 if mode == "photo" else 512
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            async for event in stream:
                if hasattr(event, "type"):
                    if event.type == "content_block_delta" and hasattr(event, "delta"):
                        if hasattr(event.delta, "text"):
                            yield event.delta.text, None

            final = await stream.get_final_message()
            input_tokens = final.usage.input_tokens
            output_tokens = final.usage.output_tokens

        latency = int((time.monotonic() - start) * 1000)
        yield "", LLMUsage(
            provider=self.name,
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
            latency_ms=latency,
        )


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str):
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model_id = "gemini-2.0-flash"

    async def analyze_image(self, image_b64: str, mode: str = "stream") -> tuple[dict, LLMUsage]:
        from google.genai import types

        start = time.monotonic()
        image_bytes = base64.b64decode(image_b64)
        vision_prompt = get_vision_prompt(mode)

        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=self._model_id,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                vision_prompt,
            ],
        )
        latency = int((time.monotonic() - start) * 1000)

        prompt_tokens = 0
        completion_tokens = 0
        if response.usage_metadata:
            prompt_tokens = response.usage_metadata.prompt_token_count or 0
            completion_tokens = response.usage_metadata.candidates_token_count or 0

        usage = LLMUsage(
            provider=self.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency,
        )
        parsed = _parse_json(response.text)
        return parsed, usage

    async def stream_interpretation(
        self, analysis_json: str, aggregate_json: str = "null", mode: str = "stream"
    ) -> AsyncIterator[tuple[str, Optional[LLMUsage]]]:
        start = time.monotonic()
        interp_prompt = get_interpretation_prompt(mode)
        prompt = interp_prompt.format(
            analysis_json=analysis_json,
            aggregate_json=aggregate_json,
        )

        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=self._model_id,
            contents=prompt,
        )

        # google-genai doesn't support streaming the same way, emit full text
        if response.text:
            yield response.text, None

        prompt_tokens = 0
        completion_tokens = 0
        if response.usage_metadata:
            prompt_tokens = response.usage_metadata.prompt_token_count or 0
            completion_tokens = response.usage_metadata.candidates_token_count or 0

        latency = int((time.monotonic() - start) * 1000)
        yield "", LLMUsage(
            provider=self.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency,
        )


class LLMRouter:
    def __init__(self, primary: LLMProvider, fallback: Optional[LLMProvider] = None):
        self.primary = primary
        self.fallback = fallback

    async def analyze_image(self, image_b64: str, mode: str = "stream") -> tuple[dict, LLMUsage]:
        try:
            return await self.primary.analyze_image(image_b64, mode)
        except Exception as e:
            logger.warning("Primary LLM (%s) failed: %s", self.primary.name, e)
            if self.fallback:
                logger.info("Falling back to %s", self.fallback.name)
                return await self.fallback.analyze_image(image_b64, mode)
            raise

    async def stream_interpretation(
        self, analysis_json: str, aggregate_json: str = "null", mode: str = "stream"
    ) -> AsyncIterator[tuple[str, Optional[LLMUsage]]]:
        try:
            async for token, usage in self.primary.stream_interpretation(
                analysis_json, aggregate_json, mode
            ):
                yield token, usage
        except Exception as e:
            logger.warning("Primary LLM (%s) failed: %s", self.primary.name, e)
            if self.fallback:
                logger.info("Falling back to %s", self.fallback.name)
                async for token, usage in self.fallback.stream_interpretation(
                    analysis_json, aggregate_json, mode
                ):
                    yield token, usage
            else:
                raise


def create_router(
    provider: str,
    fallback: str,
    anthropic_key: str = "",
    gemini_key: str = "",
) -> LLMRouter:
    providers = {}
    if anthropic_key:
        providers["claude"] = ClaudeProvider(anthropic_key)
    if gemini_key:
        providers["gemini"] = GeminiProvider(gemini_key)

    primary = providers.get(provider)
    fallback_provider = providers.get(fallback)

    if not primary:
        raise ValueError(
            f"Primary provider '{provider}' not available. Check API key."
        )

    return LLMRouter(primary=primary, fallback=fallback_provider)


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.error("Failed to parse LLM JSON response: %s", text[:200])
        return {"dog_detected": False, "error": "Failed to parse response"}
