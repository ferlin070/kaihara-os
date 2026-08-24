"""
Email Channel - SMTP + IMAP integration.
Inbound: IMAP polling for incoming emails.
Outbound: SMTP for sending replies.
"""

import asyncio
import email
from email.mime.text import MIMEText
from typing import Any
import os

from core.channels.base import BaseChannel


class EmailChannel(BaseChannel):
    """Email channel with IMAP polling and SMTP sending."""

    CHANNEL_TYPE = "email"

    def __init__(self, config: dict, command_center=None):
        super().__init__(config, command_center)
        self.smtp_host = config.get("smtp_host") or os.environ.get(
            "SMTP_HOST", "")
        self.smtp_port = config.get("smtp_port", 587)
        self.imap_host = config.get("imap_host") or os.environ.get(
            "IMAP_HOST", "")
        self.imap_port = config.get("imap_port", 993)
        self.username = (config.get("username") or
                         os.environ.get("EMAIL_USERNAME", ""))
        self.password = (config.get("password") or
                         os.environ.get("EMAIL_PASSWORD", ""))
        self._poll_task = None
        self._poll_interval = 30

    async def start(self) -> dict:
        if not self._enabled:
            return {"error": "Email channel not enabled in config"}
        if not self.imap_host:
            return {"error": "No IMAP host configured"}
        self._running = True
        self._poll_task = asyncio.create_task(self._poll_loop())
        return {"status": "started", "type": self.CHANNEL_TYPE}

    async def _poll_loop(self):
        import imaplib
        while self._running:
            try:
                conn = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
                conn.login(self.username, self.password)
                conn.select("inbox")
                _, data = conn.search(None, "UNSEEN")
                for num in data[0].split():
                    _, msg_data = conn.fetch(num, "(RFC822)")
                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    parsed = self._parse_email(msg)
                    if parsed:
                        conn.store(num, "+FLAGS", "\\Seen")
                        await self.receive(parsed)
                conn.logout()
            except Exception:
                pass
            await asyncio.sleep(self._poll_interval)

    async def stop(self) -> dict:
        self._running = False
        if self._poll_task:
            self._poll_task.cancel()
        return {"status": "stopped", "type": self.CHANNEL_TYPE}

    async def send(self, recipient: str, text: str,
                    attachments: list = None) -> dict:
        if not self.smtp_host:
            return {"error": "No SMTP host configured"}
        try:
            msg = MIMEText(text)
            msg["From"] = self.username
            msg["To"] = recipient
            msg["Subject"] = "Kaihara Response"
            try:
                import aiosmtplib
                await aiosmtplib.send(
                    msg, hostname=self.smtp_host, port=self.smtp_port,
                    username=self.username, password=self.password,
                    start_tls=True,
                )
            except ImportError:
                import smtplib
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as s:
                    s.starttls()
                    s.login(self.username, self.password)
                    s.send_message(msg)
            return {"status": "sent", "recipient": recipient}
        except Exception as e:
            return {"error": str(e)}

    def _parse_inbound(self, raw: dict | email.message.Message) -> dict | None:
        if isinstance(raw, dict):
            return {
                "sender": raw.get("from", ""),
                "text": raw.get("text", ""),
                "conv_id": f"email_{raw.get('from', 'unknown')}",
            }
        return self._parse_email_impl(raw)

    def _parse_email(self, msg: email.message.Message) -> dict | None:
        sender = msg.get("From", "")
        subject = msg.get("Subject", "")
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode("utf-8", errors="ignore")
                        break
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="ignore")
        if not body:
            return None
        text = f"Subject: {subject}\n\n{body}" if subject else body
        return {
            "sender": sender,
            "text": text,
            "conv_id": f"email_{sender}",
            "subject": subject,
        }

    def status(self) -> dict:
        return {
            **super().status(),
            "has_smtp": bool(self.smtp_host),
            "has_imap": bool(self.imap_host),
            "username": self.username or "not set",
        }
