"""
WhatsApp Channel - WhatsApp Web integration via Baileys (Node.js).
Two-way: receive + send. Uses subprocess to run Node.js Baileys bridge.
"""

import asyncio
import json
import subprocess
import os
from typing import Any

from core.channels.base import BaseChannel


class WhatsAppChannel(BaseChannel):
    """WhatsApp Web channel using Baileys (Node.js)."""

    CHANNEL_TYPE = "whatsapp"

    def __init__(self, config: dict, command_center=None):
        super().__init__(config, command_center)
        self.bridge_script = config.get("bridge_script",
                                         "core/channels/whatsapp_bridge/whatsapp_bridge.js")
        self._process = None
        self._stdout_task = None
        self._qr_code = None

    async def start(self) -> dict:
        """Start WhatsApp bridge subprocess."""
        if not self._enabled:
            return {"error": "WhatsApp channel not enabled in config"}

        bridge_path = os.path.join(
            os.path.dirname(__file__), "whatsapp_bridge", "whatsapp_bridge.js"
        )
        if not os.path.exists(bridge_path):
            return {
                "error": "WhatsApp bridge script not found. "
                          "Install Baileys: npm install @whiskeysockets/baileys"
            }

        try:
            self._process = await asyncio.create_subprocess_exec(
                "node", bridge_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            self._running = True
            self._stdout_task = asyncio.create_task(self._read_messages())
            return {"status": "started", "type": self.CHANNEL_TYPE}
        except FileNotFoundError:
            return {
                "error": "Node.js not installed. "
                          "Install Node.js to use WhatsApp channel."
            }
        except Exception as e:
            self._running = False
            return {"error": str(e)}

    async def _read_messages(self):
        """Read messages from bridge stdout."""
        if not self._process or not self._process.stdout:
            return
        while self._running and self._process:
            try:
                line = await self._process.stdout.readline()
                if not line:
                    break
                data = json.loads(line.decode().strip())
                msg_type = data.get("type")
                if msg_type == "message":
                    await self.receive(data)
                elif msg_type == "qr":
                    self._qr_code = data.get("qr")
                elif msg_type == "status":
                    if data.get("status") == "connected":
                        self._qr_code = None
                elif msg_type == "error":
                    self._last_error = data.get("error")
            except Exception:
                continue

    async def stop(self) -> dict:
        """Stop WhatsApp bridge."""
        if self._process:
            try:
                self._process.terminate()
                await self._process.wait()
            except Exception:
                pass
        self._running = False
        return {"status": "stopped", "type": self.CHANNEL_TYPE}

    async def send(self, recipient: str, text: str,
                    attachments: list = None) -> dict:
        """Send message via WhatsApp bridge stdin."""
        if not self._process or not self._process.stdin:
            return {"error": "WhatsApp bridge not running"}
        try:
            msg = json.dumps({
                "type": "send",
                "recipient": recipient,
                "text": text,
            })
            self._process.stdin.write(msg.encode() + b"\n")
            await self._process.stdin.drain()
            return {"status": "sent", "recipient": recipient}
        except Exception as e:
            return {"error": str(e)}

    def _parse_inbound(self, raw: dict) -> dict | None:
        """Parse WhatsApp message to standard format."""
        if not raw.get("text"):
            return None
        return {
            "sender": raw.get("from", ""),
            "text": raw["text"],
            "conv_id": f"whatsapp_{raw.get('from', 'unknown')}",
        }

    def status(self) -> dict:
        return {
            **super().status(),
            "bridge_running": self._process is not None,
            "qr_pending": self._qr_code is not None,
            "qr": self._qr_code,
            "last_error": getattr(self, "_last_error", None),
        }
