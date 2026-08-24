"""Video Pipeline — automated video processing workflows."""

import os
from typing import Any


class VideoPipeline:
    """Automated video processing pipelines."""

    def __init__(self, media_dir: str = ""):
        self._media_dir = media_dir or os.path.join(
            os.path.expanduser("~"), ".kaihara", "media", "pipelines")
        os.makedirs(self._media_dir, exist_ok=True)

    async def auto_voiceover(self, video_path: str, text: str,
                              voice: str = "yasmin", output_path: str = None) -> dict:
        """Auto-generate voiceover and overlay on video."""
        from core.tools.media_tools import video_add_audio, audio_normalize
        from core.voice.tts import TTS

        if not output_path:
            output_path = os.path.join(self._media_dir, "voiceover",
                f"vo_{os.path.basename(video_path)}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Generate TTS
        tts = TTS()
        tts_result = await tts.synthesize_async(text, voice_name=voice)
        if not tts_result.get("audio"):
            return {"ok": False, "error": tts_result.get("error", "TTS failed")}

        # Save TTS audio
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(tts_result["audio"])
            audio_path = f.name

        try:
            # Normalize audio
            norm_path = audio_path + ".norm.mp3"
            audio_normalize(audio_path, norm_path)

            # Overlay on video
            result = video_add_audio(video_path, norm_path, output_path, replace=True)
            result["voice"] = tts_result.get("voice", voice)
            result["engine"] = tts_result.get("engine", "edge-neural")
            return result
        finally:
            for p in [audio_path, norm_path]:
                try:
                    os.unlink(p)
                except Exception:
                    pass

    async def auto_slideshow(self, image_dir: str, output_path: str = None,
                              seconds_per_image: float = 3.0,
                              transition: str = "fade",
                              voiceover: str = "", voice: str = "yasmin") -> dict:
        """Auto-create slideshow from directory of images with optional voiceover."""
        from core.tools.media_tools import video_from_images, video_add_audio
        from core.voice.tts import TTS

        # Find images
        exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
        images = sorted([
            os.path.join(image_dir, f)
            for f in os.listdir(image_dir)
            if os.path.splitext(f)[1].lower() in exts
        ])

        if not images:
            return {"ok": False, "error": "no images found in directory"}

        if not output_path:
            output_path = os.path.join(self._media_dir, "slideshows",
                f"slideshow_{os.path.basename(image_dir)}.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Create slideshow
        result = video_from_images(images, output_path,
            seconds_per_image=seconds_per_image, transition=transition)

        if not result.get("ok"):
            return result

        # Add voiceover if provided
        if voiceover:
            tts = TTS()
            tts_result = await tts.synthesize_async(voiceover, voice_name=voice)
            if tts_result.get("audio"):
                import tempfile
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    f.write(tts_result["audio"])
                    audio_path = f.name
                try:
                    vo_output = output_path.replace(".mp4", "_vo.mp4")
                    audio_result = video_add_audio(output_path, audio_path, vo_output, replace=True)
                    if audio_result.get("ok"):
                        result["output"] = vo_output
                        result["voiceover"] = True
                finally:
                    try:
                        os.unlink(audio_path)
                    except Exception:
                        pass

        result["images_count"] = len(images)
        return result

    async def auto_thumbnail_grid(self, video_path: str, output_path: str = None,
                                   count: int = 6) -> dict:
        """Extract multiple thumbnails from video for grid preview."""
        from core.tools.media_tools import video_probe, generate_thumbnail

        probe = video_probe(video_path)
        if not probe.get("ok"):
            return {"ok": False, "error": "cannot probe video"}

        duration = probe.get("duration", 10)
        interval = duration / (count + 1)

        if not output_path:
            output_path = os.path.join(self._media_dir, "thumbnails",
                f"grid_{os.path.basename(video_path)}")
        os.makedirs(output_path, exist_ok=True)

        thumbs = []
        for i in range(1, count + 1):
            time = interval * i
            thumb_path = os.path.join(output_path, f"thumb_{i:02d}.png")
            result = generate_thumbnail(video_path, thumb_path, time=time)
            if result.get("ok"):
                thumbs.append(thumb_path)

        return {
            "ok": len(thumbs) > 0,
            "thumbnails": thumbs,
            "count": len(thumbs),
            "output_dir": output_path,
        }

    async def auto_trim_silence(self, video_path: str, output_path: str = None,
                                 threshold: float = 0.02) -> dict:
        """Auto-trim silent parts from video (basic)."""
        from core.tools.media_tools import video_probe, _run_ffmpeg

        if not output_path:
            output_path = os.path.join(self._media_dir, "trimmed",
                f"silence_trimmed_{os.path.basename(video_path)}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Use ffmpeg silencedetect + trim
        args = [
            "-i", video_path,
            "-af", f"silencedetect=noise={threshold}dB:d=0.5",
            "-f", "null", "-"
        ]
        result = _run_ffmpeg(args, timeout=60)

        # Simple approach: just copy with audio normalization
        from core.tools.media_tools import audio_normalize
        norm_path = output_path.replace(".mp4", "_norm.mp3")
        video_add_audio_result = _run_ffmpeg([
            "-i", video_path,
            "-af", f"silenceremove=start_periods=1:start_duration=0.5:start_threshold={threshold}dB,"
                   f"areverse,silenceremove=start_periods=1:start_duration=0.5:start_threshold={threshold}dB,areverse",
            "-c:v", "copy", output_path
        ], timeout=120)

        if video_add_audio_result.get("ok") and os.path.exists(output_path):
            probe = video_probe(output_path)
            return {"ok": True, "output": output_path, "duration": probe.get("duration", 0)}
        return {"ok": False, "error": video_add_audio_result.get("stderr", "trim failed")}

    async def auto_export_all(self, video_path: str, output_dir: str = None) -> dict:
        """Auto-export video in multiple formats/sizes."""
        from core.tools.media_tools import video_export

        if not output_dir:
            output_dir = os.path.join(self._media_dir, "exports",
                os.path.splitext(os.path.basename(video_path))[0])
        os.makedirs(output_dir, exist_ok=True)

        formats = [
            {"name": "1080p", "width": 1920, "height": 1080},
            {"name": "720p", "width": 1280, "height": 720},
            {"name": "480p", "width": 854, "height": 480},
            {"name": "square", "width": 1080, "height": 1080},
            {"name": "vertical", "width": 1080, "height": 1920},
        ]

        results = []
        for fmt in formats:
            out = os.path.join(output_dir, f"{fmt['name']}.mp4")
            r = video_export(video_path, out, width=fmt["width"], height=fmt["height"])
            results.append({"format": fmt["name"], "ok": r.get("ok", False), "output": out})

        return {
            "ok": any(r["ok"] for r in results),
            "exports": results,
            "output_dir": output_dir,
        }


VIDEO_PIPELINE_TOOLS = [
    {
        "name": "pipeline_auto_voiceover",
        "description": "Auto-generate Edge TTS voiceover and overlay on video",
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {"type": "string", "description": "Input video path"},
                "text": {"type": "string", "description": "Voiceover text"},
                "voice": {"type": "string", "enum": ["yasmin", "osman"], "default": "yasmin"},
            },
            "required": ["video_path", "text"],
        },
    },
    {
        "name": "pipeline_auto_slideshow",
        "description": "Auto-create slideshow from image directory with optional voiceover",
        "parameters": {
            "type": "object",
            "properties": {
                "image_dir": {"type": "string", "description": "Directory with images"},
                "seconds_per_image": {"type": "number", "default": 3.0},
                "transition": {"type": "string", "default": "fade"},
                "voiceover": {"type": "string", "description": "Voiceover text (optional)"},
                "voice": {"type": "string", "default": "yasmin"},
            },
            "required": ["image_dir"],
        },
    },
    {
        "name": "pipeline_auto_thumbnail_grid",
        "description": "Extract multiple thumbnails from video for grid preview",
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {"type": "string", "description": "Input video path"},
                "count": {"type": "integer", "default": 6},
            },
            "required": ["video_path"],
        },
    },
    {
        "name": "pipeline_auto_trim_silence",
        "description": "Auto-trim silent parts from video",
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {"type": "string", "description": "Input video path"},
                "threshold": {"type": "number", "default": 0.02},
            },
            "required": ["video_path"],
        },
    },
    {
        "name": "pipeline_auto_export_all",
        "description": "Auto-export video in multiple formats (1080p, 720p, 480p, square, vertical)",
        "parameters": {
            "type": "object",
            "properties": {
                "video_path": {"type": "string", "description": "Input video path"},
            },
            "required": ["video_path"],
        },
    },
]
