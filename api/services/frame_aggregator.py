from __future__ import annotations

import logging
import time
from collections import Counter
from typing import Optional

from models.schemas import DogAnalysis, FrameAggregate

logger = logging.getLogger("dogsense.aggregator")

MAX_WINDOW = 20


class FrameAggregator:
    """Maintains a sliding window of frame analyses for temporal aggregation."""

    def __init__(self):
        self._frames: list[tuple[float, DogAnalysis]] = []

    def add(self, analysis: DogAnalysis) -> None:
        now = time.time()
        self._frames.append((now, analysis))
        if len(self._frames) > MAX_WINDOW:
            self._frames = self._frames[-MAX_WINDOW:]

    def aggregate(self) -> FrameAggregate:
        if not self._frames:
            return FrameAggregate()

        valid = [(t, a) for t, a in self._frames if a.dog_detected]
        if not valid:
            return FrameAggregate(frame_count=len(self._frames))

        window_seconds = valid[-1][0] - valid[0][0] if len(valid) > 1 else 0

        # Dominant state from hypotheses
        state_counts: Counter[str] = Counter()
        for _, a in valid:
            ps = a.primary_state
            if ps:
                state_counts[ps] += 1

        dominant = state_counts.most_common(1)[0][0] if state_counts else None

        # Stability
        stability = 0.0
        total_states = sum(state_counts.values())
        if dominant and total_states:
            stability = state_counts[dominant] / total_states

        # Averages of latent dimensions
        arousals = [a.latent_state.arousal for _, a in valid]
        valences = [a.latent_state.valence for _, a in valid]
        safeties = [a.latent_state.perceived_safety for _, a in valid]

        avg_arousal = sum(arousals) / len(arousals) if arousals else 0
        avg_valence = sum(valences) / len(valences) if valences else 0
        avg_safety = sum(safeties) / len(safeties) if safeties else 0

        # Trend (compare first half vs second half of arousal)
        trend = "stable"
        if len(arousals) >= 4:
            mid = len(arousals) // 2
            first_half = sum(arousals[:mid]) / mid
            second_half = sum(arousals[mid:]) / (len(arousals) - mid)
            diff = second_half - first_half
            if diff > 1.5:
                trend = "deteriorating"
            elif diff < -1.5:
                trend = "improving"

        # Conflict count
        conflict_count = sum(1 for _, a in valid if a.conflict.detected)

        return FrameAggregate(
            frame_count=len(valid),
            window_seconds=round(window_seconds, 1),
            dominant_state=dominant,
            state_stability=round(stability, 2),
            avg_arousal=round(avg_arousal, 1),
            avg_valence=round(avg_valence, 2),
            avg_safety=round(avg_safety, 1),
            trend=trend,
            conflict_count=conflict_count,
        )

    def clear(self) -> None:
        self._frames.clear()
