"""
Editor Agent — video editing, image generation, stock media, media processing.
Integrates FFmpeg, MoviePy, Pillow, Pexels API, and Google Flow MCP.
"""

import os
from agents.base_agent import BaseAgent
from core.tools.media_tools import (
    video_probe, video_trim, video_concat, video_overlay,
    video_add_audio, video_add_text, video_add_subtitles,
    video_from_images, video_export, video_add_transition,
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


class EditorAgent(BaseAgent):
    """Video editing, image generation, and media processing agent."""

    AGENT_TYPE = "editor"

    APPROVAL_REQUIRED = {
        "batch_generate", "video_export", "download_stock_video",
    }

    def __init__(self, config=None, memory=None, model_router=None,
                 token_juice=None, approval_gate=None, **kwargs):
        super().__init__(
            config=config, memory=memory, model_router=model_router,
            token_juice=token_juice, approval_gate=approval_gate, **kwargs,
        )
        self.media_dir = (config or {}).get("media_dir",
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "media"))
        self._register_tools()

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

        # Image generation tools
        self.register_tool("generate_poster", self._generate_poster)
        self.register_tool("generate_banner", self._generate_banner)
        self.register_tool("generate_instagram_post", self._generate_instagram_post)
        self.register_tool("generate_youtube_thumbnail", self._generate_youtube_thumbnail)
        self.register_tool("generate_quote_image", self._generate_quote_image)
        self.register_tool("generate_gradient", self._generate_gradient)
        self.register_tool("add_watermark", self._add_watermark)
        self.register_tool("batch_generate_posters", self._batch_generate_posters)

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
        }
