"""
Image Tools — Generate posters, banners, thumbnails, social media images.
Uses Pillow for programmatic image creation.
"""

import os
import json
import math
from pathlib import Path
from datetime import datetime


DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "media", "generated")


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _get_font(size: int = 48, bold: bool = False):
    """Get font (try system fonts, fallback to default)."""
    from PIL import ImageFont
    font_paths = [
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            return ImageFont.truetype(fp, size)
    return ImageFont.load_default()


# ============================================================
# Poster Generation
# ============================================================

def generate_poster(title: str, subtitle: str = "", output_path: str = None,
                    width: int = 1080, height: int = 1920,
                    bg_color: str = "#1a1a2e", title_color: str = "#ffffff",
                    subtitle_color: str = "#e94560", bg_image: str = None) -> dict:
    """Generate a social media poster (Instagram story size)."""
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

        if bg_image and os.path.exists(bg_image):
            img = Image.open(bg_image).resize((width, height), Image.Resampling.LANCZOS)
            # Darken background
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(0.3)
        else:
            img = Image.new("RGB", (width, height), bg_color)

        draw = ImageDraw.Draw(img)

        # Title
        title_font = _get_font(min(width // 10, 72), bold=True)
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_w = title_bbox[2] - title_bbox[0]
        title_x = (width - title_w) // 2
        title_y = height // 2 - 100

        # Draw title with shadow
        draw.text((title_x + 2, title_y + 2), title, fill="#000000", font=title_font)
        draw.text((title_x, title_y), title, fill=title_color, font=title_font)

        # Subtitle
        if subtitle:
            sub_font = _get_font(min(width // 16, 36))
            sub_bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
            sub_w = sub_bbox[2] - sub_bbox[0]
            sub_x = (width - sub_w) // 2
            sub_y = title_y + (title_bbox[3] - title_bbox[1]) + 40
            draw.text((sub_x, sub_y), subtitle, fill=subtitle_color, font=sub_font)

        # Decorative line
        line_y = title_y - 30
        line_w = min(width // 3, 200)
        draw.line(
            [(width // 2 - line_w, line_y), (width // 2 + line_w, line_y)],
            fill=subtitle_color, width=3
        )

        if not output_path:
            _ensure_dir(DEFAULT_OUTPUT_DIR)
            output_path = os.path.join(DEFAULT_OUTPUT_DIR, f"poster_{int(datetime.now().timestamp())}.png")

        img.save(output_path, quality=95)
        return {"ok": True, "output": output_path, "size": [width, height]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# Banner Generation
# ============================================================

def generate_banner(title: str, output_path: str = None,
                    width: int = 1200, height: int = 628,
                    bg_color: str = "#0f3460", title_color: str = "#ffffff",
                    accent_color: str = "#e94560", bg_image: str = None) -> dict:
    """Generate a social media banner (Facebook/LinkedIn cover size)."""
    try:
        from PIL import Image, ImageDraw, ImageEnhance

        if bg_image and os.path.exists(bg_image):
            img = Image.open(bg_image).resize((width, height), Image.Resampling.LANCZOS)
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(0.4)
        else:
            img = Image.new("RGB", (width, height), bg_color)

        draw = ImageDraw.Draw(img)

        # Accent bar at bottom
        draw.rectangle([(0, height - 8), (width, height)], fill=accent_color)

        # Title
        title_font = _get_font(min(width // 12, 64), bold=True)
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_w = title_bbox[2] - title_bbox[0]
        title_x = (width - title_w) // 2
        title_y = (height - (title_bbox[3] - title_bbox[1])) // 2

        draw.text((title_x + 2, title_y + 2), title, fill="#000000", font=title_font)
        draw.text((title_x, title_y), title, fill=title_color, font=title_font)

        if not output_path:
            _ensure_dir(DEFAULT_OUTPUT_DIR)
            output_path = os.path.join(DEFAULT_OUTPUT_DIR, f"banner_{int(datetime.now().timestamp())}.png")

        img.save(output_path, quality=95)
        return {"ok": True, "output": output_path, "size": [width, height]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# Social Media Images
# ============================================================

def generate_instagram_post(text: str, output_path: str = None,
                            bg_color: str = "#4a4e69", text_color: str = "#ffffff",
                            width: int = 1080, height: int = 1080) -> dict:
    """Generate Instagram post (square)."""
    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        # Word wrap text
        font = _get_font(48, bold=True)
        lines = []
        words = text.split()
        current_line = ""
        max_w = width - 100
        for word in words:
            test = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_w and current_line:
                lines.append(current_line)
                current_line = word
            else:
                current_line = test
        if current_line:
            lines.append(current_line)

        # Draw text centered
        total_h = len(lines) * 60
        start_y = (height - total_h) // 2
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            lw = bbox[2] - bbox[0]
            x = (width - lw) // 2
            draw.text((x, start_y + i * 60), line, fill=text_color, font=font)

        if not output_path:
            _ensure_dir(DEFAULT_OUTPUT_DIR)
            output_path = os.path.join(DEFAULT_OUTPUT_DIR, f"ig_post_{int(datetime.now().timestamp())}.png")

        img.save(output_path, quality=95)
        return {"ok": True, "output": output_path}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def generate_youtube_thumbnail(title: str, output_path: str = None,
                                width: int = 1280, height: int = 720,
                                bg_color: str = "#ff0000", text_color: str = "#ffffff",
                                bg_image: str = None) -> dict:
    """Generate YouTube thumbnail."""
    try:
        from PIL import Image, ImageDraw, ImageEnhance

        if bg_image and os.path.exists(bg_image):
            img = Image.open(bg_image).resize((width, height), Image.Resampling.LANCZOS)
            enhancer = ImageEnhance.Brightness(img)
            img = enhancer.enhance(0.5)
        else:
            img = Image.new("RGB", (width, height), bg_color)

        draw = ImageDraw.Draw(img)

        # Large bold title
        title_font = _get_font(min(width // 8, 96), bold=True)
        # Word wrap
        lines = []
        words = title.split()
        current_line = ""
        max_w = width - 100
        for word in words:
            test = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test, font=title_font)
            if bbox[2] - bbox[0] > max_w and current_line:
                lines.append(current_line)
                current_line = word
            else:
                current_line = test
        if current_line:
            lines.append(current_line)

        total_h = len(lines) * 110
        start_y = (height - total_h) // 2
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=title_font)
            lw = bbox[2] - bbox[0]
            x = (width - lw) // 2
            # Shadow
            draw.text((x + 3, start_y + i * 110 + 3), line, fill="#000000", font=title_font)
            draw.text((x, start_y + i * 110), line, fill=text_color, font=title_font)

        if not output_path:
            _ensure_dir(DEFAULT_OUTPUT_DIR)
            output_path = os.path.join(DEFAULT_OUTPUT_DIR, f"yt_thumb_{int(datetime.now().timestamp())}.png")

        img.save(output_path, quality=95)
        return {"ok": True, "output": output_path}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# Quote Image
# ============================================================

def generate_quote_image(quote: str, author: str = "", output_path: str = None,
                         width: int = 1080, height: int = 1080,
                         bg_color: str = "#2d3436", quote_color: str = "#ffffff",
                         author_color: str = "#fdcb6e") -> dict:
    """Generate a quote image for social media."""
    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)

        # Quote marks
        quote_mark_font = _get_font(120, bold=True)
        draw.text((80, 80), '"', fill=author_color, font=quote_mark_font)

        # Quote text
        quote_font = _get_font(min(width // 15, 42))
        # Word wrap
        lines = []
        words = quote.split()
        current_line = ""
        max_w = width - 200
        for word in words:
            test = f"{current_line} {word}".strip()
            bbox = draw.textbbox((0, 0), test, font=quote_font)
            if bbox[2] - bbox[0] > max_w and current_line:
                lines.append(current_line)
                current_line = word
            else:
                current_line = test
        if current_line:
            lines.append(current_line)

        total_h = len(lines) * 55
        start_y = (height - total_h) // 2
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=quote_font)
            lw = bbox[2] - bbox[0]
            x = (width - lw) // 2
            draw.text((x, start_y + i * 55), line, fill=quote_color, font=quote_font)

        # Author
        if author:
            author_font = _get_font(min(width // 20, 28), bold=True)
            author_text = f"— {author}"
            bbox = draw.textbbox((0, 0), author_text, font=author_font)
            aw = bbox[2] - bbox[0]
            draw.text(((width - aw) // 2, start_y + total_h + 40), author_text,
                      fill=author_color, font=author_font)

        if not output_path:
            _ensure_dir(DEFAULT_OUTPUT_DIR)
            output_path = os.path.join(DEFAULT_OUTPUT_DIR, f"quote_{int(datetime.now().timestamp())}.png")

        img.save(output_path, quality=95)
        return {"ok": True, "output": output_path}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# Gradient Background
# ============================================================

def generate_gradient(width: int = 1920, height: int = 1080,
                      color1: str = "#667eea", color2: str = "#764ba2",
                      direction: str = "vertical", output_path: str = None) -> dict:
    """Generate gradient background image."""
    try:
        from PIL import Image

        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip("#")
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        c1 = hex_to_rgb(color1)
        c2 = hex_to_rgb(color2)

        img = Image.new("RGB", (width, height))
        pixels = img.load()

        for y in range(height):
            for x in range(width):
                if direction == "vertical":
                    ratio = y / height
                elif direction == "horizontal":
                    ratio = x / width
                elif direction == "diagonal":
                    ratio = (x + y) / (width + height)
                else:
                    ratio = y / height

                r = int(c1[0] + (c2[0] - c1[0]) * ratio)
                g = int(c1[1] + (c2[1] - c1[1]) * ratio)
                b = int(c1[2] + (c2[2] - c1[2]) * ratio)
                pixels[x, y] = (r, g, b)

        if not output_path:
            _ensure_dir(DEFAULT_OUTPUT_DIR)
            output_path = os.path.join(DEFAULT_OUTPUT_DIR, f"gradient_{int(datetime.now().timestamp())}.png")

        img.save(output_path, quality=95)
        return {"ok": True, "output": output_path, "size": [width, height]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# Text Watermark
# ============================================================

def add_watermark(input_path: str, output_path: str, text: str,
                  position: str = "bottom-right", opacity: int = 128,
                  font_size: int = 24) -> dict:
    """Add text watermark to image."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.open(input_path).convert("RGBA")
        txt_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(txt_layer)
        font = _get_font(font_size)

        bbox = draw.textbbox((0, 0), text, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        w, h = img.size

        pos_map = {
            "top-left": (20, 20),
            "top-right": (w - tw - 20, 20),
            "bottom-left": (20, h - th - 20),
            "bottom-right": (w - tw - 20, h - th - 20),
            "center": ((w - tw) // 2, (h - th) // 2),
        }
        pos = pos_map.get(position, pos_map["bottom-right"])
        draw.text(pos, text, fill=(255, 255, 255, opacity), font=font)

        result = Image.alpha_composite(img, txt_layer).convert("RGB")
        result.save(output_path)
        return {"ok": True, "output": output_path}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# Batch Generation
# ============================================================

def batch_generate_posters(items: list, output_dir: str = None) -> dict:
    """Generate multiple posters. items = [{"title": ..., "subtitle": ..., "bg_color": ...}]"""
    if not output_dir:
        _ensure_dir(DEFAULT_OUTPUT_DIR)
        output_dir = DEFAULT_OUTPUT_DIR

    results = []
    for i, item in enumerate(items):
        path = os.path.join(output_dir, f"poster_batch_{i+1}.png")
        r = generate_poster(
            title=item.get("title", "Untitled"),
            subtitle=item.get("subtitle", ""),
            output_path=path,
            bg_color=item.get("bg_color", "#1a1a2e"),
        )
        results.append(r)

    return {
        "ok": all(r.get("ok") for r in results),
        "generated": len([r for r in results if r.get("ok")]),
        "failed": len([r for r in results if not r.get("ok")]),
        "outputs": [r.get("output") for r in results if r.get("ok")],
    }
