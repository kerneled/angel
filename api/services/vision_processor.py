from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Optional

from models.schemas import DogAnalysis, FrameAggregate
from services.llm_router import LLMRouter, LLMUsage

logger = logging.getLogger("dogsense.vision")


async def analyze_frame(
    router: LLMRouter,
    image_b64: str,
    mode: str = "stream",
) -> tuple[DogAnalysis, LLMUsage]:
    raw, usage = await router.analyze_image(image_b64, mode)

    try:
        analysis = DogAnalysis(**raw)
    except Exception as e:
        logger.warning("Failed to validate vision response: %s — raw: %s", e, str(raw)[:200])
        analysis = DogAnalysis(dog_detected=False)

    return analysis, usage


async def stream_interpretation(
    router: LLMRouter,
    analysis: DogAnalysis,
    aggregate: Optional[FrameAggregate] = None,
    mode: str = "stream",
) -> AsyncIterator[tuple[str, Optional[LLMUsage]]]:
    if not analysis.dog_detected:
        yield "Nenhum cachorro detectado na imagem.", LLMUsage(provider="none")
        return

    analysis_json = analysis.model_dump_json()
    aggregate_json = aggregate.model_dump_json() if aggregate else "null"

    async for token, usage in router.stream_interpretation(analysis_json, aggregate_json, mode):
        yield token, usage
