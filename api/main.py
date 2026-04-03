from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from deps import get_store
from models.schemas import HealthResponse
from startup import is_audio_model_loaded, preload_audio_model

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("dogsense")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("DogSense API starting up...")
    get_store()
    preload_audio_model()
    logger.info("Startup complete")
    yield
    logger.info("DogSense API shutting down...")


app = FastAPI(
    title="DogSense API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        audio_model_loaded=is_audio_model_loaded(),
    )


from routers.ws import router as ws_router
from routers.upload import router as upload_router

app.include_router(ws_router)
app.include_router(upload_router)


@app.get("/api/sessions")
async def list_sessions():
    store = get_store()
    return store.list_sessions()


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    store = get_store()
    return store.get_session_analyses(session_id)
