"""
Step 8: Close & Payment
Create invoices and track payment.
"""

import json
import logging

from core.workflow.steps.base_step import BusinessStep

logger = logging.getLogger("kaihara.workflow.close_payment")


class ClosePaymentStep(BusinessStep):
    """Create invoices and track payment from clients."""

    NAME = "close_payment"
    AGENT = "marketing"
    MAX_RETRIES = 1
    REQUIRES_APPROVAL = False

    def get_description(self) -> str:
        return "Buat invoice dan trace bayaran client"

    async def run(self, context: dict) -> dict:
        deploy_result = context.get("deploy_site_result", {})
        deployed = deploy_result.get("deployed", [])
        deployed = [d for d in deployed if d.get("deployed")]

        win_result = context.get("win_job_result", {})
        converted = win_result.get("converted", [])

        if not deployed and not converted:
            return {"output": {"invoices": [], "message": "Tiada client untuk invoice"}}

        from core.marketing.invoices import create_invoice

        invoices = []
        # Create invoices for deployed sites
        for site in deployed:
            client_name = site.get("client_name", "")
            vercel_url = site.get("url", "")

            try:
                invoice = create_invoice(
                    client_name=client_name,
                    items=[
                        {
                            "description": f"Website development — {client_name}",
                            "quantity": 1,
                            "unit_price": 2500.00,
                        },
                        {
                            "description": "Domain & hosting setup",
                            "quantity": 1,
                            "unit_price": 500.00,
                        },
                    ],
                    currency="MYR",
                    tax_rate=0.06,  # SST 6%
                    notes=f"Website: {vercel_url}",
                )
                invoices.append({
                    "client_name": client_name,
                    "invoice_id": invoice.get("id") if isinstance(invoice, dict) else None,
                    "invoice_number": invoice.get("invoice_number", "") if isinstance(invoice, dict) else "",
                    "total": invoice.get("total", 0) if isinstance(invoice, dict) else 0,
                    "currency": "MYR",
                    "status": "sent",
                    "url": vercel_url,
                })
            except Exception as e:
                logger.error(f"Invoice creation failed for {client_name}: {e}")
                invoices.append({
                    "client_name": client_name,
                    "status": "failed",
                    "error": str(e),
                })

        total_revenue = sum(inv.get("total", 0) for inv in invoices if inv.get("status") == "sent")

        return {
            "output": {
                "invoices": invoices,
                "total_invoices": len(invoices),
                "total_revenue": total_revenue,
                "currency": "MYR",
                "workflow_complete": True,
                "summary": {
                    "businesses_found": context.get("find_businesses_result", {}).get("total_found", 0),
                    "demos_generated": context.get("generate_demo_result", {}).get("total_generated", 0),
                    "outreach_sent": context.get("outreach_result", {}).get("total_sent", 0),
                    "clients_converted": len(converted),
                    "sites_deployed": len(deployed),
                    "invoices_created": len([i for i in invoices if i.get("status") == "sent"]),
                    "total_revenue": total_revenue,
                },
            }
        }
