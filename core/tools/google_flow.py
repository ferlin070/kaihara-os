"""
Google Flow MCP Integration — Browser-based AI image/video generation.
Uses Playwright to drive Google Flow (labs.google/fx/tools/flow)
through the user's logged-in Chrome profile.
"""

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger("kaihara.tools.google_flow")

# Google Flow URLs
FLOW_URL = "https://labs.google/fx/tools/flow"
FLOW_LOGIN_URL = "https://accounts.google.com"


class GoogleFlowMCP:
    """Google Flow MCP client for AI image/video generation via browser automation."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.user_data_dir = self.config.get(
            "user_data_dir",
            str(Path.home() / ".kaihara" / "chrome-profile")
        )
        self.headless = self.config.get("headless", False)
        self.timeout = self.config.get("timeout", 60000)
        self._browser = None
        self._context = None
        self._page = None

    async def _ensure_browser(self):
        """Ensure browser is launched and logged in."""
        if self._page and not self._page.is_closed():
            return self._page

        try:
            from playwright.async_api import async_playwright
        except ImportError:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && playwright install chromium"
            )

        playwright = await async_playwright().start()

        # Use persistent context to keep Google login
        self._context = await playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
            viewport={"width": 1280, "height": 800},
        )

        self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
        return self._page

    async def check_login(self) -> dict:
        """Check if user is logged into Google."""
        page = await self._ensure_browser()
        try:
            await page.goto(FLOW_URL, timeout=self.timeout)
            await page.wait_for_load_state("networkidle", timeout=10000)

            # Check if redirected to login
            if "accounts.google.com" in page.url:
                return {
                    "status": "not_logged_in",
                    "message": "Please log in to Google in the browser window",
                    "login_url": page.url,
                }

            return {
                "status": "logged_in",
                "message": "Google account authenticated",
                "url": page.url,
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def generate_image(self, prompt: str, style: str = "default",
                             aspect_ratio: str = "16:9") -> dict:
        """Generate an image using Google Flow."""
        page = await self._ensure_browser()
        try:
            await page.goto(FLOW_URL, timeout=self.timeout)
            await page.wait_for_load_state("networkidle", timeout=10000)

            # Find and fill prompt input
            prompt_input = page.locator('textarea, input[type="text"]').first
            await prompt_input.fill(prompt)

            # Select aspect ratio if available
            if aspect_ratio != "16:9":
                try:
                    ratio_btn = page.locator(f'button:has-text("{aspect_ratio}")')
                    if await ratio_btn.count() > 0:
                        await ratio_btn.click()
                except Exception:
                    pass

            # Click generate button
            generate_btn = page.locator('button:has-text("Generate"), button[type="submit"]').first
            await generate_btn.click()

            # Wait for generation to complete
            await page.wait_for_timeout(30000)  # Wait 30s for generation

            # Try to find and download the result
            result_images = await page.locator('img[src*="generated"], img[src*="output"]').all()

            if result_images:
                # Download first result
                src = await result_images[0].get_attribute("src")
                return {
                    "status": "success",
                    "prompt": prompt,
                    "image_url": src,
                    "message": "Image generated successfully",
                }

            return {
                "status": "pending",
                "prompt": prompt,
                "message": "Generation started, check browser for results",
            }

        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            return {"status": "error", "message": str(e), "prompt": prompt}

    async def generate_video(self, prompt: str, duration: str = "5s") -> dict:
        """Generate a video using Google Flow Veo."""
        page = await self._ensure_browser()
        try:
            await page.goto(FLOW_URL, timeout=self.timeout)
            await page.wait_for_load_state("networkidle", timeout=10000)

            # Switch to video mode
            try:
                video_tab = page.locator('button:has-text("Video"), [data-tab="video"]')
                if await video_tab.count() > 0:
                    await video_tab.click()
            except Exception:
                pass

            # Fill prompt
            prompt_input = page.locator('textarea, input[type="text"]').first
            await prompt_input.fill(prompt)

            # Click generate
            generate_btn = page.locator('button:has-text("Generate"), button[type="submit"]').first
            await generate_btn.click()

            # Wait for video generation (longer than image)
            await page.wait_for_timeout(60000)

            return {
                "status": "pending",
                "prompt": prompt,
                "message": "Video generation started, check browser for results",
            }

        except Exception as e:
            logger.error(f"Video generation failed: {e}")
            return {"status": "error", "message": str(e), "prompt": prompt}

    async def download_result(self, save_dir: str = None) -> dict:
        """Download the latest generated result."""
        page = await self._ensure_browser()
        try:
            if save_dir is None:
                save_dir = str(Path.home() / ".kaihara" / "generated")

            os.makedirs(save_dir, exist_ok=True)

            # Find download buttons
            download_btns = await page.locator('button:has-text("Download"), a[download]').all()

            if download_btns:
                # Click first download button
                async with page.expect_download(timeout=30000) as download_info:
                    await download_btns[0].click()

                download = await download_info.value
                filename = download.suggested_filename or f"flow_{uuid.uuid4().hex[:8]}.png"
                save_path = os.path.join(save_dir, filename)
                await download.save_as(save_path)

                return {
                    "status": "success",
                    "file_path": save_path,
                    "filename": filename,
                    "message": f"Downloaded to {save_path}",
                }

            return {
                "status": "no_results",
                "message": "No downloadable results found",
            }

        except Exception as e:
            logger.error(f"Download failed: {e}")
            return {"status": "error", "message": str(e)}

    async def batch_generate(self, prompts: list[dict]) -> list[dict]:
        """Generate multiple images/videos in batch."""
        results = []
        for i, item in enumerate(prompts):
            prompt = item.get("prompt", "")
            media_type = item.get("type", "image")

            logger.info(f"Batch {i+1}/{len(prompts)}: {media_type} - {prompt[:50]}...")

            if media_type == "video":
                result = await self.generate_video(prompt, item.get("duration", "5s"))
            else:
                result = await self.generate_image(
                    prompt,
                    item.get("style", "default"),
                    item.get("aspect_ratio", "16:9"),
                )

            results.append(result)

            # Wait between generations to avoid rate limiting
            if i < len(prompts) - 1:
                await asyncio.sleep(5)

        return results

    async def close(self):
        """Close browser context."""
        if self._context:
            await self._context.close()
            self._context = None
            self._page = None


# Tool functions for agent integration

_google_flow_instance: Optional[GoogleFlowMCP] = None


def _get_flow_instance(config: dict = None) -> GoogleFlowMCP:
    global _google_flow_instance
    if _google_flow_instance is None:
        _google_flow_instance = GoogleFlowMCP(config)
    return _google_flow_instance


async def google_flow_generate_image(prompt: str, style: str = "default",
                                      aspect_ratio: str = "16:9") -> str:
    """Generate an image using Google Flow (free AI image generation)."""
    flow = _get_flow_instance()
    result = await flow.generate_image(prompt, style, aspect_ratio)
    return json.dumps(result, indent=2)


async def google_flow_generate_video(prompt: str, duration: str = "5s") -> str:
    """Generate a video using Google Flow Veo (free AI video generation)."""
    flow = _get_flow_instance()
    result = await flow.generate_video(prompt, duration)
    return json.dumps(result, indent=2)


async def google_flow_download(save_dir: str = None) -> str:
    """Download the latest Google Flow generation result."""
    flow = _get_flow_instance()
    result = await flow.download_result(save_dir)
    return json.dumps(result, indent=2)


async def google_flow_batch(prompts_json: str) -> str:
    """Batch generate multiple images/videos. Pass JSON array of {prompt, type, style, aspect_ratio}."""
    flow = _get_flow_instance()
    prompts = json.loads(prompts_json)
    results = await flow.batch_generate(prompts)
    return json.dumps(results, indent=2)


async def google_flow_check_login() -> str:
    """Check if Google account is logged in for Google Flow."""
    flow = _get_flow_instance()
    result = await flow.check_login()
    return json.dumps(result, indent=2)


# MCP-style tool definitions
GOOGLE_FLOW_TOOLS = [
    {
        "name": "google_flow_generate_image",
        "description": "Generate free AI images using Google Flow (labs.google/fx/tools/flow). Supports custom styles and aspect ratios.",
        "parameters": {
            "prompt": {"type": "string", "description": "Image generation prompt"},
            "style": {"type": "string", "description": "Image style (default, realistic, artistic, etc.)"},
            "aspect_ratio": {"type": "string", "description": "Aspect ratio (16:9, 1:1, 9:16)"},
        },
        "function": google_flow_generate_image,
    },
    {
        "name": "google_flow_generate_video",
        "description": "Generate free AI videos using Google Flow Veo. Supports text-to-video generation.",
        "parameters": {
            "prompt": {"type": "string", "description": "Video generation prompt"},
            "duration": {"type": "string", "description": "Video duration (5s, 10s)"},
        },
        "function": google_flow_generate_video,
    },
    {
        "name": "google_flow_download",
        "description": "Download the latest Google Flow generation result to local storage.",
        "parameters": {
            "save_dir": {"type": "string", "description": "Directory to save files (optional)"},
        },
        "function": google_flow_download,
    },
    {
        "name": "google_flow_batch",
        "description": "Batch generate multiple images/videos using Google Flow.",
        "parameters": {
            "prompts_json": {"type": "string", "description": "JSON array of {prompt, type, style, aspect_ratio}"},
        },
        "function": google_flow_batch,
    },
    {
        "name": "google_flow_check_login",
        "description": "Check if Google account is logged in for Google Flow access.",
        "parameters": {},
        "function": google_flow_check_login,
    },
]
