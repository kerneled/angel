from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# --- Enums ---

class EmotionLabel(str, Enum):
    HAPPY = "happy"
    FEARFUL = "fearful"
    AGGRESSIVE = "aggressive"
    ANXIOUS = "anxious"
    PLAYFUL = "playful"
    NEUTRAL = "neutral"
    PAIN = "pain"


class AudioLabel(str, Enum):
    ALERT = "alert"
    FEAR = "fear"
    PLAYFUL = "playful"
    PAIN = "pain"
    LONELINESS = "loneliness"
    AGGRESSION = "aggression"
    ATTENTION = "attention"


class TailPosition(str, Enum):
    HIGH = "high"
    MID = "mid"
    LOW = "low"
    TUCKED = "tucked"
    WAGGING = "wagging"
    UNKNOWN = "unknown"


class EarOrientation(str, Enum):
    FORWARD = "forward"
    BACK = "back"
    RELAXED = "relaxed"
    ASYMMETRIC = "asymmetric"
    UNKNOWN = "unknown"


class BodyPosture(str, Enum):
    UPRIGHT = "upright"
    CROUCHED = "crouched"
    PLAY_BOW = "play-bow"
    STIFF = "stiff"
    RELAXED = "relaxed"
    UNKNOWN = "unknown"


class FacialExpression(str, Enum):
    RELAXED = "relaxed"
    TENSE = "tense"
    TEETH_SHOWING = "teeth-showing"
    YAWNING = "yawning"
    UNKNOWN = "unknown"


class Piloerection(str, Enum):
    VISIBLE = "visible"
    NOT_VISIBLE = "not-visible"
    UNCERTAIN = "uncertain"


class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnalysisMode(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"
    COMBINED = "combined"


class WSMessageType(str, Enum):
    FRAME = "frame"
    AUDIO_CHUNK = "audio_chunk"
    TOKEN = "token"
    RESULT = "result"
    ERROR = "error"


# --- Vision Analysis ---

class DogAnalysis(BaseModel):
    dog_detected: bool
    tail_position: Optional[TailPosition] = None
    ear_orientation: Optional[EarOrientation] = None
    body_posture: Optional[BodyPosture] = None
    facial_expression: Optional[FacialExpression] = None
    piloerection: Optional[Piloerection] = None
    overall_emotion: Optional[EmotionLabel] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    urgency: Optional[Urgency] = None
    summary: Optional[str] = None


# --- Audio Analysis ---

class AudioResult(BaseModel):
    label: AudioLabel
    confidence: float = Field(ge=0.0, le=1.0)
    all_scores: dict[str, float] = Field(default_factory=dict)


# --- WebSocket Messages ---

class WSMessageIn(BaseModel):
    type: WSMessageType
    data: Optional[str] = None
    timestamp: Optional[int] = None


class WSMessageOut(BaseModel):
    type: WSMessageType
    content: Optional[str] = None
    payload: Optional[dict] = None
    message: Optional[str] = None


# --- Session / History ---

class SessionCreate(BaseModel):
    mode: AnalysisMode


class AnalysisRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    session_id: UUID
    mode: AnalysisMode
    vision: Optional[DogAnalysis] = None
    audio: Optional[AudioResult] = None
    interpretation: Optional[str] = None
    provider: Optional[str] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SessionSummary(BaseModel):
    id: UUID
    mode: AnalysisMode
    analysis_count: int = 0
    last_emotion: Optional[EmotionLabel] = None
    created_at: datetime
    ended_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    audio_model_loaded: bool = False
    version: str = "0.1.0"
