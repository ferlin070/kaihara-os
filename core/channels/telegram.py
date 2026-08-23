"""
Telegram Channel - Telegram bot integration.
Uses python-telegram-bot library. Two-way: receive + send.
"""

import asyncio
import os
from typing import Any

from core.channels.base import BaseChannel


class TelegramChannel(BaseChannel):
    """Telegram bot channel for Kaihara."""

    CHANNEL_TYPE = "telegram"

    def __init__(self, config: dict, command_center=None):
        super().__init__(config, command_center)
        # Token: config first, then env var fallback
        self.bot_token = config.get("bot_token") or os.environ.get(
            "TELEGRAM_BOT_TOKEN", "")
        # Security: only allow listed chat IDs (empty = allow all, not recommended)
        raw_ids = config.get("allowed_chat_ids", [])
        if isinstance(raw_ids, str):
            raw_ids = [i.strip() for i in raw_ids.split(",") if i.strip()]
        self.allowed_chat_ids = {str(i) for i in raw_ids}
        self._bot = None
        self._app = None
        self._task = None

    async def start(self) -> dict:
        """Start Telegram bot polling."""
        if not self._enabled:
            return {"error": "Telegram channel not enabled in config"}
        if not self.bot_token:
            return {"error": "No bot_token configured. Set TELEGRAM_BOT_TOKEN."}

        try:
            from telegram import Update
            from telegram.ext import (
                Application, CommandHandler, MessageHandler, filters
            )
        except ImportError:
            return {
                "error": "python-telegram-bot not installed. "
                          "Install: pip install python-telegram-bot"
            }

        try:
            self._app = Application.builder().token(self.bot_token).build()

            async def handle_message(update: Update, context):
                if not (update.message and update.message.text):
                    return
                chat_id = str(update.message.chat_id)
                # Security: enforce allowlist
                if self.allowed_chat_ids and chat_id not in self.allowed_chat_ids:
                    await update.message.reply_text(
                        "⛔ Unauthorized. This bot is private."
                    )
                    return
                raw = {
                    "chat_id": update.message.chat_id,
                    "text": update.message.text,
                    "username": update.message.from_user.username
                        if update.message.from_user else "unknown",
                }
                # Send typing indicator while thinking
                async def _typing():
                    try:
                        while True:
                            await self._app.bot.send_chat_action(
                                chat_id=int(chat_id), action="typing")
                            await asyncio.sleep(4)
                    except asyncio.CancelledError:
                        pass
                typing_task = asyncio.create_task(_typing())
                try:
                    await self.receive(raw)
                finally:
                    typing_task.cancel()

            self._app.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
            )
            self._running = True
            await self._app.initialize()
            await self._app.start()
            self._task = asyncio.create_task(self._app.updater.start_polling())
            return {"status": "started", "type": self.CHANNEL_TYPE}
        except Exception as e:
            self._running = False
            return {"error": str(e)}

    async def stop(self) -> dict:
        """Stop Telegram bot."""
        if self._app:
            try:
                await self._app.updater.stop()
                await self._app.stop()
                await self._app.shutdown()
            except Exception:
                pass
        self._running = False
        return {"status": "stopped", "type": self.CHANNEL_TYPE}

    async def send(self, recipient: str, text: str,
                    attachments: list = None) -> dict:
        """Send message to Telegram chat."""
        if not self._app:
            return {"error": "Bot not started"}
        try:
            await self._app.bot.send_message(chat_id=int(recipient), text=text)
            return {"status": "sent", "recipient": recipient}
        except Exception as e:
            return {"error": str(e)}

    def _parse_inbound(self, raw: dict) -> dict | None:
        """Parse Telegram update to standard format."""
        if not raw.get("text"):
            return None
        return {
            "sender": str(raw.get("chat_id", "")),
            "text": raw["text"],
            "conv_id": f"telegram_{raw.get('chat_id', 'unknown')}",
            "username": raw.get("username", ""),
        }

    def status(self) -> dict:
        return {
            **super().status(),
            "has_token": bool(self.bot_token),
            "bot_connected": self._app is not None,
            "allowed_users": len(self.allowed_chat_ids),
            "locked": bool(self.allowed_chat_ids),
        }
