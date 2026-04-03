from __future__ import annotations

import json
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

Base = declarative_base()


class SessionRow(Base):
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    mode = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)


class AnalysisRow(Base):
    __tablename__ = "analyses"

    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False, index=True)
    mode = Column(String, nullable=False)
    vision_json = Column(Text, nullable=True)
    audio_json = Column(Text, nullable=True)
    interpretation = Column(Text, nullable=True)
    provider = Column(String, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SessionStore:
    def __init__(self, db_path: str = "./data/sessions.db"):
        self._engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self._engine)
        self._session_factory = sessionmaker(bind=self._engine)

    def _get_session(self) -> Session:
        return self._session_factory()

    def create_session(self, mode: str) -> str:
        session_id = str(uuid4())
        with self._get_session() as db:
            db.add(SessionRow(id=session_id, mode=mode))
            db.commit()
        return session_id

    def end_session(self, session_id: str) -> None:
        with self._get_session() as db:
            row = db.query(SessionRow).filter_by(id=session_id).first()
            if row:
                row.ended_at = datetime.utcnow()
                db.commit()

    def save_analysis(
        self,
        session_id: str,
        mode: str,
        vision: Optional[dict] = None,
        audio: Optional[dict] = None,
        interpretation: Optional[str] = None,
        provider: Optional[str] = None,
        prompt_tokens: Optional[int] = None,
        completion_tokens: Optional[int] = None,
        latency_ms: Optional[int] = None,
    ) -> str:
        analysis_id = str(uuid4())
        with self._get_session() as db:
            db.add(
                AnalysisRow(
                    id=analysis_id,
                    session_id=session_id,
                    mode=mode,
                    vision_json=json.dumps(vision) if vision else None,
                    audio_json=json.dumps(audio) if audio else None,
                    interpretation=interpretation,
                    provider=provider,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    latency_ms=latency_ms,
                )
            )
            db.commit()
        return analysis_id

    def list_sessions(self, limit: int = 50) -> list[dict]:
        with self._get_session() as db:
            rows = (
                db.query(SessionRow)
                .order_by(SessionRow.created_at.desc())
                .limit(limit)
                .all()
            )
            result = []
            for r in rows:
                count = db.query(AnalysisRow).filter_by(session_id=r.id).count()
                last = (
                    db.query(AnalysisRow)
                    .filter_by(session_id=r.id)
                    .order_by(AnalysisRow.created_at.desc())
                    .first()
                )
                last_emotion = None
                if last and last.vision_json:
                    v = json.loads(last.vision_json)
                    last_emotion = v.get("overall_emotion")
                result.append(
                    {
                        "id": r.id,
                        "mode": r.mode,
                        "analysis_count": count,
                        "last_emotion": last_emotion,
                        "created_at": r.created_at.isoformat() if r.created_at else None,
                        "ended_at": r.ended_at.isoformat() if r.ended_at else None,
                    }
                )
            return result

    def get_session_analyses(self, session_id: str) -> list[dict]:
        with self._get_session() as db:
            rows = (
                db.query(AnalysisRow)
                .filter_by(session_id=session_id)
                .order_by(AnalysisRow.created_at.asc())
                .all()
            )
            return [
                {
                    "id": r.id,
                    "session_id": r.session_id,
                    "mode": r.mode,
                    "vision": json.loads(r.vision_json) if r.vision_json else None,
                    "audio": json.loads(r.audio_json) if r.audio_json else None,
                    "interpretation": r.interpretation,
                    "provider": r.provider,
                    "prompt_tokens": r.prompt_tokens,
                    "completion_tokens": r.completion_tokens,
                    "latency_ms": r.latency_ms,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ]
