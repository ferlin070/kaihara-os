"""
Step 4: Outreach via Email & WhatsApp
Generates personalized outreach messages and sends them.
"""

import json
import logging

from core.workflow.steps.base_step import BusinessStep

logger = logging.getLogger("kaihara.workflow.outreach")


class OutreachStep(BusinessStep):
    """Generate and send personalized outreach via email/WhatsApp."""

    NAME = "outreach"
    AGENT = "marketing"
    MAX_RETRIES = 1
    REQUIRES_APPROVAL = True  # CRITICAL: Needs approval before sending

    def get_description(self) -> str:
        return "Hantar outreach email/WhatsApp kepada perniagaan"

    async def run(self, context: dict) -> dict:
        demos = context.get("generate_demo_result", {}).get("demos", [])
        analyzed = context.get("analyze_business_result", {}).get("analyzed", [])
        channel = context.get("outreach_channel", "email")
        sender_name = context.get("sender_name", "Kaihara")

        # Match demos to analyzed businesses
        targets = []
        demo_map = {d["name"]: d for d in demos if d.get("deployed")}
        for biz in analyzed:
            demo = demo_map.get(biz["name"])
            if demo:
                targets.append({**biz, "demo_url": demo.get("url", "")})

        if not targets:
            # Use analyzed businesses even without demos
            targets = analyzed[:5]

        if not targets:
            return {"output": {"sent": [], "message": "Tiada target untuk outreach"}}

        from core.tools.email_templates import generate_outreach_email
        from core.tools.email_templates import generate_whatsapp_message

        sent = []
        for target in targets:
            name = target.get("name", "Business Owner")
            demo_url = target.get("demo_url", "")
            phone = target.get("phone", "")
            email_addr = target.get("contacts", {}).get("email", "")
            business_type = target.get("business_type", "general")

            message_data = {
                "business_name": name,
                "demo_url": demo_url,
                "business_type": business_type,
            }

            try:
                if channel == "email" and email_addr:
                    content = generate_outreach_email(**message_data)
                    result = await self._send_email(email_addr, content, name)
                    sent.append({
                        "name": name,
                        "channel": "email",
                        "recipient": email_addr,
                        "success": result.get("ok", False),
                        "error": result.get("error", ""),
                    })
                elif channel == "whatsapp" and phone:
                    content = generate_whatsapp_message(**message_data)
                    result = await self._send_whatsapp(phone, content)
                    sent.append({
                        "name": name,
                        "channel": "whatsapp",
                        "recipient": phone,
                        "success": result.get("ok", False),
                        "error": result.get("error", ""),
                    })
                elif channel == "both":
                    results = {}
                    if email_addr:
                        email_content = generate_outreach_email(**message_data)
                        results["email"] = await self._send_email(
                            email_addr, email_content, name
                        )
                    if phone:
                        wa_content = generate_whatsapp_message(**message_data)
                        results["whatsapp"] = await self._send_whatsapp(phone, wa_content)

                    success = any(r.get("ok") for r in results.values())
                    sent.append({
                        "name": name,
                        "channel": "both",
                        "success": success,
                        "results": results,
                    })
                else:
                    sent.append({
                        "name": name,
                        "channel": channel,
                        "success": False,
                        "error": f"No {channel} contact available",
                    })
            except Exception as e:
                logger.error(f"Outreach failed for {name}: {e}")
                sent.append({
                    "name": name,
                    "channel": channel,
                    "success": False,
                    "error": str(e),
                })

        successful = [s for s in sent if s.get("success")]

        return {
            "output": {
                "sent": sent,
                "total_targets": len(targets),
                "total_sent": len(successful),
                "channel": channel,
            }
        }

    async def _send_email(self, recipient: str, content: dict,
                          business_name: str) -> dict:
        """Send email via EmailChannel."""
        try:
            from core.channels.email_channel import EmailChannel
            channel = EmailChannel(config={})
            msg_text = f"{content.get('subject', '')}\n\n{content.get('body', '')}"
            result = await channel.send(recipient, msg_text)
            return {"ok": True, "result": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def _send_whatsapp(self, phone: str, content: dict) -> dict:
        """Send WhatsApp via WhatsAppChannel."""
        try:
            from core.channels.whatsapp import WhatsAppChannel
            channel = WhatsAppChannel(config={})
            result = await channel.send(phone, content.get("message", ""))
            return {"ok": True, "result": result}
        except Exception as e:
            return {"ok": False, "error": str(e)}
