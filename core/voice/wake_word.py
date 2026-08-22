"""
Wake Word - detect "Kaihara" to activate voice mode.
OpenWakeWord: https://github.com/dscripka/openWakeWord
Falls back to simple energy-based detection.
"""

import numpy as np
from typing import Any


class WakeWord:
    """Detect wake word 'kaihara' to activate voice mode."""

    def __init__(self, wake_word: str = "kaihara"):
        self.wake_word = wake_word.lower()
        self._oww = None
        self._threshold = 0.5

    def _load_model(self):
        if self._oww is not None:
            return self._oww
        try:
            from openwakeword import Model as OWWModel
            self._oww = OWWModel()
            return self._oww
        except ImportError:
            return None
        except Exception:
            return None

    def detect(self, audio_bytes: bytes,
               sample_rate: int = 16000) -> dict:
        """Detect wake word in audio."""
        model = self._load_model()
        if model is not None:
            return self._detect_oww(audio_bytes, sample_rate)
        return self._detect_fallback(audio_bytes, sample_rate)

    def _detect_oww(self, audio_bytes: bytes,
                    sample_rate: int) -> dict:
        """Use OpenWakeWord for detection."""
        try:
            audio = np.frombuffer(audio_bytes, dtype=np.int16)
            if len(audio) == 0:
                return {"detected": False, "confidence": 0}
            predictions = self._oww.predict(audio)
            for word, score in predictions.items():
                if self.wake_word in word.lower():
                    if score > self._threshold:
                        return {"detected": True, "confidence": score}
            best = max(predictions.values()) if predictions else 0
            return {"detected": False, "confidence": best}
        except Exception:
            return {"detected": False, "confidence": 0}

    def _detect_fallback(self, audio_bytes: bytes,
                          sample_rate: int) -> dict:
        """Fallback: energy-based detection (no wake word recognition)."""
        try:
            audio = np.frombuffer(audio_bytes, dtype=np.int16)
            if len(audio) == 0:
                return {"detected": False, "confidence": 0}
            energy = np.sqrt(np.mean(audio.astype(float) ** 2))
            threshold = 500
            if energy > threshold:
                return {"detected": True, "confidence": min(energy / 2000, 1.0)}
            return {"detected": False, "confidence": 0}
        except Exception:
            return {"detected": False, "confidence": 0}

    def is_available(self) -> bool:
        return self._load_model() is not None

    def status(self) -> dict:
        return {
            "wake_word": self.wake_word,
            "engine": "openwakeword" if self.is_available() else "energy",
            "available": self.is_available(),
            "threshold": self._threshold,
        }
