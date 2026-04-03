from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_provider: str = "claude"
    llm_fallback: str = "gemini"
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    hf_model_audio: str = "facebook/wav2vec2-base"
    hf_cache_dir: str = "./models"
    frame_interval_ms: int = 2500
    audio_chunk_ms: int = 3000
    max_upload_size_mb: int = 100
    session_db_path: str = "./data/sessions.db"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    class Config:
        env_file = ("../.env", ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
