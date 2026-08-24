"""
Notify Tools — send messages via configured channels.
Telegram: uses TELEGRAM_BOT_TOKEN + default chat from TELEGRAM_ALLOWED_IDS.
"""

import os
import json
from typing import Any

import httpx


def _get_token() -> str | None:
    return os.environ.get("TELEGRAM_BOT_TOKEN") or None


def _default_chat_ids() -> list[str]:
    raw = os.environ.get("TELEGRAM_ALLOWED_IDS", "")
    return [i.strip() for i in raw.split(",") if i.strip()]


def send_telegram_message(message: str, chat_id: str | None = None) -> dict:
    """Send a message via Telegram Bot API."""
    token = _get_token()
    if not token:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN not set"}

    chat_ids = [chat_id] if chat_id else _default_chat_ids()
    if not chat_ids:
        return {"ok": False, "error": "No chat_id provided or allowed"}

    results = []
    for cid in chat_ids:
        try:
            r = httpx.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": int(cid), "text": message[:4000],
                      "parse_mode": "Markdown"},
                timeout=15,
            )
            d = r.json()
            ok = bool(d.get("ok"))
            results.append({
                "chat_id": cid, "ok": ok,
                "error": d.get("description", "") if not ok else "",
                "message_id": d.get("result", {}).get("message_id"),
            })
        except Exception as e:
            results.append({"chat_id": cid, "ok": False, "error": str(e)})

    sent = sum(1 for r in results if r["ok"])
    return {
        "ok": sent > 0,
        "sent": sent,
        "total": len(results),
        "details": results,
    }


def telegram_status() -> dict:
    token = _get_token()
    if not token:
        return {"configured": False}
    try:
        r = httpx.get(
            f"https://api.telegram.org/bot{token}/getMe", timeout=10)
        d = r.json()
        me = d.get("result", {})
        return {
            "configured": True,
            "bot_username": f"@{me.get('username')}",
            "bot_name": me.get("first_name"),
            "allowed_chat_ids": _default_chat_ids(),
        }
    except Exception as e:
        return {"configured": True, "error": str(e)}
