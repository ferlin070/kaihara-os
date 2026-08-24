"""Google Flow API — Imagen & Veo video generation via useapi.net."""

import os
import json
import time
import tempfile
from pathlib import Path
from typing import Any

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


class GoogleFlowTools:
    """Google Flow API integration via useapi.net proxy."""

    BASE_URL = "https://useapi.net/api/v1"

    def __init__(self, api_token: str = ""):
        self._token = api_token or os.environ.get("USEAPI_TOKEN", "")
        self._media_dir = os.path.join(
            os.path.expanduser("~"), ".kaihara", "media", "google_flow")
        os.makedirs(self._media_dir, exist_ok=True)
        self._email = os.environ.get("GOOGLE_FLOW_EMAIL", "")

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def _post(self, endpoint: str, data: dict) -> dict:
        if not self._token:
            return {"ok": False, "error": "USEAPI_TOKEN not set"}
        if not HAS_HTTPX:
            return {"ok": False, "error": "httpx not installed. pip install httpx"}

        try:
            with httpx.Client(timeout=120) as client:
                r = client.post(
                    f"{self.BASE_URL}{endpoint}",
                    headers=self._headers(),
                    json=data,
                )
                return {
                    "ok": r.status_code in (200, 201),
                    "status": r.status_code,
                    "data": r.json(),
                }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _get(self, endpoint: str) -> dict:
        if not self._token:
            return {"ok": False, "error": "USEAPI_TOKEN not set"}
        if not HAS_HTTPX:
            return {"ok": False, "error": "httpx not installed"}

        try:
            with httpx.Client(timeout=60) as client:
                r = client.get(
                    f"{self.BASE_URL}{endpoint}",
                    headers=self._headers(),
                )
                return {
                    "ok": r.status_code == 200,
                    "status": r.status_code,
                    "data": r.json(),
                }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ============================================================
    # IMAGE GENERATION (Imagen / Nano Banana)
    # ============================================================

    def generate_image(self, prompt: str,
                       model: str = "imagen-4",
                       output_path: str = None,
                       **kwargs) -> dict:
        """Generate image using Google Flow Imagen."""
        data = {
            "prompt": prompt,
            "model": model,
        }
        data.update(kwargs)

        result = self._post("/google-flow/images", data)
        if not result.get("ok"):
            return result

        # Handle async task
        resp = result.get("data", {})
        task_id = resp.get("task_id") or resp.get("id")

        if task_id:
            # Poll for completion
            for _ in range(60):
                time.sleep(5)
                status = self._get(f"/google-flow/images/{task_id}")
                s_data = status.get("data", {})
                if s_data.get("status") == "completed":
                    images = s_data.get("images", s_data.get("output", []))
                    if images:
                        img_url = images[0] if isinstance(images[0], str) else images[0].get("url", "")
                        if img_url and not output_path:
                            output_path = os.path.join(self._media_dir,
                                f"flow_{hash(prompt) % 100000}.png")
                        if img_url and output_path:
                            self._download_file(img_url, output_path)
                            return {"ok": True, "output": output_path, "url": img_url}
                    return {"ok": True, "data": s_data}
                elif s_data.get("status") == "failed":
                    return {"ok": False, "error": s_data.get("error", "generation failed")}

            return {"ok": False, "error": "timeout waiting for image generation"}

        return {"ok": True, "data": resp}

    # ============================================================
    # VIDEO GENERATION (Veo 3.1)
    # ============================================================

    def generate_video(self, prompt: str,
                       model: str = "veo-3.1-fast",
                       duration: str = "8s",
                       aspect_ratio: str = "16:9",
                       output_path: str = None,
                       **kwargs) -> dict:
        """Generate video using Google Flow Veo."""
        data = {
            "prompt": prompt,
            "model": model,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
        }
        data.update(kwargs)

        result = self._post("/google-flow/videos", data)
        if not result.get("ok"):
            return result

        resp = result.get("data", {})
        task_id = resp.get("task_id") or resp.get("id")

        if task_id:
            # Poll for completion (video takes longer)
            for _ in range(120):
                time.sleep(10)
                status = self._get(f"/google-flow/videos/{task_id}")
                s_data = status.get("data", {})
                if s_data.get("status") == "completed":
                    videos = s_data.get("videos", s_data.get("output", []))
                    if videos:
                        vid_url = videos[0] if isinstance(videos[0], str) else videos[0].get("url", "")
                        if vid_url and not output_path:
                            output_path = os.path.join(self._media_dir,
                                f"flow_{hash(prompt) % 100000}.mp4")
                        if vid_url and output_path:
                            self._download_file(vid_url, output_path)
                            return {"ok": True, "output": output_path, "url": vid_url}
                    return {"ok": True, "data": s_data}
                elif s_data.get("status") == "failed":
                    return {"ok": False, "error": s_data.get("error", "video generation failed")}

            return {"ok": False, "error": "timeout waiting for video generation"}

        return {"ok": True, "data": resp}

    def generate_video_from_image(self, image_path: str, prompt: str = "",
                                   model: str = "veo-3.1-fast",
                                   output_path: str = None) -> dict:
        """Generate video from image (image-to-video)."""
        if not os.path.exists(image_path):
            return {"ok": False, "error": f"image not found: {image_path}"}

        # Upload image first if needed
        data = {
            "prompt": prompt or "animate this image",
            "model": model,
            "image": image_path,
        }

        result = self._post("/google-flow/videos", data)
        if not result.get("ok"):
            return result

        resp = result.get("data", {})
        task_id = resp.get("task_id") or resp.get("id")

        if task_id:
            for _ in range(120):
                time.sleep(10)
                status = self._get(f"/google-flow/videos/{task_id}")
                s_data = status.get("data", {})
                if s_data.get("status") == "completed":
                    videos = s_data.get("videos", s_data.get("output", []))
                    if videos:
                        vid_url = videos[0] if isinstance(videos[0], str) else videos[0].get("url", "")
                        if vid_url and not output_path:
                            output_path = os.path.join(self._media_dir,
                                f"flow_img2vid.mp4")
                        if vid_url and output_path:
                            self._download_file(vid_url, output_path)
                            return {"ok": True, "output": output_path}
                    return {"ok": True, "data": s_data}
                elif s_data.get("status") == "failed":
                    return {"ok": False, "error": s_data.get("error", "failed")}

            return {"ok": False, "error": "timeout"}

        return {"ok": True, "data": resp}

    # ============================================================
    # HELPERS
    # ============================================================

    def _download_file(self, url: str, output_path: str) -> bool:
        try:
            with httpx.Client(timeout=120) as client:
                r = client.get(url, follow_redirects=True)
                if r.status_code == 200:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(r.content)
                    return True
        except Exception:
            pass
        return False

    def status(self) -> dict:
        """Check Google Flow status."""
        return {
            "token_set": bool(self._token),
            "email": self._email or "(not set)",
            "httpx_installed": HAS_HTTPX,
            "media_dir": self._media_dir,
        }


GOOGLE_FLOW_TOOLS = [
    {
        "name": "google_flow_generate_image",
        "description": "Generate AI image using Google Flow Imagen (requires Google Flow subscription + useapi token)",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Text prompt for image generation"},
                "model": {"type": "string", "default": "imagen-4", "description": "Model: imagen-4, nano-banana-2, nano-banana-pro"},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "google_flow_generate_video",
        "description": "Generate AI video using Google Flow Veo 3.1 (requires subscription + useapi token)",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Text prompt for video generation"},
                "model": {"type": "string", "default": "veo-3.1-fast", "description": "Model: veo-3.1-fast, veo-3.1-quality"},
                "duration": {"type": "string", "default": "8s", "description": "Duration: 4s, 6s, 8s"},
                "aspect_ratio": {"type": "string", "default": "16:9"},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "google_flow_image_to_video",
        "description": "Animate an image into video using Google Flow Veo",
        "parameters": {
            "type": "object",
            "properties": {
                "image_path": {"type": "string", "description": "Path to input image"},
                "prompt": {"type": "string", "default": "animate this image"},
                "model": {"type": "string", "default": "veo-3.1-fast"},
            },
            "required": ["image_path"],
        },
    },
    {
        "name": "google_flow_status",
        "description": "Check Google Flow API status",
        "parameters": {"type": "object", "properties": {}},
    },
]
