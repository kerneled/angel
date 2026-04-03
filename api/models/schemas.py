from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# --- Vision Analysis (probabilistic inference) ---

class BehavioralHypothesis(BaseModel):
    state: str
    probability: float = Field(ge=0.0, le=1.0)


class BodyFeatures(BaseModel):
    tension: str = "not_visible"
    orientation: str = "not_visible"
    weight_distribution: str = "not_visible"


class TailFeatures(BaseModel):
    position: str = "not_visible"
    movement: str = "not_visible"


class EarFeatures(BaseModel):
    position: str = "not_visible"


class FaceFeatures(BaseModel):
    eyes: str = "not_visible"
    mouth: str = "not_visible"
    stress_signals: str = "not_visible"


class MovementFeatures(BaseModel):
    pattern: str = "not_available"
    variability: str = "not_available"


class ObservedFeatures(BaseModel):
    body: BodyFeatures = Field(default_factory=BodyFeatures)
    tail: TailFeatures = Field(default_factory=TailFeatures)
    ears: EarFeatures = Field(default_factory=EarFeatures)
    face: FaceFeatures = Field(default_factory=FaceFeatures)
    movement: MovementFeatures = Field(default_factory=MovementFeatures)


class LatentState(BaseModel):
    arousal: int = Field(0, ge=0, le=10)
    valence: float = Field(0.0, ge=-1.0, le=1.0)
    perceived_safety: int = Field(5, ge=0, le=10)


class ConflictDetection(BaseModel):
    detected: bool = False
    signals: list[str] = Field(default_factory=list)


class DogAnalysis(BaseModel):
    """Probabilistic canine behavior analysis from vision."""
    schema_version: str = "1.0"
    dog_detected: bool = False
    dog_count: int = 0
    breed_guess: Optional[str] = None
    input_quality: str = "medium"
    features: ObservedFeatures = Field(default_factory=ObservedFeatures)
    latent_state: LatentState = Field(default_factory=LatentState)
    conflict: ConflictDetection = Field(default_factory=ConflictDetection)
    hypotheses: list[BehavioralHypothesis] = Field(default_factory=list)
    uncertainty: str = "medium"
    summary_pt: Optional[str] = None

    @property
    def primary_state(self) -> Optional[str]:
        if not self.hypotheses:
            return None
        return max(self.hypotheses, key=lambda h: h.probability).state

    @property
    def primary_probability(self) -> Optional[float]:
        if not self.hypotheses:
            return None
        return max(self.hypotheses, key=lambda h: h.probability).probability


# --- Audio Analysis (probabilistic inference) ---

class AudioFeatures(BaseModel):
    pitch: str = "mid"
    intensity: str = "medium"
    rhythm: str = "isolated"
    type: str = "bark"


class AudioLatentState(BaseModel):
    arousal: int = Field(0, ge=0, le=10)
    valence: float = Field(0.0, ge=-1.0, le=1.0)


class AudioResult(BaseModel):
    schema_version: str = "1.0"
    dog_detected: bool = True
    features: AudioFeatures = Field(default_factory=AudioFeatures)
    latent_state: AudioLatentState = Field(default_factory=AudioLatentState)
    hypotheses: list[BehavioralHypothesis] = Field(default_factory=list)
    uncertainty: str = "medium"

    @property
    def primary_state(self) -> Optional[str]:
        if not self.hypotheses:
            return None
        return max(self.hypotheses, key=lambda h: h.probability).state

    @property
    def primary_probability(self) -> Optional[float]:
        if not self.hypotheses:
            return None
        return max(self.hypotheses, key=lambda h: h.probability).probability


# --- Frame Aggregation ---

class FrameAggregate(BaseModel):
    frame_count: int = 0
    window_seconds: float = 0
    dominant_state: Optional[str] = None
    state_stability: float = Field(0, ge=0.0, le=1.0)
    avg_arousal: float = 0
    avg_valence: float = 0
    avg_safety: float = 0
    trend: Optional[str] = None
    conflict_count: int = 0
    narrative_pt: Optional[str] = None


# --- WebSocket Messages ---

class AnalysisMode(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"
    COMBINED = "combined"


class WSMessageType(str, Enum):
    FRAME = "frame"
    AUDIO_CHUNK = "audio_chunk"
    TOKEN = "token"
    RESULT = "result"
    AGGREGATE = "aggregate"
    ERROR = "error"


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


class SessionSummary(BaseModel):
    id: UUID
    mode: AnalysisMode
    analysis_count: int = 0
    last_state: Optional[str] = None
    created_at: datetime
    ended_at: Optional[datetime] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    audio_model_loaded: bool = False
    version: str = "0.3.0"
