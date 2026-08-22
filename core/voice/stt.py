"""
STT - Speech-to-Text using Whisper (local, free).
openai-whisper: https://github.com/openai/whisper
"""

import io
import wave
from typing import Any


class STT:
    """Whisper-based speech-to-text. Local, free, private."""

    def __init__(self, model_name: str = "base"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is not None:
            return self._model
        try:
            import whisper
            self._model = whisper.load_model(self.model_name)
            return self._model
        except ImportError:
            return None
        except Exception:
            return None

    def transcribe(self, audio_bytes: bytes,
                   language: str = None) -> dict:
        """Transcribe audio bytes to text."""
        model = self._load_model()
        if model is None:
            return {
                "text": "",
                "error": ("Whisper not installed. "
                          "Install: pip install openai-whisper")
            }
        try:
            import tempfile
            with tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False
            ) as f:
                f.write(audio_bytes)
                f.flush()
                result = model.transcribe(
                    f.name, language=language
                )
            return {
                "text": result.get("text", "").strip(),
                "language": result.get("language", "unknown"),
                "segments": len(result.get("segments", [])),
            }
        except Exception as e:
            return {"text": "", "error": str(e)}

    def is_available(self) -> bool:
        return self._load_model() is not None

    def status(self) -> dict:
        return {
            "engine": "whisper",
            "model": self.model_name,
            "available": self.is_available(),
        }
