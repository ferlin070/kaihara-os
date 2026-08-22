"""
Base Channel - abstract interface for all messaging channels.
Two-way: inbound (receive from user) + outbound (send to user).
"""

from abc import ABC, abstractmethod
from typing import Any, Callable


class BaseChannel(ABC):
    """Abstract base for all channels (Telegram, WhatsApp, Email, etc)."""

    CHANNEL_TYPE = "base"

    def __init__(self, config: dict, command_center=None):
        self.config = config
        self.command_center = command_center
        self._enabled = config.get("enabled", False)
        self._running = False
        self._on_message: Callable | None = None

    @abstractmethod
    async def start(self) -> dict:
        """Start listening for incoming messages."""
        pass

    @abstractmethod
    async def stop(self) -> dict:
        """Stop the channel."""
        pass

    @abstractmethod
    async def send(self, recipient: str, text: str,
                    attachments: list = None) -> dict:
        """Send a message to a recipient."""
        pass

    async def receive(self, raw_message: dict) -> dict:
        """Process an incoming message and route to Command Center."""
        parsed = self._parse_inbound(raw_message)
        if not parsed or not parsed.get("text"):
            return {"error": "Could not parse message"}

        if self.command_center:
            result = await self.command_center.handle_input(
                source=self.CHANNEL_TYPE,
                message=parsed["text"],
                conv_id=parsed.get("conv_id", "default"),
            )
            # Send response back to user
            response_text = result.get("response", "")
            if response_text and parsed.get("sender"):
                await self.send(parsed["sender"], response_text)
            return result
        return {"text": parsed["text"], "response": "no command center"}

    @abstractmethod
    def _parse_inbound(self, raw: dict) -> dict | None:
        """Parse raw incoming message to {sender, text, conv_id}."""
        pass

    def set_callback(self, callback: Callable):
        self._on_message = callback

    def is_enabled(self) -> bool:
        return self._enabled

    def is_running(self) -> bool:
        return self._running

    def status(self) -> dict:
        return {
            "type": self.CHANNEL_TYPE,
            "enabled": self._enabled,
            "running": self._running,
        }
