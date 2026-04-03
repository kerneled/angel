from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

logger = logging.getLogger("dogsense.llm")

VISION_PROMPT = """Analyze this image of a dog. Return ONLY valid JSON, no explanation:
{
  "dog_detected": true|false,
  "tail_position": "high|mid|low|tucked|wagging|unknown",
  "ear_orientation": "forward|back|relaxed|asymmetric|unknown",
  "body_posture": "upright|crouched|play-bow|stiff|relaxed|unknown",
  "facial_expression": "relaxed|tense|teeth-showing|yawning|unknown",
  "piloerection": "visible|not-visible|uncertain",
  "overall_emotion": "happy|fearful|aggressive|anxious|playful|neutral|pain",
  "confidence": 0.0-1.0,
  "urgency": "low|medium|high",
  "summary": "one sentence for owner"
}
If no dog is detected, return dog_detected: false and null for all other fields."""

INTERPRETATION_PROMPT = """You are an expert canine behaviorist. Based on the following structured analysis of a dog's body language, provide a brief, actionable interpretation for the owner in Portuguese (Brazilian).

Analysis data:
{analysis_json}

Respond with:
1. What the dog is likely feeling (1 sentence)
2. What the owner should do (1 sentence)
3. Any urgency note if applicable

Keep it concise and friendly. Max 3 sentences total."""


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


class LLMProvider(ABC):
    name: str

    @abstractmethod
    async def analyze_image(self, image_b64: str) -> tuple[dict, LLMUsage]:
        """Send image to vision API, return structured JSON + usage."""

    @abstractmethod
    async def stream_interpretation(
        self, analysis_json: str
    ) -> AsyncIterator[tuple[str, Optional[LLMUsage]]]:
        """Stream interpretation tokens. Last yield includes usage."""


class ClaudeProvider(LLMProvider):
    name = "claude"

    def __init__(self, api_key: str):
        import anthropic

        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = "claude-sonnet-4-20250514"

    async def analyze_image(self, image_b64: str) -> tuple[dict, LLMUsage]:
        start = time.monotonic()
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=512,
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
                        {"type": "text", "text": VISION_PROMPT},
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
        self, analysis_json: str
    ) -> AsyncIterator[tuple[str, Optional[LLMUsage]]]:
        start = time.monotonic()
        prompt = INTERPRETATION_PROMPT.format(analysis_json=analysis_json)
        input_tokens = 0
        output_tokens = 0

        async with self._client.messages.stream(
            model=self._model,
            max_tokens=256,
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
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel("gemini-2.0-flash")

    async def analyze_image(self, image_b64: str) -> tuple[dict, LLMUsage]:
        import google.generativeai as genai

        start = time.monotonic()
        image_bytes = base64.b64decode(image_b64)
        image_part = {"mime_type": "image/jpeg", "data": image_bytes}

        response = await asyncio.to_thread(
            self._model.generate_content, [image_part, VISION_PROMPT]
        )
        latency = int((time.monotonic() - start) * 1000)

        prompt_tokens = 0
        completion_tokens = 0
        if hasattr(response, "usage_metadata"):
            prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
            completion_tokens = getattr(
                response.usage_metadata, "candidates_token_count", 0
            )

        usage = LLMUsage(
            provider=self.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency,
        )
        parsed = _parse_json(response.text)
        return parsed, usage

    async def stream_interpretation(
        self, analysis_json: str
    ) -> AsyncIterator[tuple[str, Optional[LLMUsage]]]:
        start = time.monotonic()
        prompt = INTERPRETATION_PROMPT.format(analysis_json=analysis_json)

        response = await asyncio.to_thread(
            self._model.generate_content, prompt, stream=True
        )

        for chunk in response:
            if chunk.text:
                yield chunk.text, None

        prompt_tokens = 0
        completion_tokens = 0
        if hasattr(response, "usage_metadata"):
            prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0)
            completion_tokens = getattr(
                response.usage_metadata, "candidates_token_count", 0
            )

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

    async def analyze_image(self, image_b64: str) -> tuple[dict, LLMUsage]:
        try:
            return await self.primary.analyze_image(image_b64)
        except Exception as e:
            logger.warning("Primary LLM (%s) failed: %s", self.primary.name, e)
            if self.fallback:
                logger.info("Falling back to %s", self.fallback.name)
                return await self.fallback.analyze_image(image_b64)
            raise

    async def stream_interpretation(
        self, analysis_json: str
    ) -> AsyncIterator[tuple[str, Optional[LLMUsage]]]:
        try:
            async for token, usage in self.primary.stream_interpretation(analysis_json):
                yield token, usage
        except Exception as e:
            logger.warning("Primary LLM (%s) failed: %s", self.primary.name, e)
            if self.fallback:
                logger.info("Falling back to %s", self.fallback.name)
                async for token, usage in self.fallback.stream_interpretation(
                    analysis_json
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
