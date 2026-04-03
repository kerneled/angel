from __future__ import annotations

import asyncio
import io
import logging

import numpy as np

from models.schemas import AudioFeatures, AudioLatentState, AudioResult, BehavioralHypothesis

logger = logging.getLogger("dogsense.audio")


async def process_audio_chunk(
    audio_bytes: bytes,
    sample_rate: int = 16000,
) -> AudioResult:
    from startup import get_audio_model, get_audio_processor

    model = get_audio_model()
    processor = get_audio_processor()

    if model is not None and processor is not None:
        return await _wav2vec2_inference(audio_bytes, model, processor, sample_rate)
    else:
        return await _librosa_fallback(audio_bytes, sample_rate)


async def _wav2vec2_inference(
    audio_bytes: bytes,
    model,
    processor,
    sample_rate: int,
) -> AudioResult:
    import torch

    def _run():
        waveform = _decode_audio(audio_bytes, sample_rate)
        inputs = processor(
            waveform, sampling_rate=sample_rate, return_tensors="pt", padding=True
        )
        with torch.no_grad():
            logits = model(**inputs).logits
        probs = torch.nn.functional.softmax(logits, dim=-1)[0]

        # Map model outputs to behavioral states
        state_map = ["relaxed", "fearful", "playful", "anxious", "excited", "defensive_aggression", "excited"]
        num = min(len(state_map), probs.shape[0])
        hypotheses = []
        for i in range(num):
            if float(probs[i]) > 0.05:
                hypotheses.append(BehavioralHypothesis(state=state_map[i], probability=float(probs[i])))

        # Normalize
        total = sum(h.probability for h in hypotheses)
        if total > 0:
            for h in hypotheses:
                h.probability = round(h.probability / total, 3)

        hypotheses.sort(key=lambda h: h.probability, reverse=True)

        best_prob = hypotheses[0].probability if hypotheses else 0
        arousal = int(min(10, best_prob * 10))

        return AudioResult(
            features=AudioFeatures(type="bark", intensity="medium", pitch="mid", rhythm="isolated"),
            latent_state=AudioLatentState(arousal=arousal, valence=0.0),
            hypotheses=hypotheses[:4],
            uncertainty="medium",
        )

    return await asyncio.to_thread(_run)


async def _librosa_fallback(
    audio_bytes: bytes,
    sample_rate: int,
) -> AudioResult:
    import librosa

    def _run():
        waveform = _decode_audio(audio_bytes, sample_rate)
        energy = float(np.mean(librosa.feature.rms(y=waveform)))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y=waveform)))
        spectral_centroid = float(
            np.mean(librosa.feature.spectral_centroid(y=waveform, sr=sample_rate))
        )

        # Determine features
        pitch = "high" if spectral_centroid > 3000 else "mid" if spectral_centroid > 1500 else "low"
        intensity = "high" if energy > 0.1 else "medium" if energy > 0.03 else "low"

        # Build probabilistic hypotheses from heuristics
        hypotheses: list[BehavioralHypothesis] = []

        if energy > 0.1 and spectral_centroid > 3000:
            hypotheses = [
                BehavioralHypothesis(state="excited", probability=0.5),
                BehavioralHypothesis(state="anxious", probability=0.3),
                BehavioralHypothesis(state="defensive_aggression", probability=0.2),
            ]
            arousal = 8
            valence = -0.2
        elif energy > 0.08 and zcr > 0.15:
            hypotheses = [
                BehavioralHypothesis(state="defensive_aggression", probability=0.5),
                BehavioralHypothesis(state="fearful", probability=0.3),
                BehavioralHypothesis(state="anxious", probability=0.2),
            ]
            arousal = 7
            valence = -0.6
        elif energy < 0.02:
            hypotheses = [
                BehavioralHypothesis(state="relaxed", probability=0.6),
                BehavioralHypothesis(state="anxious", probability=0.25),
                BehavioralHypothesis(state="fearful", probability=0.15),
            ]
            arousal = 2
            valence = -0.1
        elif spectral_centroid > 2000:
            hypotheses = [
                BehavioralHypothesis(state="playful", probability=0.5),
                BehavioralHypothesis(state="excited", probability=0.35),
                BehavioralHypothesis(state="anxious", probability=0.15),
            ]
            arousal = 6
            valence = 0.4
        else:
            hypotheses = [
                BehavioralHypothesis(state="relaxed", probability=0.4),
                BehavioralHypothesis(state="anxious", probability=0.3),
                BehavioralHypothesis(state="excited", probability=0.3),
            ]
            arousal = 4
            valence = 0.0

        return AudioResult(
            features=AudioFeatures(pitch=pitch, intensity=intensity, rhythm="isolated", type="bark"),
            latent_state=AudioLatentState(arousal=arousal, valence=valence),
            hypotheses=hypotheses,
            uncertainty="high",
        )

    return await asyncio.to_thread(_run)


def _decode_audio(audio_bytes: bytes, target_sr: int) -> np.ndarray:
    try:
        import soundfile as sf

        waveform, sr = sf.read(io.BytesIO(audio_bytes))
        if sr != target_sr:
            import librosa

            waveform = librosa.resample(waveform, orig_sr=sr, target_sr=target_sr)
        if waveform.ndim > 1:
            waveform = waveform.mean(axis=1)
        return waveform.astype(np.float32)
    except Exception:
        logger.warning("soundfile decode failed, trying librosa")
        import librosa

        waveform, _ = librosa.load(io.BytesIO(audio_bytes), sr=target_sr, mono=True)
        return waveform
