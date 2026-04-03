from __future__ import annotations

from functools import lru_cache

from config import Settings, settings
from services.session_store import SessionStore


@lru_cache
def get_settings() -> Settings:
    return settings


_store: SessionStore | None = None


def get_store() -> SessionStore:
    global _store
    if _store is None:
        _store = SessionStore(db_path=settings.session_db_path)
    return _store
