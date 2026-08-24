"""
ComfyUI Integration — Node-based Stable Diffusion API client.
Connects to a running ComfyUI instance for advanced AI generation.
"""

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("kaihara.tools.comfyui")

# Default ComfyUI API endpoint
DEFAULT_COMFYUI_URL = "http://127.0.0.1:8188"


class ComfyUIClient:
    """Client for ComfyUI API — advanced node-based Stable Diffusion."""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.base_url = self.config.get("url", DEFAULT_COMFYUI_URL)
        self.client_id = str(uuid.uuid4())
        self.output_dir = self.config.get(
            "output_dir",
            str(Path.home() / ".kaihara" / "media" / "comfyui")
        )
        os.makedirs(self.output_dir, exist_ok=True)

    async def check_connection(self) -> dict:
        """Check if ComfyUI is running and accessible."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/system_stats")
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "status": "connected",
                        "version": data.get("system", {}).get("comfyui_version", "unknown"),
                        "gpu": data.get("devices", [{}])[0].get("name", "unknown"),
                        "url": self.base_url,
                    }
        except Exception as e:
            pass

        return {
            "status": "disconnected",
            "message": f"ComfyUI not reachable at {self.base_url}",
            "url": self.base_url,
        }

    async def get_models(self) -> dict:
        """Get available models (checkpoints, LoRAs, etc.)."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/object_info")
                if resp.status_code == 200:
                    data = resp.json()
                    checkpoints = data.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
                    return {
                        "status": "success",
                        "checkpoints": checkpoints,
                        "url": self.base_url,
                    }
        except Exception as e:
            pass

        return {"status": "error", "message": "Failed to fetch models"}

    async def generate_image(self, prompt: str, checkpoint: str = None,
                             negative_prompt: str = "", width: int = 512,
                             height: int = 512, steps: int = 30,
                             cfg: float = 7.0, seed: int = None) -> dict:
        """Generate image using ComfyUI workflow."""
        try:
            # Build basic workflow
            workflow = self._build_txt2img_workflow(
                prompt=prompt,
                negative_prompt=negative_prompt,
                checkpoint=checkpoint,
                width=width,
                height=height,
                steps=steps,
                cfg=cfg,
                seed=seed,
            )

            # Queue prompt
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.base_url}/prompt",
                    json={"prompt": workflow, "client_id": self.client_id},
                )

                if resp.status_code != 200:
                    return {"status": "error", "message": f"Queue failed: {resp.text}"}

                prompt_id = resp.json().get("prompt_id")

                # Poll for completion
                result = await self._wait_for_completion(prompt_id)

                if result.get("status") == "success":
                    # Download generated image
                    image_path = await self._download_image(result["filename"], result["subfolder"])

                    return {
                        "status": "success",
                        "output": image_path,
                        "prompt": prompt,
                        "prompt_id": prompt_id,
                        "size": [width, height],
                        "steps": steps,
                        "model": checkpoint or "default",
                    }

                return result

        except Exception as e:
            logger.error(f"ComfyUI generation failed: {e}")
            return {"status": "error", "message": str(e)}

    def _build_txt2img_workflow(self, prompt: str, negative_prompt: str = "",
                                 checkpoint: str = None, width: int = 512,
                                 height: int = 512, steps: int = 30,
                                 cfg: float = 7.0, seed: int = None) -> dict:
        """Build a basic txt2img ComfyUI workflow."""
        if seed is None:
            seed = int.from_bytes(os.urandom(4), "little")

        workflow = {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": checkpoint or "v1-5-pruned-emaonly.safetensors",
                },
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1,
                },
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": ["4", 1],
                },
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": negative_prompt or "blurry, bad quality, deformed",
                    "clip": ["4", 1],
                },
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2],
                },
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "kaihara",
                    "images": ["8", 0],
                },
            },
        }

        return workflow

    async def _wait_for_completion(self, prompt_id: str, timeout: int = 120) -> dict:
        """Wait for ComfyUI to finish processing."""
        import time
        start = time.time()

        async with httpx.AsyncClient(timeout=5) as client:
            while time.time() - start < timeout:
                try:
                    resp = await client.get(f"{self.base_url}/history/{prompt_id}")
                    if resp.status_code == 200:
                        history = resp.json()
                        if prompt_id in history:
                            outputs = history[prompt_id].get("outputs", {})
                            # Find the SaveImage output
                            for node_id, node_output in outputs.items():
                                if "images" in node_output:
                                    for img in node_output["images"]:
                                        return {
                                            "status": "success",
                                            "filename": img["filename"],
                                            "subfolder": img.get("subfolder", ""),
                                            "type": img.get("type", "output"),
                                        }
                except Exception:
                    pass

                await asyncio.sleep(1)

        return {"status": "timeout", "message": f"Generation timed out after {timeout}s"}

    async def _download_image(self, filename: str, subfolder: str = "") -> str:
        """Download generated image from ComfyUI."""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/view",
                params={"filename": filename, "subfolder": subfolder, "type": "output"},
            )

            if resp.status_code == 200:
                # Save to local directory
                save_path = os.path.join(self.output_dir, filename)
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                return save_path

            raise Exception(f"Download failed: {resp.status_code}")

    async def interrupt(self) -> dict:
        """Interrupt current generation."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(f"{self.base_url}/interrupt")
                return {"status": "interrupted"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


# Tool functions for agent integration

_comfyui_instance: Optional[ComfyUIClient] = None


def _get_comfyui_instance(config: dict = None) -> ComfyUIClient:
    global _comfyui_instance
    if _comfyui_instance is None:
        _comfyui_instance = ComfyUIClient(config)
    return _comfyui_instance


async def comfyui_check() -> str:
    """Check if ComfyUI is running and accessible."""
    client = _get_comfyui_instance()
    result = await client.check_connection()
    return json.dumps(result, indent=2)


async def comfyui_generate(prompt: str, checkpoint: str = None,
                           negative_prompt: str = "", width: int = 512,
                           height: int = 512, steps: int = 30,
                           cfg: float = 7.0, seed: int = None) -> str:
    """Generate image using ComfyUI (advanced node-based Stable Diffusion)."""
    client = _get_comfyui_instance()
    result = await client.generate_image(
        prompt=prompt, checkpoint=checkpoint,
        negative_prompt=negative_prompt,
        width=width, height=height,
        steps=steps, cfg=cfg, seed=seed,
    )
    return json.dumps(result, indent=2)


async def comfyui_models() -> str:
    """List available ComfyUI models (checkpoints, LoRAs)."""
    client = _get_comfyui_instance()
    result = await client.get_models()
    return json.dumps(result, indent=2)


async def comfyui_interrupt() -> str:
    """Interrupt current ComfyUI generation."""
    client = _get_comfyui_instance()
    result = await client.interrupt()
    return json.dumps(result, indent=2)


# MCP-style tool definitions
COMFYUI_TOOLS = [
    {
        "name": "comfyui_check",
        "description": "Check if ComfyUI server is running and accessible",
        "parameters": {},
        "function": comfyui_check,
    },
    {
        "name": "comfyui_generate",
        "description": "Generate AI image using ComfyUI (node-based Stable Diffusion). More powerful than basic diffusers.",
        "parameters": {
            "prompt": {"type": "string", "description": "Image generation prompt"},
            "checkpoint": {"type": "string", "description": "Model checkpoint to use"},
            "negative_prompt": {"type": "string", "description": "What to avoid"},
            "width": {"type": "integer", "default": 512},
            "height": {"type": "integer", "default": 512},
            "steps": {"type": "integer", "default": 30},
            "cfg": {"type": "number", "default": 7.0},
            "seed": {"type": "integer", "description": "Random seed"},
        },
        "function": comfyui_generate,
    },
    {
        "name": "comfyui_models",
        "description": "List available ComfyUI models (checkpoints, LoRAs, VAEs)",
        "parameters": {},
        "function": comfyui_models,
    },
    {
        "name": "comfyui_interrupt",
        "description": "Interrupt current ComfyUI generation",
        "parameters": {},
        "function": comfyui_interrupt,
    },
]
