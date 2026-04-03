from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import settings
from deps import get_store
from services.audio_processor import process_audio_chunk
from services.frame_aggregator import FrameAggregator
from services.llm_router import LLMRouter, LLMUsage, create_router
from services.vision_processor import analyze_frame, stream_interpretation

logger = logging.getLogger("dogsense.ws")
router = APIRouter()

_llm_router: LLMRouter | None = None


def _get_llm_router() -> LLMRouter:
    global _llm_router
    if _llm_router is None:
        _llm_router = create_router(
            provider=settings.llm_provider,
            fallback=settings.llm_fallback,
            anthropic_key=settings.anthropic_api_key,
            gemini_key=settings.gemini_api_key,
        )
    return _llm_router


@router.websocket("/ws/{session_id}/{mode}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: str,
    mode: str,
):
    await websocket.accept()
    store = get_store()

    try:
        llm = _get_llm_router()
    except Exception as e:
        logger.error("LLM Router init failed: %s", e)
        await websocket.send_json({"type": "error", "message": f"LLM init failed: {e}"})
        await websocket.close()
        return

    store.create_session(session_id=session_id, mode=mode)
    logger.info("WS connected: session=%s mode=%s", session_id, mode)

    aggregator = FrameAggregator()
    session_cost = 0.0
    ping_task = asyncio.create_task(_ping_loop(websocket))

    try:
        while True:
            raw = await websocket.receive()

            if "text" in raw:
                msg = json.loads(raw["text"])
                msg_type = msg.get("type")

                if msg_type == "frame" and mode in ("video", "combined"):
                    cost = await _handle_frame(
                        websocket, llm, store, session_id, msg, aggregator
                    )
                    session_cost += cost
                elif msg_type == "audio_chunk" and mode in ("audio", "combined"):
                    data = msg.get("data", "")
                    import base64

                    audio_bytes = base64.b64decode(data)
                    cost = await _handle_audio(
                        websocket, llm, store, session_id, audio_bytes
                    )
                    session_cost += cost

            elif "bytes" in raw:
                if mode in ("audio", "combined"):
                    cost = await _handle_audio(
                        websocket, llm, store, session_id, raw["bytes"]
                    )
                    session_cost += cost

    except WebSocketDisconnect:
        logger.info(
            "WS disconnected: session=%s total_cost=$%.4f", session_id, session_cost
        )
    except Exception as e:
        logger.error("WS error: session=%s %s", session_id, e)
        await _send_error(websocket, str(e))
    finally:
        ping_task.cancel()
        store.end_session(session_id)


async def _handle_frame(
    ws: WebSocket,
    llm: LLMRouter,
    store,
    session_id: str,
    msg: dict,
    aggregator: FrameAggregator,
) -> float:
    """Returns cost in USD for this frame analysis."""
    image_b64 = msg.get("data", "")
    if not image_b64:
        return 0.0

    total_cost = 0.0

    try:
        analysis, vision_usage = await analyze_frame(llm, image_b64)
        total_cost += vision_usage.cost_usd

        # Add to aggregator
        aggregator.add(analysis)
        aggregate = aggregator.aggregate()

        # Send structured result + aggregate
        await ws.send_json({
            "type": "result",
            "payload": {
                **analysis.model_dump(),
                "aggregate": aggregate.model_dump(),
                "cost_usd": round(total_cost, 5),
                "provider": vision_usage.provider,
                "latency_ms": vision_usage.latency_ms,
            },
        })

        # Stream interpretation with aggregate context
        interpretation_text = ""
        interp_usage: LLMUsage | None = None

        async for token, usage in stream_interpretation(llm, analysis, aggregate):
            if token:
                interpretation_text += token
                await ws.send_json({"type": "token", "content": token})
            if usage:
                interp_usage = usage

        if interp_usage:
            total_cost += interp_usage.cost_usd

        # Send final cost
        await ws.send_json({
            "type": "aggregate",
            "payload": {
                "aggregate": aggregate.model_dump(),
                "frame_cost_usd": round(total_cost, 5),
            },
        })

        # Persist
        total_prompt = vision_usage.prompt_tokens
        total_completion = vision_usage.completion_tokens
        total_latency = vision_usage.latency_ms
        provider = vision_usage.provider
        if interp_usage:
            total_prompt += interp_usage.prompt_tokens
            total_completion += interp_usage.completion_tokens
            total_latency += interp_usage.latency_ms

        store.save_analysis(
            session_id=session_id,
            mode="video",
            vision=analysis.model_dump(),
            interpretation=interpretation_text,
            provider=provider,
            prompt_tokens=total_prompt,
            completion_tokens=total_completion,
            latency_ms=total_latency,
        )

    except Exception as e:
        logger.error("Frame analysis error: %s", e)
        await _send_error(ws, f"Vision analysis failed: {e}")

    return total_cost


async def _handle_audio(
    ws: WebSocket,
    llm: LLMRouter,
    store,
    session_id: str,
    audio_bytes: bytes,
) -> float:
    """Returns cost in USD for this audio analysis."""
    total_cost = 0.0

    try:
        result = await process_audio_chunk(audio_bytes)

        await ws.send_json({"type": "result", "payload": result.model_dump()})

        interpretation_text = ""
        interp_usage: LLMUsage | None = None
        analysis_json = json.dumps(result.model_dump())

        async for token, usage in llm.stream_interpretation(analysis_json):
            if token:
                interpretation_text += token
                await ws.send_json({"type": "token", "content": token})
            if usage:
                interp_usage = usage

        if interp_usage:
            total_cost += interp_usage.cost_usd

        store.save_analysis(
            session_id=session_id,
            mode="audio",
            audio=result.model_dump(),
            interpretation=interpretation_text,
            provider=interp_usage.provider if interp_usage else None,
            prompt_tokens=interp_usage.prompt_tokens if interp_usage else None,
            completion_tokens=interp_usage.completion_tokens if interp_usage else None,
            latency_ms=interp_usage.latency_ms if interp_usage else None,
        )

    except Exception as e:
        logger.error("Audio analysis error: %s", e)
        await _send_error(ws, f"Audio analysis failed: {e}")

    return total_cost


async def _ping_loop(ws: WebSocket):
    try:
        while True:
            await asyncio.sleep(20)
            await ws.send_json({"type": "ping"})
    except Exception:
        pass


async def _send_error(ws: WebSocket, message: str):
    try:
        await ws.send_json({"type": "error", "message": message})
    except Exception:
        pass
