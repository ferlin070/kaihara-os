"""
Step 7: Deploy Site
Deploy the final website to Vercel for production.
Uses nakhodacloud.top for demo, Vercel for production.
"""

import json
import logging
import subprocess

from core.workflow.steps.base_step import BusinessStep

logger = logging.getLogger("kaihara.workflow.deploy_site")


class DeploySiteStep(BusinessStep):
    """Deploy client website to Vercel for production."""

    NAME = "deploy_site"
    AGENT = "deploy"
    MAX_RETRIES = 2
    REQUIRES_APPROVAL = True  # CRITICAL: Needs approval before deploying

    def get_description(self) -> str:
        return "Deploy website client ke Vercel (production)"

    async def run(self, context: dict) -> dict:
        build_result = context.get("build_project_result", {})
        ready_sites = build_result.get("built", [])
        ready_sites = [s for s in ready_sites if s.get("status") == "ready_to_deploy"]

        if not ready_sites:
            return {"output": {"deployed": [], "message": "Tiada site untuk deploy"}}

        from core.tools.deploy_tools import deploy_landing

        deployed = []
        for site in ready_sites:
            client_name = site.get("client_name", "")
            html = site.get("html", "")

            if not html:
                deployed.append({
                    "client_name": client_name,
                    "deployed": False,
                    "error": "No HTML content",
                })
                continue

            try:
                # Deploy to Vercel using vercel CLI
                slug = client_name.lower().replace(" ", "-")[:20]
                vercel_result = self._deploy_to_vercel(slug, html)

                deployed.append({
                    "client_name": client_name,
                    "deployed": vercel_result.get("ok", False),
                    "url": vercel_result.get("url", ""),
                    "vercel_url": vercel_result.get("url", ""),
                    "error": vercel_result.get("error", ""),
                })
            except Exception as e:
                logger.error(f"Deploy failed for {client_name}: {e}")
                deployed.append({
                    "client_name": client_name,
                    "deployed": False,
                    "error": str(e),
                })

        successful = [d for d in deployed if d.get("deployed")]

        return {
            "output": {
                "deployed": deployed,
                "total_deployed": len(successful),
                "live_urls": [d["url"] for d in successful if d.get("url")],
            }
        }

    def _deploy_to_vercel(self, name: str, html: str) -> dict:
        """Deploy to Vercel using vercel CLI."""
        import os
        import tempfile

        try:
            # Create temp directory with index.html
            with tempfile.TemporaryDirectory() as tmpdir:
                index_path = os.path.join(tmpdir, "index.html")
                with open(index_path, "w", encoding="utf-8") as f:
                    f.write(html)

                # Check if vercel CLI is available
                result = subprocess.run(
                    ["vercel", "--version"],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode != 0:
                    return {"ok": False, "error": "Vercel CLI not installed"}

                # Deploy to Vercel
                result = subprocess.run(
                    ["vercel", "deploy", "--yes", "--prod", tmpdir],
                    capture_output=True, text=True, timeout=120,
                    cwd=tmpdir,
                )

                if result.returncode == 0:
                    # Extract URL from output
                    url = ""
                    for line in result.stdout.split("\n"):
                        if "https://" in line:
                            url = line.strip()
                            break
                    return {"ok": True, "url": url, "stdout": result.stdout}
                else:
                    return {"ok": False, "error": result.stderr}

        except FileNotFoundError:
            return {"ok": False, "error": "Vercel CLI not installed. Run: npm i -g vercel"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "Vercel deploy timeout"}
        except Exception as e:
            return {"ok": False, "error": str(e)}
