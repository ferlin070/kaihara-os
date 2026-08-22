"""
Voice Pipeline - full voice interaction loop (Jarvis concept).
Wake word -> record -> STT -> Kaihara agent -> TTS -> speaker.

Flow:
  1. Always listening for wake word "kaihara"
  2. On wake: record command (3-10s)
  3. STT: Whisper transcribes audio
  4. Agent: Kaihara processes text
  5. TTS: Piper speaks response
  6. Back to listening
"""

import asyncio
import json
from typing import Any, Callable

from core.voice.stt import STT
from core.voice.tts import TTS
from core.voice.wake_word import WakeWord


class VoicePipeline:
    """Full voice interaction pipeline."""

    def __init__(self, config: dict, command_center=None):
        voice_cfg = config.get("voice", {})
        self.enabled = voice_cfg.get("enabled", False)
        self.wake_word_str = voice_cfg.get("wake_word", "kaihara")
        self.stt = STT(voice_cfg.get("stt_model", "base"))
        self.tts = TTS(
            voice=voice_cfg.get("tts_voice", "en_US-lessig-medium"),
            piper_path=voice_cfg.get("piper_path", "piper"),
        )
        self.wake = WakeWord(self.wake_word_str)
        self.command_center = command_center
        self._listening = False
        self._on_status: Callable | None = None
        self._on_message: Callable | None = None

    def set_callbacks(self, on_status=None, on_message=None):
        self._on_status = on_status
        self._on_message = on_message

    async def start(self):
        """Start the voice loop."""
        if not self.enabled:
            return {"error": "Voice not enabled in config"}
        if not self._check_available():
            return {"error": "Voice components not available"}
        self._listening = True
        await self._notify_status("listening")
        await self._listen_loop()
        return {"status": "started"}

    def stop(self):
        self._listening = False

    async def _listen_loop(self):
        """Main loop: listen for wake word, process command, respond."""
        while self._listening:
            try:
                # 1. Listen for wake word
                audio = await self._record_chunk(duration=2)
                if not audio:
                    continue
                detected = self.wake.detect(audio)
                if not detected.get("detected"):
                    continue
                await self._notify_status("awake")
                await self._notify_message("kaihara", "Yes?")

                # 2. Record command
                await self._notify_status("recording")
                command_audio = await self._record_until_silence()
                if not command_audio:
                    await self._notify_status("listening")
                    continue

                # 3. STT
                await self._notify_status("thinking")
                result = self.stt.transcribe(command_audio)
                text = result.get("text", "").strip()
                if not text:
                    await self._notify_status("listening")
                    continue

                # 4. Send to Kaihara
                await self._notify_message("user", text)
                if self.command_center:
                    response = await self.command_center.handle_input(
                        source="voice", message=text
                    )
                    reply = response.get("response", "")
                else:
                    reply = "Command center not available."

                await self._notify_message("kaihara", reply)

                # 5. TTS
                await self._notify_status("speaking")
                tts_result = self.tts.synthesize(reply)
                if tts_result.get("audio"):
                    await self._play_audio(tts_result["audio"])

                # 6. Back to listening
                await self._notify_status("listening")
            except Exception as e:
                await self._notify_status("error")
                await self._notify_message("kaihara", f"Error: {e}")
                await self._notify_status("listening")

    async def process_text(self, text: str) -> dict:
        """Process text input and speak response (no wake word needed)."""
        await self._notify_status("thinking")
        if self.command_center:
            response = await self.command_center.handle_input(
                source="voice", message=text
            )
            reply = response.get("response", "")
        else:
            reply = "Command center not available."

        # TTS
        if self.tts.is_available():
            await self._notify_status("speaking")
            tts_result = self.tts.synthesize(reply)
            if tts_result.get("audio"):
                await self._play_audio(tts_result["audio"])

        await self._notify_status("idle")
        return {"text": reply, "spoken": tts_result.get("engine")}

    async def transcribe_audio(self, audio_bytes: bytes) -> dict:
        """Transcribe audio to text (for dashboard voice input)."""
        await self._notify_status("thinking")
        result = self.stt.transcribe(audio_bytes)
        await self._notify_status("idle")
        return result

    def _check_available(self) -> bool:
        return self.stt.is_available() and self.tts.is_available()

    async def _record_chunk(self, duration: int = 2) -> bytes:
        """Record audio chunk (stub - implement with pyaudio/sounddevice)."""
        return b""

    async def _record_until_silence(self,
                                      max_duration: int = 10) -> bytes:
        """Record until silence detected (stub)."""
        return b""

    async def _play_audio(self, audio_bytes: bytes):
        """Play audio bytes (stub - implement with pyaudio/sounddevice)."""
        pass

    async def _notify_status(self, status: str):
        if self._on_status:
            self._on_status(status)

    async def _notify_message(self, role: str, text: str):
        if self._on_message:
            self._on_message(role, text)

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "wake_word": self.wake_word_str,
            "listening": self._listening,
            "stt": self.stt.status(),
            "tts": self.tts.status(),
            "wake": self.wake.status(),
            "available": self._check_available(),
        }
