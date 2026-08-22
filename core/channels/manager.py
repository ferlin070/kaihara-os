"""
Channel Manager - start/stop/status for all channels.
"""

import asyncio
from typing import Any

from core.channels.base import BaseChannel
from core.channels.telegram import TelegramChannel
from core.channels.whatsapp import WhatsAppChannel
from core.channels.email_channel import EmailChannel


class ChannelManager:
    """Manage all messaging channels."""

    def __init__(self, config: dict, command_center=None):
        self.config = config
        self.command_center = command_center
        self.channels: dict[str, BaseChannel] = {}
        self._init_channels()

    def _init_channels(self):
        ch_cfg = self.config.get("channel", {})
        if ch_cfg.get("telegram", {}).get("enabled"):
            self.channels["telegram"] = TelegramChannel(
                ch_cfg["telegram"], self.command_center
            )
        if ch_cfg.get("whatsapp", {}).get("enabled"):
            self.channels["whatsapp"] = WhatsAppChannel(
                ch_cfg["whatsapp"], self.command_center
            )
        if ch_cfg.get("email", {}).get("enabled"):
            self.channels["email"] = EmailChannel(
                ch_cfg["email"], self.command_center
            )

    async def start_all(self) -> dict:
        """Start all enabled channels."""
        results = {}
        for name, channel in self.channels.items():
            results[name] = await channel.start()
        return results

    async def stop_all(self) -> dict:
        """Stop all channels."""
        results = {}
        for name, channel in self.channels.items():
            results[name] = await channel.stop()
        return results

    async def start_channel(self, name: str) -> dict:
        """Start a specific channel."""
        channel = self.channels.get(name)
        if not channel:
            return {"error": f"Channel '{name}' not found"}
        return await channel.start()

    async def stop_channel(self, name: str) -> dict:
        """Stop a specific channel."""
        channel = self.channels.get(name)
        if not channel:
            return {"error": f"Channel '{name}' not found"}
        return await channel.stop()

    async def send_to_channel(self, name: str, recipient: str,
                               text: str) -> dict:
        """Send a message through a specific channel."""
        channel = self.channels.get(name)
        if not channel:
            return {"error": f"Channel '{name}' not found"}
        return await channel.send(recipient, text)

    def status(self) -> dict:
        return {
            name: channel.status()
            for name, channel in self.channels.items()
        }

    def list_channels(self) -> list[str]:
        return list(self.channels.keys())
