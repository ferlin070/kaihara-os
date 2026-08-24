"""
Kaihara Channels Runner — standalone process for CT 205.
Connects to Kaihara Core API (CT 203) over HTTP.
Currently: Telegram. WhatsApp/Email can be added here later.
"""

import os
import sys
import asyncio
import httpx

sys.path.insert(0, "/opt")
from tg_format import md_to_telegram_html, wrap_reply

# --- Config ---
CORE_API = os.environ.get("KAIHARA_API", "http://192.168.1.211:7000")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ALLOWED = {i.strip() for i in os.environ.get(
    "TELEGRAM_ALLOWED_IDS", "8275355102").split(",") if i.strip()}
MAX_REPLY = 4000  # Telegram message limit


async def ask_kaihara(text: str, conv_id: str) -> dict:
    """Send message to Kaihara core. Returns full response dict."""
    async with httpx.AsyncClient(timeout=300) as client:
        r = await client.post(f"{CORE_API}/api/chat", json={
            "message": text, "source": "telegram", "conv_id": conv_id,
        })
        r.raise_for_status()
        return r.json()


async def main():
    from telegram import Update
    from telegram.ext import Application, MessageHandler, filters

    app = Application.builder().token(BOT_TOKEN).build()

    async def handle(update: Update, context):
        if not (update.message and update.message.text):
            return
        chat_id = str(update.message.chat_id)
        if ALLOWED and chat_id not in ALLOWED:
            await update.message.reply_text("⛔ Unauthorized. This bot is private.")
            return
        conv = f"telegram_{chat_id}"

        async def typing():
            try:
                while True:
                    await app.bot.send_chat_action(
                        chat_id=int(chat_id), action="typing")
                    await asyncio.sleep(4)
            except asyncio.CancelledError:
                pass

        task = asyncio.create_task(typing())
        try:
            res = await ask_kaihara(update.message.text, conv)
            raw = res.get("response", "")
            route = res.get("route", "")
            provider = res.get("provider", "")

            # Format cantik macam dashboard (tables/headers/bold)
            formatted = wrap_reply(
                md_to_telegram_html(raw),
                agent="Kaihara",
                route=route,
                provider=provider,
            )
            for i in range(0, len(formatted), MAX_REPLY):
                await update.message.reply_text(
                    formatted[i:i + MAX_REPLY], parse_mode="HTML")
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error: {e}")
        finally:
            task.cancel()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    print(f"Kaihara channels runner: telegram -> {CORE_API}", flush=True)
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
