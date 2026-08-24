"""
Editor Agent — video editing, image generation, stock media, media processing.
Integrates FFmpeg, MoviePy, Pillow, Pexels API, Edge TTS, Google Drive, Pinterest.
"""

import os
import re
from agents.base_agent import BaseAgent
from core.tools.media_tools import (
    video_probe, video_trim, video_concat, video_overlay,
    video_add_audio, video_add_text, video_add_subtitles,
    video_from_images, video_export, video_add_transition,
    video_speed, video_crop, video_to_gif, video_color_grade, video_remove_audio,
    generate_thumbnail, image_resize, image_composite, image_filter,
    audio_extract, audio_trim, audio_normalize,
)
from core.tools.stock_tools import (
    search_stock_image, search_stock_video,
    download_stock_image, download_stock_video,
    get_curated_photos, get_popular_videos,
)
from core.tools.image_tools import (
    generate_poster, generate_banner, generate_instagram_post,
    generate_youtube_thumbnail, generate_quote_image,
    generate_gradient, add_watermark, batch_generate_posters,
)
from core.tools.gdrive_tools import GDriveMediaTools
from core.tools.pinterest_tools import PinterestTools
from core.tools.ai_tools import AIGenerateTools
from core.tools.google_flow_tools import GoogleFlowTools
from core.tools.pipeline_tools import VideoPipeline


class EditorAgent(BaseAgent):
    """Video editing, image generation, and media processing agent."""

    AGENT_TYPE = "editor"
    SOUL_FILE = "editor.md"

    APPROVAL_REQUIRED = {
        "batch_generate", "video_export", "download_stock_video",
        "gdrive_download_media", "pinterest_download_board",
        "video_add_voiceover",
    }

    def __init__(self, config=None, memory=None, model_router=None,
                 token_juice=None, approval_gate=None, **kwargs):
        super().__init__(
            config=config, memory=memory, model_router=model_router,
            token_juice=token_juice, approval_gate=approval_gate, **kwargs,
        )
        self.media_dir = (config or {}).get("media_dir",
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "media"))
        self._gdrive = GDriveMediaTools(
            remote_name=(config or {}).get("gdrive_remote", "gdrive")
        )
        self._pinterest = PinterestTools()
        self._ai_gen = AIGenerateTools(media_dir=self.media_dir)
        self._google_flow = GoogleFlowTools(
            api_token=(config or {}).get("useapi_token", "")
        )
        self._pipeline = VideoPipeline(media_dir=self.media_dir)
        self._tts = None
        self._register_tools()

    def _get_tts(self):
        if self._tts is None:
            from core.voice.tts import TTS
            self._tts = TTS()
        return self._tts

    # ============================================================
    # RUN — accept natural language tasks from orchestrator
    # ============================================================

    async def run(self, task: str, context: dict | None = None) -> dict:
        """Execute editor task via natural language."""
        task_lower = task.lower()
        ctx = context or {}

        # Auto-detect intent and route to tools
        result = None

        # Video editing tasks
        if any(w in task_lower for w in ["trim", "cut", "potong"]):
            result = await self._handle_trim_task(task, ctx)
        elif any(w in task_lower for w in ["concat", "combine", "gabung", "merge"]):
            result = await self._handle_concat_task(task, ctx)
        elif any(w in task_lower for w in ["slideshow", "images to video", "gambar jadi video"]):
            result = await self._handle_slideshow_task(task, ctx)
        elif any(w in task_lower for w in ["gif", "animate"]):
            result = await self._handle_gif_task(task, ctx)
        elif any(w in task_lower for w in ["voiceover", "suara", "narrate", "tts"]):
            result = await self._handle_voiceover_task(task, ctx)
        elif any(w in task_lower for w in ["speed", "laju", "perlahan", "slow", "fast"]):
            result = await self._handle_speed_task(task, ctx)
        elif any(w in task_lower for w in ["crop", "potong gambar", "resize"]):
            result = await self._handle_crop_task(task, ctx)
        elif any(w in task_lower for w in ["color", "warna", "grade", "filter"]):
            result = await self._handle_color_task(task, ctx)
        elif any(w in task_lower for w in ["mute", "remove audio", "buang audio"]):
            result = await self._handle_mute_task(task, ctx)
        elif any(w in task_lower for w in ["thumbnail", "thumb"]):
            result = await self._handle_thumbnail_task(task, ctx)

        # Image generation tasks
        elif any(w in task_lower for w in ["poster", "banner", "flyer"]):
            result = await self._handle_poster_task(task, ctx)
        elif any(w in task_lower for w in ["instagram", "social media", "post"]):
            result = await self._handle_social_task(task, ctx)
        elif any(w in task_lower for w in ["youtube", "thumbnail"]):
            result = await self._handle_youtube_task(task, ctx)
        elif any(w in task_lower for w in ["quote", "kata"]):
            result = await self._handle_quote_task(task, ctx)

        # Stock media
        elif any(w in task_lower for w in ["stock", "footage", "pexels"]):
            result = await self._handle_stock_task(task, ctx)

        # Google Drive
        elif any(w in task_lower for w in ["gdrive", "google drive", "drive"]):
            result = await self._handle_gdrive_task(task, ctx)

        # Pinterest
        elif any(w in task_lower for w in ["pinterest", "pin"]):
            result = await self._handle_pinterest_task(task, ctx)

        # AI Image Generation
        elif any(w in task_lower for w in ["generate image", "ai image", "ai gambar", "stable diffusion"]):
            result = await self._handle_ai_image_task(task, ctx)
        elif any(w in task_lower for w in ["ai poster", "ai thumbnail"]):
            result = await self._handle_ai_poster_task(task, ctx)

        # Google Flow
        elif any(w in task_lower for w in ["google flow", "veo", "imagen", "ai video"]):
            result = await self._handle_google_flow_task(task, ctx)

        # Pipeline automation
        elif any(w in task_lower for w in ["auto voiceover", "auto suara", "pipeline"]):
            result = await self._handle_pipeline_task(task, ctx)
        elif any(w in task_lower for w in ["slideshow", "auto slideshow"]):
            result = await self._handle_slideshow_pipeline_task(task, ctx)
        elif any(w in task_lower for w in ["export all", "export multiple", "multi export"]):
            result = await self._handle_export_all_task(task, ctx)
        elif any(w in task_lower for w in ["trim silence", "buang senyap"]):
            result = await self._handle_trim_silence_task(task, ctx)
        elif any(w in task_lower for w in ["thumbnail grid", "grid thumbnail"]):
            result = await self._handle_thumbnail_grid_task(task, ctx)

        # Probe/inspect
        elif any(w in task_lower for w in ["probe", "inspect", "info", "metadata"]):
            result = await self._handle_probe_task(task, ctx)

        if result:
            if self.memory:
                self.memory.store(
                    f"Editor completed: {task[:80]}",
                    source="agent", agent="editor",
                )
            return result

        # Fallback: use LLM to understand and suggest
        response = await self.think(
            f"Editor task: {task}\n\nAvailable capabilities: "
            "video trim/concat/crop/speed/gif, image generation (poster/banner/social), "
            "stock media search, Google Drive, Pinterest, TTS voiceover. "
            "Respond with which tool to use and parameters.",
            context=f"Available tools: {list(self.tools.keys())}"
        )
        return {"agent": "editor", "text": response, "status": "ok"}

    # ---- Task Handlers ----

    async def _handle_trim_task(self, task: str, ctx: dict) -> dict:
        input_path = ctx.get("input") or ctx.get("video")
        if not input_path:
            return {"ok": False, "error": "perlu input video path"}
        start = ctx.get("start", 0)
        end = ctx.get("end", 10)
        output = ctx.get("output")
        return await self._video_trim(input_path, start, end, output)

    async def _handle_concat_task(self, task: str, ctx: dict) -> dict:
        inputs = ctx.get("inputs") or ctx.get("videos")
        if not inputs:
            return {"ok": False, "error": "perlu list video paths"}
        return await self._video_concat(inputs, ctx.get("output"))

    async def _handle_slideshow_task(self, task: str, ctx: dict) -> dict:
        images = ctx.get("images")
        if not images:
            return {"ok": False, "error": "perlu list image paths"}
        return await self._video_from_images(images, ctx.get("output"),
            seconds_per_image=ctx.get("seconds_per_image", 3.0))

    async def _handle_gif_task(self, task: str, ctx: dict) -> dict:
        input_path = ctx.get("input") or ctx.get("video")
        if not input_path:
            return {"ok": False, "error": "perlu input video path"}
        from core.tools.media_tools import video_to_gif
        output = ctx.get("output", os.path.join(self.media_dir, "gif",
            f"{os.path.splitext(os.path.basename(input_path))[0]}.gif"))
        os.makedirs(os.path.dirname(output), exist_ok=True)
        return video_to_gif(input_path, output,
            start=ctx.get("start", 0), duration=ctx.get("duration", 5.0),
            fps=ctx.get("fps", 15))

    async def _handle_voiceover_task(self, task: str, ctx: dict) -> dict:
        text = ctx.get("text") or ctx.get("narration")
        video = ctx.get("input") or ctx.get("video")
        if not text:
            return {"ok": False, "error": "perlu text untuk voiceover"}
        return await self._video_add_voiceover(video, text,
            voice=ctx.get("voice", "yasmin"),
            output=ctx.get("output"))

    async def _handle_speed_task(self, task: str, ctx: dict) -> dict:
        input_path = ctx.get("input") or ctx.get("video")
        if not input_path:
            return {"ok": False, "error": "perlu input video path"}
        # Parse speed from task
        speed = ctx.get("speed", 1.0)
        if "2x" in task or "double" in task or "laju" in task:
            speed = 2.0
        elif "half" in task or "perlahan" in task or "slow" in task:
            speed = 0.5
        elif "0.5x" in task:
            speed = 0.5
        return await self._video_speed(input_path, speed, ctx.get("output"))

    async def _handle_crop_task(self, task: str, ctx: dict) -> dict:
        input_path = ctx.get("input") or ctx.get("video") or ctx.get("image")
        if not input_path:
            return {"ok": False, "error": "perlu input path"}
        return await self._video_crop(input_path, ctx.get("output"),
            x=ctx.get("x", 0), y=ctx.get("y", 0),
            width=ctx.get("width"), height=ctx.get("height"))

    async def _handle_color_task(self, task: str, ctx: dict) -> dict:
        input_path = ctx.get("input") or ctx.get("video")
        if not input_path:
            return {"ok": False, "error": "perlu input video path"}
        return await self._video_color_grade(input_path, ctx.get("output"),
            brightness=ctx.get("brightness", 0.0),
            contrast=ctx.get("contrast", 1.0),
            saturation=ctx.get("saturation", 1.0),
            gamma=ctx.get("gamma", 1.0))

    async def _handle_mute_task(self, task: str, ctx: dict) -> dict:
        input_path = ctx.get("input") or ctx.get("video")
        if not input_path:
            return {"ok": False, "error": "perlu input video path"}
        return await self._video_remove_audio(input_path, ctx.get("output"))

    async def _handle_thumbnail_task(self, task: str, ctx: dict) -> dict:
        input_path = ctx.get("input") or ctx.get("video")
        if not input_path:
            return {"ok": False, "error": "perlu input video path"}
        return await self._generate_thumbnail(input_path, ctx.get("output"),
            time=ctx.get("time", 1.0))

    async def _handle_poster_task(self, task: str, ctx: dict) -> dict:
        title = ctx.get("title") or task
        return await self._generate_poster(title,
            subtitle=ctx.get("subtitle", ""),
            output_path=ctx.get("output"),
            bg_color=ctx.get("color", "#1a1a2e"))

    async def _handle_social_task(self, task: str, ctx: dict) -> dict:
        text = ctx.get("text") or task
        return await self._generate_instagram_post(text,
            output_path=ctx.get("output"),
            bg_color=ctx.get("color", "#4a4e69"))

    async def _handle_youtube_task(self, task: str, ctx: dict) -> dict:
        title = ctx.get("title") or task
        return await self._generate_youtube_thumbnail(title,
            output_path=ctx.get("output"),
            bg_image=ctx.get("bg_image"))

    async def _handle_quote_task(self, task: str, ctx: dict) -> dict:
        quote = ctx.get("quote") or task
        return await self._generate_quote_image(quote,
            author=ctx.get("author", ""),
            output_path=ctx.get("output"))

    async def _handle_stock_task(self, task: str, ctx: dict) -> dict:
        query = ctx.get("query") or task
        media_type = ctx.get("type", "image")
        if media_type == "video":
            return await self._search_stock_video(query,
                per_page=ctx.get("limit", 10))
        return await self._search_stock_image(query,
            per_page=ctx.get("limit", 10))

    async def _handle_gdrive_task(self, task: str, ctx: dict) -> dict:
        action = ctx.get("action", "browse")
        if action == "search":
            return await self._gdrive_search_media(ctx.get("query", ""),
                folder=ctx.get("folder", ""))
        elif action == "download":
            return await self._gdrive_download_media(ctx.get("remote_path", ""))
        elif action == "storage":
            return await self._gdrive_get_storage_info()
        return await self._gdrive_browse_folder(ctx.get("path", ""))

    async def _handle_pinterest_task(self, task: str, ctx: dict) -> dict:
        query = ctx.get("query") or task
        return await self._pinterest_search(query,
            limit=ctx.get("limit", 20))

    async def _handle_ai_image_task(self, task: str, ctx: dict) -> dict:
        prompt = ctx.get("prompt") or task
        return await self._ai_generate_image(prompt,
            negative_prompt=ctx.get("negative", ""),
            width=ctx.get("width", 512),
            height=ctx.get("height", 512),
            steps=ctx.get("steps", 30),
            seed=ctx.get("seed"))

    async def _handle_ai_poster_task(self, task: str, ctx: dict) -> dict:
        title = ctx.get("title") or task
        return await self._ai_generate_poster(title,
            style=ctx.get("style", "cinematic"),
            prompt=ctx.get("prompt", ""))

    async def _handle_google_flow_task(self, task: str, ctx: dict) -> dict:
        prompt = ctx.get("prompt") or task
        media_type = ctx.get("type", "image")
        if media_type == "video" or any(w in task_lower for w in ["video", "veo"]):
            return await self._google_flow_generate_video(prompt,
                model=ctx.get("model", "veo-3.1-fast"),
                duration=ctx.get("duration", "8s"))
        return await self._google_flow_generate_image(prompt,
            model=ctx.get("model", "imagen-4"))

    async def _handle_pipeline_task(self, task: str, ctx: dict) -> dict:
        video = ctx.get("video") or ctx.get("input")
        text = ctx.get("text") or ctx.get("narration")
        if not video or not text:
            return {"ok": False, "error": "perlu video path dan text"}
        return await self._pipeline_auto_voiceover(video, text,
            voice=ctx.get("voice", "yasmin"))

    async def _handle_slideshow_pipeline_task(self, task: str, ctx: dict) -> dict:
        image_dir = ctx.get("image_dir") or ctx.get("images")
        if not image_dir:
            return {"ok": False, "error": "perlu image directory"}
        return await self._pipeline_auto_slideshow(image_dir,
            seconds_per_image=ctx.get("seconds_per_image", 3.0),
            transition=ctx.get("transition", "fade"),
            voiceover=ctx.get("voiceover", ""),
            voice=ctx.get("voice", "yasmin"))

    async def _handle_export_all_task(self, task: str, ctx: dict) -> dict:
        video = ctx.get("video") or ctx.get("input")
        if not video:
            return {"ok": False, "error": "perlu video path"}
        return await self._pipeline_auto_export_all(video)

    async def _handle_trim_silence_task(self, task: str, ctx: dict) -> dict:
        video = ctx.get("video") or ctx.get("input")
        if not video:
            return {"ok": False, "error": "perlu video path"}
        return await self._pipeline_auto_trim_silence(video,
            threshold=ctx.get("threshold", 0.02))

    async def _handle_thumbnail_grid_task(self, task: str, ctx: dict) -> dict:
        video = ctx.get("video") or ctx.get("input")
        if not video:
            return {"ok": False, "error": "perlu video path"}
        return await self._pipeline_auto_thumbnail_grid(video,
            count=ctx.get("count", 6))

    async def _handle_probe_task(self, task: str, ctx: dict) -> dict:
        path = ctx.get("input") or ctx.get("path")
        if not path:
            return {"ok": False, "error": "perlu file path"}
        return await self._video_probe(path)

    # ============================================================
    # TOOLS REGISTRATION
    # ============================================================

    def _register_tools(self):
        # Video tools
        self.register_tool("video_probe", self._video_probe)
        self.register_tool("video_trim", self._video_trim)
        self.register_tool("video_concat", self._video_concat)
        self.register_tool("video_overlay", self._video_overlay)
        self.register_tool("video_add_audio", self._video_add_audio)
        self.register_tool("video_add_text", self._video_add_text)
        self.register_tool("video_add_subtitles", self._video_add_subtitles)
        self.register_tool("video_from_images", self._video_from_images)
        self.register_tool("video_export", self._video_export)
        self.register_tool("video_add_transition", self._video_add_transition)
        self.register_tool("video_speed", self._video_speed)
        self.register_tool("video_crop", self._video_crop)
        self.register_tool("video_to_gif", self._video_to_gif)
        self.register_tool("video_color_grade", self._video_color_grade)
        self.register_tool("video_remove_audio", self._video_remove_audio)
        self.register_tool("video_add_voiceover", self._video_add_voiceover)

        # Image tools
        self.register_tool("image_resize", self._image_resize)
        self.register_tool("image_composite", self._image_composite)
        self.register_tool("image_filter", self._image_filter)
        self.register_tool("generate_thumbnail", self._generate_thumbnail)

        # Audio tools
        self.register_tool("audio_extract", self._audio_extract)
        self.register_tool("audio_trim", self._audio_trim)
        self.register_tool("audio_normalize", self._audio_normalize)

        # Stock media tools
        self.register_tool("search_stock_image", self._search_stock_image)
        self.register_tool("search_stock_video", self._search_stock_video)
        self.register_tool("download_stock_image", self._download_stock_image)
        self.register_tool("download_stock_video", self._download_stock_video)
        self.register_tool("get_curated_photos", self._get_curated_photos)
        self.register_tool("get_popular_videos", self._get_popular_videos)

        # Image generation tools
        self.register_tool("generate_poster", self._generate_poster)
        self.register_tool("generate_banner", self._generate_banner)
        self.register_tool("generate_instagram_post", self._generate_instagram_post)
        self.register_tool("generate_youtube_thumbnail", self._generate_youtube_thumbnail)
        self.register_tool("generate_quote_image", self._generate_quote_image)
        self.register_tool("generate_gradient", self._generate_gradient)
        self.register_tool("add_watermark", self._add_watermark)
        self.register_tool("batch_generate_posters", self._batch_generate_posters)

        # Google Drive tools
        self.register_tool("gdrive_search_media", self._gdrive_search_media)
        self.register_tool("gdrive_browse_folder", self._gdrive_browse_folder)
        self.register_tool("gdrive_download_media", self._gdrive_download_media)
        self.register_tool("gdrive_get_storage_info", self._gdrive_get_storage_info)
        self.register_tool("gdrive_upload_media", self._gdrive_upload_media)

        # Pinterest tools
        self.register_tool("pinterest_search", self._pinterest_search)
        self.register_tool("pinterest_search_images", self._pinterest_search_images)
        self.register_tool("pinterest_search_videos", self._pinterest_search_videos)
        self.register_tool("pinterest_download_pin", self._pinterest_download_pin)
        self.register_tool("pinterest_download_board", self._pinterest_download_board)
        self.register_tool("pinterest_list_downloads", self._pinterest_list_downloads)
        self.register_tool("pinterest_clear_downloads", self._pinterest_clear_downloads)

        # AI Image Generation tools
        self.register_tool("ai_generate_image", self._ai_generate_image)
        self.register_tool("ai_generate_poster", self._ai_generate_poster)
        self.register_tool("ai_generate_thumbnail", self._ai_generate_thumbnail)
        self.register_tool("ai_generate_status", self._ai_generate_status)

        # Google Flow tools
        self.register_tool("google_flow_generate_image", self._google_flow_generate_image)
        self.register_tool("google_flow_generate_video", self._google_flow_generate_video)
        self.register_tool("google_flow_image_to_video", self._google_flow_image_to_video)
        self.register_tool("google_flow_status", self._google_flow_status)

        # Video Pipeline tools
        self.register_tool("pipeline_auto_voiceover", self._pipeline_auto_voiceover)
        self.register_tool("pipeline_auto_slideshow", self._pipeline_auto_slideshow)
        self.register_tool("pipeline_auto_thumbnail_grid", self._pipeline_auto_thumbnail_grid)
        self.register_tool("pipeline_auto_trim_silence", self._pipeline_auto_trim_silence)
        self.register_tool("pipeline_auto_export_all", self._pipeline_auto_export_all)

    # ---- Video Tools ----

    async def _video_probe(self, input_path: str) -> dict:
        return video_probe(input_path)

    async def _video_trim(self, input_path: str, start: float, end: float,
                          output_path: str = None) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "trimmed",
                f"trim_{os.path.basename(input_path)}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return video_trim(input_path, start, end, output_path)

    async def _video_concat(self, input_paths: list, output_path: str = None) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "concat",
                f"concat_{len(input_paths)}_clips.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return video_concat(input_paths, output_path)

    async def _video_overlay(self, base_path: str, overlay_path: str,
                             output_path: str = None, x: int = 0,
                             y: int = 0, scale: float = 0.3) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "overlay",
                f"overlay_{os.path.basename(base_path)}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return video_overlay(base_path, overlay_path, output_path, x, y, scale)

    async def _video_add_audio(self, video_path: str, audio_path: str,
                               output_path: str = None, replace: bool = True) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "audio",
                f"audio_{os.path.basename(video_path)}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return video_add_audio(video_path, audio_path, output_path, replace)

    async def _video_add_text(self, input_path: str, text: str,
                              output_path: str = None, fontsize: int = 48,
                              fontcolor: str = "white", position: str = "center",
                              start: float = 0, end: float = None) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "text",
                f"text_{os.path.basename(input_path)}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return video_add_text(input_path, output_path, text, fontsize,
                              fontcolor, position, start=start, end=end)

    async def _video_add_subtitles(self, video_path: str, srt_path: str,
                                   output_path: str = None) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "subs",
                f"subs_{os.path.basename(video_path)}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return video_add_subtitles(video_path, srt_path, output_path)

    async def _video_from_images(self, image_paths: list, output_path: str = None,
                                 seconds_per_image: float = 3.0) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "slideshow",
                f"slideshow_{len(image_paths)}_images.mp4")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return video_from_images(image_paths, output_path,
                                 seconds_per_image=seconds_per_image)

    async def _video_export(self, input_path: str, output_path: str = None,
                            width: int = None, height: int = None,
                            fps: int = None) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "export",
                f"export_{os.path.basename(input_path)}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return video_export(input_path, output_path, width, height, fps)

    async def _video_add_transition(self, input_path: str, output_path: str = None,
                                    transition_type: str = "fade") -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "transitions",
                f"fade_{os.path.basename(input_path)}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return video_add_transition(input_path, output_path, transition_type)

    async def _video_speed(self, input_path: str, speed: float = 1.0,
                           output_path: str = None) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "speed",
                f"speed{speed}x_{os.path.basename(input_path)}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return video_speed(input_path, output_path, speed)

    async def _video_crop(self, input_path: str, output_path: str = None,
                          x: int = 0, y: int = 0,
                          width: int = None, height: int = None) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "cropped",
                f"crop_{os.path.basename(input_path)}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return video_crop(input_path, output_path, x, y, width, height)

    async def _video_to_gif(self, input_path: str, output_path: str = None,
                            start: float = 0, duration: float = 5.0,
                            fps: int = 15) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "gif",
                f"{os.path.splitext(os.path.basename(input_path))[0]}.gif")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return video_to_gif(input_path, output_path, start, duration, fps)

    async def _video_color_grade(self, input_path: str, output_path: str = None,
                                 brightness: float = 0.0, contrast: float = 1.0,
                                 saturation: float = 1.0, gamma: float = 1.0,
                                 temperature: float = 0.0) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "graded",
                f"graded_{os.path.basename(input_path)}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return video_color_grade(input_path, output_path, brightness,
            contrast, saturation, gamma, temperature)

    async def _video_remove_audio(self, input_path: str,
                                  output_path: str = None) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "muted",
                f"muted_{os.path.basename(input_path)}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return video_remove_audio(input_path, output_path)

    async def _video_add_voiceover(self, video_path: str = None,
                                   text: str = "", voice: str = "yasmin",
                                   output_path: str = None) -> dict:
        """Generate TTS audio and overlay on video."""
        tts = self._get_tts()
        tts_result = await tts.synthesize_async(text, voice_name=voice)
        if not tts_result.get("audio"):
            return {"ok": False, "error": tts_result.get("error", "TTS failed")}

        # Save TTS audio to temp file
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            f.write(tts_result["audio"])
            audio_path = f.name

        try:
            if video_path and os.path.exists(video_path):
                # Overlay TTS on video
                if not output_path:
                    output_path = os.path.join(self.media_dir, "voiceover",
                        f"vo_{os.path.basename(video_path)}")
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                result = video_add_audio(video_path, audio_path, output_path, replace=True)
            else:
                # Just return the TTS audio file
                if not output_path:
                    output_path = os.path.join(self.media_dir, "voiceover",
                        f"tts_{hash(text) % 100000}.mp3")
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                import shutil
                shutil.copy(audio_path, output_path)
                result = {"ok": True, "output": output_path}
        finally:
            try:
                os.unlink(audio_path)
            except Exception:
                pass

        result["engine"] = tts_result.get("engine", "edge-neural")
        result["voice"] = tts_result.get("voice", voice)
        return result

    # ---- Image Tools ----

    async def _image_resize(self, input_path: str, output_path: str = None,
                            width: int = None, height: int = None) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "resized",
                f"resized_{os.path.basename(input_path)}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return image_resize(input_path, output_path, width, height)

    async def _image_composite(self, layers: list, output_path: str = None,
                               width: int = 1920, height: int = 1080) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "composite",
                f"composite_{len(layers)}_layers.png")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return image_composite(layers, output_path, width, height)

    async def _image_filter(self, input_path: str, output_path: str = None,
                            brightness: float = 1.0, contrast: float = 1.0,
                            blur: int = 0, grayscale: bool = False) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "filtered",
                f"filtered_{os.path.basename(input_path)}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return image_filter(input_path, output_path, brightness, contrast,
                            blur, grayscale)

    async def _generate_thumbnail(self, video_path: str, output_path: str = None,
                                  time: float = 1.0) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "thumbnails",
                f"thumb_{os.path.basename(video_path)}.png")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return generate_thumbnail(video_path, output_path, time)

    # ---- Audio Tools ----

    async def _audio_extract(self, video_path: str, output_path: str = None) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "audio",
                f"extracted_{os.path.basename(video_path)}.mp3")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return audio_extract(video_path, output_path)

    async def _audio_trim(self, input_path: str, output_path: str,
                          start: float, end: float) -> dict:
        return audio_trim(input_path, output_path, start, end)

    async def _audio_normalize(self, input_path: str, output_path: str = None) -> dict:
        if not output_path:
            output_path = os.path.join(self.media_dir, "audio",
                f"norm_{os.path.basename(input_path)}")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        return audio_normalize(input_path, output_path)

    # ---- Stock Media Tools ----

    async def _search_stock_image(self, query: str, per_page: int = 10,
                                  orientation: str = None) -> dict:
        return search_stock_image(query, per_page=per_page,
                                  orientation=orientation,
                                  config=self.config)

    async def _search_stock_video(self, query: str, per_page: int = 10,
                                  orientation: str = None) -> dict:
        return search_stock_video(query, per_page=per_page,
                                  orientation=orientation,
                                  config=self.config)

    async def _download_stock_image(self, url: str, output_dir: str = None,
                                    filename: str = None) -> dict:
        return download_stock_image(url, output_dir, filename)

    async def _download_stock_video(self, url: str, output_dir: str = None,
                                    filename: str = None) -> dict:
        return download_stock_video(url, output_dir, filename)

    async def _get_curated_photos(self, per_page: int = 10) -> dict:
        return get_curated_photos(per_page=per_page, config=self.config)

    async def _get_popular_videos(self, per_page: int = 10) -> dict:
        return get_popular_videos(per_page=per_page, config=self.config)

    # ---- Image Generation Tools ----

    async def _generate_poster(self, title: str, subtitle: str = "",
                               output_path: str = None, width: int = 1080,
                               height: int = 1920, bg_color: str = "#1a1a2e",
                               bg_image: str = None) -> dict:
        return generate_poster(title, subtitle, output_path, width, height,
                               bg_color, bg_image=bg_image)

    async def _generate_banner(self, title: str, output_path: str = None,
                               width: int = 1200, height: int = 628,
                               bg_color: str = "#0f3460",
                               bg_image: str = None) -> dict:
        return generate_banner(title, output_path, width, height,
                               bg_color, bg_image=bg_image)

    async def _generate_instagram_post(self, text: str, output_path: str = None,
                                       bg_color: str = "#4a4e69") -> dict:
        return generate_instagram_post(text, output_path, bg_color)

    async def _generate_youtube_thumbnail(self, title: str, output_path: str = None,
                                          bg_image: str = None) -> dict:
        return generate_youtube_thumbnail(title, output_path, bg_image=bg_image)

    async def _generate_quote_image(self, quote: str, author: str = "",
                                    output_path: str = None) -> dict:
        return generate_quote_image(quote, author, output_path)

    async def _generate_gradient(self, output_path: str = None,
                                 color1: str = "#667eea",
                                 color2: str = "#764ba2") -> dict:
        return generate_gradient(color1=color1, color2=color2,
                                 output_path=output_path)

    async def _add_watermark(self, input_path: str, text: str,
                             output_path: str = None,
                             position: str = "bottom-right") -> dict:
        return add_watermark(input_path, output_path, text, position)

    async def _batch_generate_posters(self, items: list,
                                      output_dir: str = None) -> dict:
        return batch_generate_posters(items, output_dir)

    # ---- Google Drive Tools ----

    async def _gdrive_search_media(self, query: str, folder: str = "",
                                    media_type: str = "all",
                                    limit: int = 20) -> dict:
        return self._gdrive.search_media(query, folder, media_type, limit)

    async def _gdrive_browse_folder(self, path: str = "") -> dict:
        return self._gdrive.browse_folder(path)

    async def _gdrive_download_media(self, remote_path: str,
                                      local_dir: str = "") -> dict:
        return self._gdrive.download_media(remote_path, local_dir)

    async def _gdrive_get_storage_info(self) -> dict:
        return self._gdrive.get_storage_info()

    async def _gdrive_upload_media(self, local_path: str,
                                    remote_folder: str = "") -> dict:
        return self._gdrive.upload_media(local_path, remote_folder)

    # ---- Pinterest Tools ----

    async def _pinterest_search(self, query: str, limit: int = 20) -> dict:
        return self._pinterest.search(query, limit)

    async def _pinterest_search_images(self, query: str,
                                        limit: int = 20) -> dict:
        return self._pinterest.search_images(query, limit)

    async def _pinterest_search_videos(self, query: str,
                                        limit: int = 10) -> dict:
        return self._pinterest.search_videos(query, limit)

    async def _pinterest_download_pin(self, url: str) -> dict:
        return self._pinterest.download_pin(url)

    async def _pinterest_download_board(self, board_url: str,
                                         limit: int = 50) -> dict:
        return self._pinterest.download_board(board_url, limit)

    async def _pinterest_list_downloads(self) -> dict:
        return self._pinterest.list_downloads()

    async def _pinterest_clear_downloads(self) -> dict:
        return self._pinterest.clear_downloads()

    # ---- AI Image Generation Tools ----

    async def _ai_generate_image(self, prompt: str, output_path: str = None,
                                  negative_prompt: str = "",
                                  width: int = 512, height: int = 512,
                                  steps: int = 30, guidance_scale: float = 7.5,
                                  seed: int = None) -> dict:
        return self._ai_gen.generate_image(prompt, output_path,
            negative_prompt=negative_prompt, width=width, height=height,
            steps=steps, guidance_scale=guidance_scale, seed=seed)

    async def _ai_generate_poster(self, title: str, output_path: str = None,
                                   style: str = "cinematic",
                                   prompt: str = "") -> dict:
        return self._ai_gen.generate_poster_ai(title, style, output_path,
            prompt=prompt)

    async def _ai_generate_thumbnail(self, topic: str,
                                      output_path: str = None) -> dict:
        return self._ai_gen.generate_thumbnail_ai(topic, output_path)

    async def _ai_generate_status(self) -> dict:
        return self._ai_gen.status()

    # ---- Google Flow Tools ----

    async def _google_flow_generate_image(self, prompt: str,
                                           output_path: str = None,
                                           model: str = "imagen-4") -> dict:
        return self._google_flow.generate_image(prompt, model=model,
            output_path=output_path)

    async def _google_flow_generate_video(self, prompt: str,
                                           output_path: str = None,
                                           model: str = "veo-3.1-fast",
                                           duration: str = "8s",
                                           aspect_ratio: str = "16:9") -> dict:
        return self._google_flow.generate_video(prompt, model=model,
            duration=duration, aspect_ratio=aspect_ratio,
            output_path=output_path)

    async def _google_flow_image_to_video(self, image_path: str,
                                           prompt: str = "",
                                           output_path: str = None) -> dict:
        return self._google_flow.generate_video_from_image(image_path,
            prompt=prompt, output_path=output_path)

    async def _google_flow_status(self) -> dict:
        return self._google_flow.status()

    # ---- Video Pipeline Tools ----

    async def _pipeline_auto_voiceover(self, video_path: str, text: str,
                                        voice: str = "yasmin") -> dict:
        return await self._pipeline.auto_voiceover(video_path, text, voice)

    async def _pipeline_auto_slideshow(self, image_dir: str,
                                        seconds_per_image: float = 3.0,
                                        transition: str = "fade",
                                        voiceover: str = "",
                                        voice: str = "yasmin") -> dict:
        return await self._pipeline.auto_slideshow(image_dir,
            seconds_per_image=seconds_per_image, transition=transition,
            voiceover=voiceover, voice=voice)

    async def _pipeline_auto_thumbnail_grid(self, video_path: str,
                                             count: int = 6) -> dict:
        return await self._pipeline.auto_thumbnail_grid(video_path, count)

    async def _pipeline_auto_trim_silence(self, video_path: str,
                                           threshold: float = 0.02) -> dict:
        return await self._pipeline.auto_trim_silence(video_path, threshold)

    async def _pipeline_auto_export_all(self, video_path: str) -> dict:
        return await self._pipeline.auto_export_all(video_path)

    # ---- Background Task ----

    async def run_task(self) -> dict:
        """Background: check media directory status."""
        media_dir = self.media_dir
        total_files = 0
        total_size = 0
        if os.path.exists(media_dir):
            for root, dirs, files in os.walk(media_dir):
                for f in files:
                    fp = os.path.join(root, f)
                    total_files += 1
                    total_size += os.path.getsize(fp)
        return {
            "media_dir": media_dir,
            "exists": os.path.exists(media_dir),
            "total_files": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 1),
            "tts": self._get_tts().status(),
        }
