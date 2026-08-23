"""
NotificationService - Outbound notification dispatch with routing,
scheduling, and multi-channel support.

Provides a clean API for agents to send notifications.
"""

import asyncio
from datetime import datetime
from typing import Any

from core.channels.manager import ChannelManager


class NotificationService:
    """Dispatch notifications across channels with routing and priorities."""

    PRIORITY_LEVELS = {"low": 0, "normal": 1, "high": 2, "urgent": 3}

    def __init__(self, channel_manager: ChannelManager, config: dict = None):
        self.channels = channel_manager
        self.config = config or {}
        self._queue: list[dict] = []
        self._history: list[dict] = []
        self._routing: dict[str, list[str]] = self.config.get("routing", {
            "urgent": ["telegram", "email"],
            "high": ["telegram"],
            "normal": ["telegram"],
            "low": [],
        })
        self._quiet_hours_start = self.config.get("quiet_hours_start", 23)
        self._quiet_hours_end = self.config.get("quiet_hours_end", 7)
        self._rate_limit_per_hour = self.config.get("rate_limit_per_hour", 30)
        self._sent_this_hour: list[datetime] = []

    def _is_quiet_hours(self) -> bool:
        """Check if we're in quiet hours."""
        hour = datetime.now().hour
        if self._quiet_hours_start > self._quiet_hours_end:
            return hour >= self._quiet_hours_start or hour < self._quiet_hours_end
        return self._quiet_hours_start <= hour < self._quiet_hours_end

    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = datetime.now()
        cutoff = now.timestamp() - 3600
        self._sent_this_hour = [t for t in self._sent_this_hour if t.timestamp() > cutoff]
        return len(self._sent_this_hour) < self._rate_limit_per_hour

    async def send(self, message: str, priority: str = "normal",
                   title: str = "", channels: list[str] = None,
                   recipient: str = None, quiet_ok: bool = False) -> dict:
        """
        Send a notification.

        Args:
            message: Notification text
            priority: low, normal, high, urgent
            title: Optional title/subject
            channels: Override routing — send to specific channels
            recipient: Recipient for channels that need it
            quiet_ok: Send even during quiet hours
        """
        priority = priority if priority in self.PRIORITY_LEVELS else "normal"

        # Quiet hours check
        if not quiet_ok and self._is_quiet_hours() and priority not in ("high", "urgent"):
            return {"status": "deferred", "reason": "quiet_hours"}

        # Rate limit check
        if not self._check_rate_limit() and priority not in ("urgent",):
            return {"status": "rate_limited"}

        # Determine target channels
        target_channels = channels or self._routing.get(priority, ["telegram"])
        if not target_channels:
            return {"status": "no_channels"}

        # Format message
        prefix = ""
        if priority in ("high", "urgent"):
            prefix = "🚨 " if priority == "urgent" else "⚠️ "
        if title:
            text = f"{prefix}**{title}**\n\n{message}"
        else:
            text = f"{prefix}{message}"

        # Dispatch to channels
        results = {}
        for ch_name in target_channels:
            ch = self.channels.channels.get(ch_name)
            if ch and ch.is_enabled() and ch.is_running():
                try:
                    target = recipient or self.config.get(f"{ch_name}_default_recipient", "")
                    if target:
                        result = await ch.send(target, text)
                        results[ch_name] = result
                    else:
                        results[ch_name] = {"error": "no_recipient"}
                except Exception as e:
                    results[ch_name] = {"error": str(e)}
            else:
                results[ch_name] = {"error": "channel_unavailable"}

        # Record
        self._sent_this_hour.append(datetime.now())
        entry = {
            "message": message,
            "priority": priority,
            "title": title,
            "channels": target_channels,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }
        self._history.append(entry)
        if len(self._history) > 100:
            self._history = self._history[-100:]

        sent_to = [ch for ch, r in results.items() if "error" not in r]
        return {"status": "sent", "channels": sent_to, "results": results}

    async def alert(self, message: str, title: str = "Alert") -> dict:
        """Send a high-priority alert."""
        return await self.send(message, priority="high", title=title, quiet_ok=True)

    async def urgent(self, message: str, title: str = "Urgent") -> dict:
        """Send an urgent notification (always delivered)."""
        return await self.send(message, priority="urgent", title=title, quiet_ok=True)

    async def info(self, message: str, title: str = "") -> dict:
        """Send a normal info notification."""
        return await self.send(message, priority="normal", title=title)

    def status(self) -> dict:
        """Get notification service status."""
        now = datetime.now()
        cutoff = now.timestamp() - 3600
        recent = [t for t in self._sent_this_hour if t.timestamp() > cutoff]

        return {
            "quiet_hours": self._is_quiet_hours(),
            "rate_limit": {
                "max_per_hour": self._rate_limit_per_hour,
                "sent_this_hour": len(recent),
                "remaining": max(0, self._rate_limit_per_hour - len(recent)),
            },
            "routing": self._routing,
            "history_count": len(self._history),
            "last_5": self._history[-5:] if self._history else [],
        }

    def update_routing(self, routing: dict):
        """Update channel routing preferences."""
        self._routing.update(routing)
        return {"status": "updated", "routing": self._routing}
