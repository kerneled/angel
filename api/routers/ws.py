from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import settings
from deps import get_store
from services.audio_processor import process_audio_chunk
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
    llm = _get_llm_router()

    store.create_session(mode=mode)
    logger.info("WS connected: session=%s mode=%s", session_id, mode)

    ping_task = asyncio.create_task(_ping_loop(websocket))

    try:
        while True:
            raw = await websocket.receive()

            if "text" in raw:
                msg = json.loads(raw["text"])
                msg_type = msg.get("type")

                if msg_type == "frame" and mode in ("video", "combined"):
                    await _handle_frame(websocket, llm, store, session_id, msg)
                elif msg_type == "audio_chunk" and mode in ("audio", "combined"):
                    data = msg.get("data", "")
                    import base64

                    audio_bytes = base64.b64decode(data)
                    await _handle_audio(
                        websocket, llm, store, session_id, audio_bytes
                    )

            elif "bytes" in raw:
                if mode in ("audio", "combined"):
                    await _handle_audio(
                        websocket, llm, store, session_id, raw["bytes"]
                    )

    except WebSocketDisconnect:
        logger.info("WS disconnected: session=%s", session_id)
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
):
    image_b64 = msg.get("data", "")
    if not image_b64:
        return

    try:
        analysis, vision_usage = await analyze_frame(llm, image_b64)

        await ws.send_json(
            {"type": "result", "payload": analysis.model_dump()}
        )

        interpretation_text = ""
        interp_usage: LLMUsage | None = None

        async for token, usage in stream_interpretation(llm, analysis):
            if token:
                interpretation_text += token
                await ws.send_json({"type": "token", "content": token})
            if usage:
                interp_usage = usage

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


async def _handle_audio(
    ws: WebSocket,
    llm: LLMRouter,
    store,
    session_id: str,
    audio_bytes: bytes,
):
    try:
        result = await process_audio_chunk(audio_bytes)

        await ws.send_json(
            {"type": "result", "payload": result.model_dump()}
        )

        interpretation_text = ""
        interp_usage: LLMUsage | None = None
        analysis_json = json.dumps(result.model_dump())

        async for token, usage in llm.stream_interpretation(analysis_json):
            if token:
                interpretation_text += token
                await ws.send_json({"type": "token", "content": token})
            if usage:
                interp_usage = usage

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
