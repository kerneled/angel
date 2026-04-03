from __future__ import annotations

import logging
import os

logger = logging.getLogger("dogsense.startup")

_audio_model = None
_audio_processor = None


def preload_audio_model() -> bool:
    global _audio_model, _audio_processor

    model_name = os.getenv("HF_MODEL_AUDIO", "facebook/wav2vec2-base")
    cache_dir = os.getenv("HF_CACHE_DIR", "/app/models")

    try:
        from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2Processor

        logger.info("Loading Wav2Vec2 model: %s (cache: %s)", model_name, cache_dir)
        _audio_processor = Wav2Vec2Processor.from_pretrained(
            model_name, cache_dir=cache_dir
        )
        _audio_model = Wav2Vec2ForSequenceClassification.from_pretrained(
            model_name, cache_dir=cache_dir
        )
        _audio_model.eval()
        logger.info("Wav2Vec2 model loaded successfully")
        return True
    except Exception as e:
        logger.warning("Failed to load Wav2Vec2, will use Librosa fallback: %s", e)
        _audio_model = None
        _audio_processor = None
        return False


def get_audio_model():
    return _audio_model


def get_audio_processor():
    return _audio_processor


def is_audio_model_loaded() -> bool:
    return _audio_model is not None
