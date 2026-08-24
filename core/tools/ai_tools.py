"""AI Image Generation — Stable Diffusion via HuggingFace diffusers (local)."""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class AIGenerateTools:
    """Local AI image generation using Stable Diffusion."""

    def __init__(self, media_dir: str = ""):
        self._media_dir = media_dir or os.path.join(
            os.path.expanduser("~"), ".kaihara", "media", "ai_gen")
        os.makedirs(self._media_dir, exist_ok=True)
        self._pipe = None
        self._device = "cuda" if self._has_cuda() else "cpu"

    def _has_cuda(self) -> bool:
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def _load_pipeline(self, model_id: str = None) -> bool:
        if self._pipe is not None:
            return True
        try:
            from diffusers import StableDiffusionPipeline
            import torch

            model = model_id or "stable-diffusion-v1-5/stable-diffusion-v1-5"
            dtype = torch.float16 if self._device == "cuda" else torch.float32

            self._pipe = StableDiffusionPipeline.from_pretrained(
                model, torch_dtype=dtype
            )
            self._pipe = self._pipe.to(self._device)

            # Enable memory optimizations
            if self._device == "cuda":
                try:
                    self._pipe.enable_attention_slicing()
                except Exception:
                    pass

            return True
        except ImportError:
            return False
        except Exception:
            return False

    def generate_image(self, prompt: str, output_path: str = None,
                       negative_prompt: str = "",
                       width: int = 512, height: int = 512,
                       steps: int = 30, guidance_scale: float = 7.5,
                       seed: int = None) -> dict:
        """Generate image from text prompt using Stable Diffusion."""
        if not output_path:
            output_path = os.path.join(self._media_dir,
                f"sd_{hash(prompt) % 100000}.png")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if not self._load_pipeline():
            return {
                "ok": False,
                "error": "diffusers not installed. pip install diffusers transformers accelerate torch",
            }

        try:
            import torch

            generator = None
            if seed is not None:
                generator = torch.Generator(device=self._device).manual_seed(seed)

            result = self._pipe(
                prompt=prompt,
                negative_prompt=negative_prompt or "blurry, bad quality, deformed",
                width=width,
                height=height,
                num_inference_steps=steps,
                guidance_scale=guidance_scale,
                generator=generator,
            )

            image = result.images[0]
            image.save(output_path)

            return {
                "ok": True,
                "output": output_path,
                "prompt": prompt,
                "size": [width, height],
                "steps": steps,
                "model": "stable-diffusion-v1-5",
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def generate_poster_ai(self, title: str, style: str = "cinematic",
                           output_path: str = None, **kwargs) -> dict:
        """Generate AI poster with a title overlay."""
        style_prompts = {
            "cinematic": "cinematic, dramatic lighting, movie poster style, epic",
            "anime": "anime style, vibrant colors, Japanese art, detailed",
            "realistic": "photorealistic, high detail, 8k, professional",
            "fantasy": "fantasy art, magical, ethereal glow, detailed",
            "minimalist": "minimalist design, clean, modern, simple",
            "retro": "retro style, vintage, 80s aesthetic, neon",
        }
        prompt = f"{title}, {style_prompts.get(style, style_prompts['cinematic'])}"
        result = self.generate_image(prompt, output_path, **kwargs)
        if result.get("ok") and result.get("output"):
            # Add text overlay
            try:
                from PIL import Image, ImageDraw, ImageFont
                img = Image.open(result["output"])
                draw = ImageDraw.Draw(img)
                # Simple center text
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
                except Exception:
                    font = ImageFont.load_default()
                bbox = draw.textbbox((0, 0), title, font=font)
                tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
                x = (img.width - tw) // 2
                y = img.height - th - 60
                draw.text((x, y), title, fill="white", font=font,
                          stroke_width=2, stroke_fill="black")
                img.save(result["output"])
                result["text_overlay"] = True
            except Exception:
                pass
        return result

    def generate_thumbnail_ai(self, topic: str, output_path: str = None,
                              **kwargs) -> dict:
        """Generate AI YouTube thumbnail."""
        prompt = f"YouTube thumbnail, {topic}, eye-catching, bold, high contrast, professional"
        return self.generate_image(prompt, output_path,
                                   width=1280, height=720, **kwargs)

    def status(self) -> dict:
        """Check AI generation status."""
        has_cuda = self._has_cuda()
        diffusers_ok = False
        try:
            import diffusers
            diffusers_ok = True
        except ImportError:
            pass
        return {
            "diffusers_installed": diffusers_ok,
            "cuda_available": has_cuda,
            "device": self._device,
            "model_loaded": self._pipe is not None,
            "media_dir": self._media_dir,
        }


AI_GENERATE_TOOLS = [
    {
        "name": "ai_generate_image",
        "description": "Generate AI image from text prompt using Stable Diffusion (local)",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Text prompt for image generation"},
                "negative_prompt": {"type": "string", "description": "What to avoid", "default": ""},
                "width": {"type": "integer", "default": 512},
                "height": {"type": "integer", "default": 512},
                "steps": {"type": "integer", "default": 30},
                "guidance_scale": {"type": "number", "default": 7.5},
                "seed": {"type": "integer", "description": "Random seed for reproducibility"},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "ai_generate_poster",
        "description": "Generate AI poster with title overlay using Stable Diffusion",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Poster title/text"},
                "style": {"type": "string", "enum": ["cinematic", "anime", "realistic", "fantasy", "minimalist", "retro"], "default": "cinematic"},
                "prompt": {"type": "string", "description": "Additional prompt details"},
                "width": {"type": "integer", "default": 512},
                "height": {"type": "integer", "default": 768},
            },
            "required": ["title"],
        },
    },
    {
        "name": "ai_generate_thumbnail",
        "description": "Generate AI YouTube thumbnail (1280x720)",
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Thumbnail topic"},
                "prompt": {"type": "string", "description": "Additional details"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "ai_generate_status",
        "description": "Check AI generation setup status",
        "parameters": {"type": "object", "properties": {}},
    },
]
