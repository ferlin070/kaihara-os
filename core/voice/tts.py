"""
TTS - Text-to-Speech with multiple engines.

Priority:
1. Edge Neural TTS (Microsoft) — natural, fluent Bahasa Malaysia
   Voices: ms-MY-YasminNeural (female), ms-MY-OsmanNeural (male)
2. Piper (local) — offline fallback
3. Browser TTS — handled client-side
"""

import os
import subprocess
import tempfile
import hashlib
from typing import Any


class TTS:
    """Multi-engine text-to-speech. Edge Neural for quality Malay."""

    # Voice presets: name -> edge voice id
    VOICES = {
        "yasmin": "ms-MY-YasminNeural",   # Female, fasih BM
        "osman": "ms-MY-OsmanNeural",     # Male, fasih BM
    }

    def __init__(self, voice: str = "en_US-lessig-medium",
                 piper_path: str = "piper"):
        self.voice = voice  # piper model path (fallback)
        self.piper_path = piper_path
        self._pyttsx = None
        self._cache_dir = tempfile.gettempdir()
        self.default_voice = "yasmin"

    async def synthesize_async(self, text: str,
                                voice_name: str = None) -> dict:
        """Synthesize using Edge Neural TTS (async)."""
        if not text.strip():
            return {"audio": b"", "error": "empty text"}

        voice_id = self.VOICES.get(
            voice_name or self.default_voice,
            self.VOICES[self.default_voice]
        )

        # Cache by (voice, text hash)
        key = hashlib.sha256(f"{voice_id}:{text}".encode()).hexdigest()[:16]
        cache_path = os.path.join(self._cache_dir, f"kaihara_tts_{key}.mp3")

        if os.path.exists(cache_path):
            with open(cache_path, "rb") as f:
                return {"audio": f.read(), "engine": "edge-neural",
                        "format": "mp3", "voice": voice_id}

        try:
            import edge_tts
            communicate = edge_tts.Communicate(text, voice_id)
            await communicate.save(cache_path)
            with open(cache_path, "rb") as f:
                audio = f.read()
            return {"audio": audio, "engine": "edge-neural",
                    "format": "mp3", "voice": voice_id}
        except Exception as e:
            # Fallback to sync engines
            result = self.synthesize(text)
            if not result.get("audio"):
                result["error"] = f"edge-tts failed: {e}"
            return result

    def synthesize(self, text: str) -> dict:
        """Sync synthesis — Piper fallback."""
        if not text.strip():
            return {"audio": b"", "error": "empty text"}

        # Try Piper first (sync fallback)
        audio = self._synthesize_piper(text)
        if audio:
            return {"audio": audio, "engine": "piper", "format": "wav"}

        # Fallback: pyttsx3
        audio = self._synthesize_pyttsx3(text)
        if audio:
            return {"audio": audio, "engine": "pyttsx3", "format": "wav"}

        return {
            "audio": b"",
            "error": ("No TTS engine available. "
                      "Install edge-tts or Piper.")
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
        try:
            import edge_tts  # noqa: F401
            return True
        except ImportError:
            pass
        try:
            result = subprocess.run(
                [self.piper_path, "--help"],
                capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                return True
        except (FileNotFoundError, Exception):
            pass
        try:
            import pyttsx3  # noqa: F401
            return True
        except ImportError:
            pass
        return False

    def status(self) -> dict:
        """TTS status for voice pipeline."""
        available = False
        engine = "none"
        try:
            import edge_tts  # noqa: F401
            available = True
            engine = "edge-neural"
        except ImportError:
            pass
        if not available:
            try:
                result = subprocess.run(
                    [self.piper_path, "--help"],
                    capture_output=True, timeout=5,
                )
                if result.returncode == 0:
                    available = True
                    engine = "piper"
            except (FileNotFoundError, Exception):
                pass
        return {
            "engine": engine,
            "voice": self.VOICES.get(self.default_voice, self.voice),
            "available": available,
            "fallback": "pyttsx3",
        }
