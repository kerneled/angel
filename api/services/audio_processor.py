from __future__ import annotations

import asyncio
import io
import logging
from typing import Optional

import numpy as np

from models.schemas import AudioLabel, AudioResult

logger = logging.getLogger("dogsense.audio")

LABELS = list(AudioLabel)


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

        num_labels = min(len(LABELS), probs.shape[0])
        scores = {LABELS[i].value: float(probs[i]) for i in range(num_labels)}
        best_idx = int(probs[:num_labels].argmax())
        return AudioResult(
            label=LABELS[best_idx],
            confidence=float(probs[best_idx]),
            all_scores=scores,
        )

    return await asyncio.to_thread(_run)


async def _librosa_fallback(
    audio_bytes: bytes,
    sample_rate: int,
) -> AudioResult:
    import librosa

    def _run():
        waveform = _decode_audio(audio_bytes, sample_rate)
        mfcc = librosa.feature.mfcc(y=waveform, sr=sample_rate, n_mfcc=13)
        energy = float(np.mean(librosa.feature.rms(y=waveform)))
        zcr = float(np.mean(librosa.feature.zero_crossing_rate(y=waveform)))
        spectral_centroid = float(
            np.mean(librosa.feature.spectral_centroid(y=waveform, sr=sample_rate))
        )

        if energy > 0.1 and spectral_centroid > 3000:
            label = AudioLabel.ALERT
            confidence = min(0.7, energy * 2)
        elif energy > 0.08 and zcr > 0.15:
            label = AudioLabel.AGGRESSION
            confidence = 0.5
        elif energy < 0.02:
            label = AudioLabel.LONELINESS
            confidence = 0.4
        elif spectral_centroid > 2000:
            label = AudioLabel.PLAYFUL
            confidence = 0.5
        elif zcr < 0.05 and energy < 0.05:
            label = AudioLabel.FEAR
            confidence = 0.4
        else:
            label = AudioLabel.ATTENTION
            confidence = 0.3

        scores = {l.value: 0.0 for l in LABELS}
        scores[label.value] = confidence
        return AudioResult(label=label, confidence=confidence, all_scores=scores)

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
