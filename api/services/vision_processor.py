from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Optional

from models.schemas import DogAnalysis
from services.llm_router import LLMRouter, LLMUsage

logger = logging.getLogger("dogsense.vision")


async def analyze_frame(
    router: LLMRouter,
    image_b64: str,
) -> tuple[DogAnalysis, LLMUsage]:
    raw, usage = await router.analyze_image(image_b64)

    try:
        analysis = DogAnalysis(**raw)
    except Exception as e:
        logger.warning("Failed to validate vision response: %s", e)
        analysis = DogAnalysis(dog_detected=False)

    return analysis, usage


async def stream_interpretation(
    router: LLMRouter,
    analysis: DogAnalysis,
) -> AsyncIterator[tuple[str, Optional[LLMUsage]]]:
    if not analysis.dog_detected:
        yield "Nenhum cachorro detectado na imagem.", LLMUsage(provider="none")
        return

    analysis_json = analysis.model_dump_json()
    async for token, usage in router.stream_interpretation(analysis_json):
        yield token, usage
