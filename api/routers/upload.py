from __future__ import annotations

import base64
import io
import logging
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile

from config import settings
from deps import get_store
from services.audio_processor import process_audio_chunk
from services.llm_router import create_router
from services.vision_processor import analyze_frame, stream_interpretation

logger = logging.getLogger("dogsense.upload")
router = APIRouter(prefix="/api/upload", tags=["upload"])

AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg"}
VIDEO_EXTENSIONS = {".mp4", ".mov"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
MAX_DURATION_S = 60


@router.post("")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    ext = _get_extension(file.filename)
    content = await file.read()

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(413, f"File too large (max {settings.max_upload_size_mb}MB)")

    llm = create_router(
        provider=settings.llm_provider,
        fallback=settings.llm_fallback,
        anthropic_key=settings.anthropic_api_key,
        gemini_key=settings.gemini_api_key,
    )
    store = get_store()
    session_id = store.create_session(mode="upload")

    if ext in AUDIO_EXTENSIONS:
        return await _process_audio(content, llm, store, session_id)
    elif ext in IMAGE_EXTENSIONS:
        return await _process_image(content, llm, store, session_id)
    elif ext in VIDEO_EXTENSIONS:
        return await _process_video(content, llm, store, session_id)
    else:
        raise HTTPException(
            400,
            f"Unsupported file type: {ext}. "
            f"Accepted: {AUDIO_EXTENSIONS | VIDEO_EXTENSIONS | IMAGE_EXTENSIONS}",
        )


async def _process_audio(content: bytes, llm, store, session_id: str):
    result = await process_audio_chunk(content)

    interpretation_text = ""
    interp_usage = None
    import json

    async for token, usage in llm.stream_interpretation(json.dumps(result.model_dump())):
        if token:
            interpretation_text += token
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

    return {
        "session_id": session_id,
        "type": "audio",
        "audio": result.model_dump(),
        "interpretation": interpretation_text,
    }


async def _process_image(content: bytes, llm, store, session_id: str):
    image_b64 = base64.b64encode(content).decode()
    analysis, vision_usage = await analyze_frame(llm, image_b64, mode="photo")

    interpretation_text = ""
    interp_usage = None
    async for token, usage in stream_interpretation(llm, analysis, mode="photo"):
        if token:
            interpretation_text += token
        if usage:
            interp_usage = usage

    total_prompt = vision_usage.prompt_tokens
    total_completion = vision_usage.completion_tokens
    if interp_usage:
        total_prompt += interp_usage.prompt_tokens
        total_completion += interp_usage.completion_tokens

    store.save_analysis(
        session_id=session_id,
        mode="video",
        vision=analysis.model_dump(),
        interpretation=interpretation_text,
        provider=vision_usage.provider,
        prompt_tokens=total_prompt,
        completion_tokens=total_completion,
        latency_ms=vision_usage.latency_ms + (interp_usage.latency_ms if interp_usage else 0),
    )

    return {
        "session_id": session_id,
        "type": "image",
        "vision": analysis.model_dump(),
        "interpretation": interpretation_text,
    }


async def _process_video(content: bytes, llm, store, session_id: str):
    from services.frame_aggregator import FrameAggregator

    frames = await _extract_keyframes(content)
    aggregator = FrameAggregator()
    frame_analyses = []
    total_prompt = 0
    total_completion = 0
    total_latency = 0
    provider_name = None

    # Analyze all frames and aggregate
    for i, frame_bytes in enumerate(frames):
        image_b64 = base64.b64encode(frame_bytes).decode()
        analysis, usage = await analyze_frame(llm, image_b64, mode="video")
        aggregator.add(analysis)
        frame_analyses.append(analysis)
        total_prompt += usage.prompt_tokens
        total_completion += usage.completion_tokens
        total_latency += usage.latency_ms
        provider_name = usage.provider

    aggregate = aggregator.aggregate()

    # Single unified interpretation using aggregate context
    best_analysis = next(
        (a for a in frame_analyses if a.dog_detected),
        frame_analyses[-1] if frame_analyses else None,
    )

    interpretation_text = ""
    if best_analysis:
        async for token, usage in stream_interpretation(llm, best_analysis, aggregate, mode="video"):
            if token:
                interpretation_text += token
            if usage:
                total_prompt += usage.prompt_tokens
                total_completion += usage.completion_tokens
                total_latency += usage.latency_ms

    # Save single consolidated analysis
    store.save_analysis(
        session_id=session_id,
        mode="video",
        vision=best_analysis.model_dump() if best_analysis else None,
        interpretation=interpretation_text,
        provider=provider_name,
        prompt_tokens=total_prompt,
        completion_tokens=total_completion,
        latency_ms=total_latency,
    )

    return {
        "session_id": session_id,
        "type": "video",
        "vision": best_analysis.model_dump() if best_analysis else None,
        "aggregate": aggregate.model_dump(),
        "interpretation": interpretation_text,
        "frame_count": len(frames),
    }


async def _extract_keyframes(video_bytes: bytes, num_frames: int = 5) -> list[bytes]:
    import asyncio

    def _extract():
        import cv2
        import numpy as np
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(video_bytes)
            tmp_path = f.name

        try:
            cap = cv2.VideoCapture(tmp_path)
            total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total <= 0:
                return []

            indices = np.linspace(0, total - 1, num_frames, dtype=int)
            frames = []

            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
                ret, frame = cap.read()
                if ret:
                    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    frames.append(buf.tobytes())

            cap.release()
            return frames
        finally:
            os.unlink(tmp_path)

    import asyncio

    return await asyncio.to_thread(_extract)


def _get_extension(filename: str) -> str:
    import os

    return os.path.splitext(filename)[1].lower()
