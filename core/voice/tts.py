"""
TTS - Text-to-Speech using Piper (local, free, natural voice).
Piper: https://github.com/rhasspy/piper
Falls back to pyttsx3 if Piper not available.
"""

import os
import subprocess
import tempfile
from typing import Any


class TTS:
    """Piper-based text-to-speech. Local, free, natural voice."""

    def __init__(self, voice: str = "en_US-lessig-medium",
                 piper_path: str = "piper"):
        self.voice = voice
        self.piper_path = piper_path
        self._pyttsx = None

    def synthesize(self, text: str) -> dict:
        """Synthesize text to speech audio bytes."""
        if not text.strip():
            return {"audio": b"", "error": "empty text"}

        # Try Piper first
        audio = self._synthesize_piper(text)
        if audio:
            return {"audio": audio, "engine": "piper"}

        # Fallback: pyttsx3
        audio = self._synthesize_pyttsx3(text)
        if audio:
            return {"audio": audio, "engine": "pyttsx3"}

        return {
            "audio": b"",
            "error": ("No TTS engine available. "
                      "Install Piper or pyttsx3.")
        }

    def _synthesize_piper(self, text: str) -> bytes | None:
        """Use Piper CLI to generate speech."""
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False
            ) as f:
                output_path = f.name

            result = subprocess.run(
                [self.piper_path, "--model", self.voice,
                 "--output_file", output_path],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=30,
            )
            if result.returncode == 0 and os.path.exists(output_path):
                with open(output_path, "rb") as f:
                    audio = f.read()
                os.unlink(output_path)
                return audio
        except FileNotFoundError:
            return None
        except Exception:
            return None
        return None

    def _synthesize_pyttsx3(self, text: str) -> bytes | None:
        """Fallback: pyttsx3 for basic TTS."""
        try:
            if self._pyttsx is None:
                import pyttsx3
                self._pyttsx = pyttsx3.init()
            with tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False
            ) as f:
                output_path = f.name
            self._pyttsx.save_to_file(text, output_path)
            self._pyttsx.runAndWait()
            if os.path.exists(output_path):
                with open(output_path, "rb") as f:
                    audio = f.read()
                os.unlink(output_path)
                return audio
        except ImportError:
            return None
        except Exception:
            return None
        return None

    def is_available(self) -> bool:
        """Check if any TTS engine is available."""
        # Check Piper
        try:
            result = subprocess.run(
                [self.piper_path, "--help"],
                capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, Exception):
            pass
        # Check pyttsx3
        try:
            import pyttsx3
            return True
        except ImportError:
            pass
        return False

    def status(self) -> dict:
        return {
            "engine": "piper",
            "voice": self.voice,
            "available": self.is_available(),
            "fallback": "pyttsx3",
        }
