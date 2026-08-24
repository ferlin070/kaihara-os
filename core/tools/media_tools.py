"""
Media Tools — FFmpeg, MoviePy, Pillow video/image processing.
Comprehensive toolkit for video assembly, image manipulation, and media operations.
"""

import os
import subprocess
import json
import tempfile
from pathlib import Path
from datetime import datetime


# ============================================================
# FFmpeg Helpers
# ============================================================

def _ffmpeg_bin() -> str:
    """Find ffmpeg binary."""
    for p in ["ffmpeg", "/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        try:
            subprocess.run([p, "-version"], capture_output=True, timeout=5)
            return p
        except Exception:
            continue
    return "ffmpeg"


def _ffprobe_bin() -> str:
    """Find ffprobe binary."""
    for p in ["ffprobe", "/usr/bin/ffprobe", "/usr/local/bin/ffprobe"]:
        try:
            subprocess.run([p, "-version"], capture_output=True, timeout=5)
            return p
        except Exception:
            continue
    return "ffprobe"


def _run_ffmpeg(args: list, timeout: int = 300) -> dict:
    """Run ffmpeg command and return result."""
    ffmpeg = _ffmpeg_bin()
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout[-1000:] if result.stdout else "",
            "stderr": result.stderr[-1000:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"FFmpeg timed out ({timeout}s)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _run_ffprobe(args: list) -> dict:
    """Run ffprobe command."""
    ffprobe = _ffprobe_bin()
    cmd = [ffprobe, "-hide_banner"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return {"ok": result.returncode == 0, "output": result.stdout, "error": result.stderr}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# Video Probe / Metadata
# ============================================================

def video_probe(input_path: str) -> dict:
    """Get video metadata (duration, resolution, codec, fps)."""
    cmd = [
        "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", input_path
    ]
    r = _run_ffprobe(cmd)
    if not r.get("ok"):
        return {"ok": False, "error": r.get("error", "probe failed")}
    try:
        data = json.loads(r["output"])
        fmt = data.get("format", {})
        streams = data.get("streams", [])
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})
        return {
            "ok": True,
            "duration": float(fmt.get("duration", 0)),
            "size_mb": round(int(fmt.get("size", 0)) / (1024 * 1024), 1),
            "bitrate_kbps": round(int(fmt.get("bit_rate", 0)) / 1000),
            "video": {
                "codec": video_stream.get("codec_name", ""),
                "width": video_stream.get("width", 0),
                "height": video_stream.get("height", 0),
                "fps": eval(video_stream.get("r_frame_rate", "0/1")) if "/" in str(video_stream.get("r_frame_rate", "0")) else float(video_stream.get("r_frame_rate", 0)),
            } if video_stream else None,
            "audio": {
                "codec": audio_stream.get("codec_name", ""),
                "sample_rate": audio_stream.get("sample_rate", ""),
                "channels": audio_stream.get("channels", 0),
            } if audio_stream else None,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# Video Trim / Cut
# ============================================================

def video_trim(input_path: str, start: float, end: float, output_path: str) -> dict:
    """Trim video from start to end (seconds)."""
    duration = end - start
    args = [
        "-ss", str(start), "-i", input_path,
        "-t", str(duration), "-c", "copy", output_path
    ]
    r = _run_ffmpeg(args)
    if r.get("ok") and os.path.exists(output_path):
        probe = video_probe(output_path)
        return {"ok": True, "output": output_path, "duration": probe.get("duration", 0)}
    return {"ok": False, "error": r.get("stderr", "trim failed")}


# ============================================================
# Video Concatenate
# ============================================================

def video_concat(input_paths: list, output_path: str, transition: str = None) -> dict:
    """Concatenate multiple videos into one."""
    if not input_paths:
        return {"ok": False, "error": "No input files"}

    # Create concat list file
    concat_file = os.path.join(tempfile.gettempdir(), "concat_list.txt")
    with open(concat_file, "w") as f:
        for p in input_paths:
            f.write(f"file '{os.path.abspath(p)}'\n")

    args = [
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-c", "copy", output_path
    ]
    r = _run_ffmpeg(args)
    try:
        os.remove(concat_file)
    except Exception:
        pass
    if r.get("ok") and os.path.exists(output_path):
        probe = video_probe(output_path)
        return {"ok": True, "output": output_path, "duration": probe.get("duration", 0)}
    return {"ok": False, "error": r.get("stderr", "concat failed")}


# ============================================================
# Video Overlay (Picture-in-Picture)
# ============================================================

def video_overlay(base_path: str, overlay_path: str, output_path: str,
                  x: int = 0, y: int = 0, scale: float = 0.3) -> dict:
    """Overlay one video on another (picture-in-picture)."""
    args = [
        "-i", base_path, "-i", overlay_path,
        "-filter_complex",
        f"[1:v]scale=iw*{scale}:ih*{scale}[ov];[0:v][ov]overlay={x}:{y}",
        "-c:a", "copy", output_path
    ]
    r = _run_ffmpeg(args)
    if r.get("ok") and os.path.exists(output_path):
        return {"ok": True, "output": output_path}
    return {"ok": False, "error": r.get("stderr", "overlay failed")}


# ============================================================
# Video Add Audio
# ============================================================

def video_add_audio(video_path: str, audio_path: str, output_path: str,
                    replace: bool = True, volume: float = 1.0) -> dict:
    """Add audio track to video. replace=True replaces original audio."""
    if replace:
        args = [
            "-i", video_path, "-i", audio_path,
            "-c:v", "copy",
            "-map", "0:v:0", "-map", "1:a:0",
            "-shortest", output_path
        ]
    else:
        args = [
            "-i", video_path, "-i", audio_path,
            "-filter_complex",
            f"[1:a]volume={volume}[a];[0:a][a]amix=inputs=2:duration=first",
            "-c:v", "copy", output_path
        ]
    r = _run_ffmpeg(args)
    if r.get("ok") and os.path.exists(output_path):
        return {"ok": True, "output": output_path}
    return {"ok": False, "error": r.get("stderr", "add audio failed")}


# ============================================================
# Video Add Text / Subtitles
# ============================================================

def video_add_text(input_path: str, output_path: str, text: str,
                   fontsize: int = 48, fontcolor: str = "white",
                   position: str = "center", bg_color: str = None,
                   start: float = 0, end: float = None) -> dict:
    """Add text overlay to video."""
    # Position mapping
    pos_map = {
        "center": "x=(w-text_w)/2:y=(h-text_h)/2",
        "top": "x=(w-text_w)/2:y=50",
        "bottom": "x=(w-text_w)/2:y=h-text_h-50",
        "top-left": "x=50:y=50",
        "top-right": "x=w-text_w-50:y=50",
        "bottom-left": "x=50:y=h-text_h-50",
        "bottom-right": "x=w-text_w-50:y=h-text_h-50",
    }
    pos = pos_map.get(position, pos_map["center"])

    # Build drawtext filter
    escaped_text = text.replace("'", "\\'").replace(":", "\\:")
    drawtext = f"drawtext=text='{escaped_text}':fontsize={fontsize}:fontcolor={fontcolor}:{pos}"
    if bg_color:
        drawtext += f":box=1:boxcolor={bg_color}@0.7:boxborderw=10"
    if end:
        drawtext += f":enable='between(t,{start},{end})'"
    else:
        drawtext += f":enable='gte(t,{start})'"

    args = [
        "-i", input_path,
        "-vf", drawtext,
        "-c:a", "copy", output_path
    ]
    r = _run_ffmpeg(args)
    if r.get("ok") and os.path.exists(output_path):
        return {"ok": True, "output": output_path}
    return {"ok": False, "error": r.get("stderr", "add text failed")}


def video_add_subtitles(video_path: str, srt_path: str, output_path: str,
                        fontsize: int = 24, fontcolor: str = "white") -> dict:
    """Burn subtitles into video."""
    args = [
        "-i", video_path,
        "-vf", f"subtitles={srt_path}:force_style='FontSize={fontsize},PrimaryColour=&Hffffff'",
        "-c:a", "copy", output_path
    ]
    r = _run_ffmpeg(args)
    if r.get("ok") and os.path.exists(output_path):
        return {"ok": True, "output": output_path}
    return {"ok": False, "error": r.get("stderr", "subtitles failed")}


# ============================================================
# Video from Images (Slideshow)
# ============================================================

def video_from_images(image_paths: list, output_path: str,
                      fps: int = 30, seconds_per_image: float = 3.0,
                      transition: str = "fade", width: int = 1920, height: int = 1080) -> dict:
    """Create video from a list of images with optional transitions."""
    if not image_paths:
        return {"ok": False, "error": "No images provided"}

    # Use moviepy for slideshow with transitions
    try:
        from moviepy import ImageClip, concatenate_videoclips
        clips = []
        for img in image_paths:
            clip = ImageClip(img, duration=seconds_per_image)
            clip = clip.resized((width, height))
            if transition == "fade":
                clip = clip.with_effects([
                    __import__("moviepy").video.fx.CrossFadeIn(0.5),
                    __import__("moviepy").video.fx.CrossFadeOut(0.5),
                ])
            clips.append(clip)

        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(output_path, fps=fps, codec="libx264",
                              audio=False, logger=None)
        final.close()
        return {"ok": True, "output": output_path, "clips": len(clips)}
    except ImportError:
        # Fallback to ffmpeg
        duration_per = seconds_per_image
        input_args = []
        for img in image_paths:
            input_args.extend(["-loop", "1", "-t", str(duration_per), "-i", img])

        filter_parts = []
        for i in range(len(image_paths)):
            filter_parts.append(f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]")

        concat_inputs = "".join(f"[v{i}]" for i in range(len(image_paths)))
        filter_parts.append(f"{concat_inputs}concat=n={len(image_paths)}:v=1:a=0[outv]")
        filter_complex = ";".join(filter_parts)

        args = input_args + [
            "-filter_complex", filter_complex,
            "-map", "[outv]", "-r", str(fps),
            "-pix_fmt", "yuv420p", output_path
        ]
        r = _run_ffmpeg(args)
        if r.get("ok") and os.path.exists(output_path):
            return {"ok": True, "output": output_path, "clips": len(image_paths)}
        return {"ok": False, "error": r.get("stderr", "slideshow failed")}


# ============================================================
# Video Export with Settings
# ============================================================

def video_export(input_path: str, output_path: str,
                 width: int = None, height: int = None,
                 fps: int = None, bitrate: str = "2M",
                 codec: str = "libx264", audio_codec: str = "aac") -> dict:
    """Export video with custom settings."""
    args = ["-i", input_path]
    vf_parts = []
    if width and height:
        vf_parts.append(f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2")
    if fps:
        args.extend(["-r", str(fps)])
    if vf_parts:
        args.extend(["-vf", ",".join(vf_parts)])
    args.extend(["-c:v", codec, "-b:v", bitrate, "-c:a", audio_codec, output_path])

    r = _run_ffmpeg(args)
    if r.get("ok") and os.path.exists(output_path):
        probe = video_probe(output_path)
        return {"ok": True, "output": output_path, "duration": probe.get("duration", 0)}
    return {"ok": False, "error": r.get("stderr", "export failed")}


# ============================================================
# Image Tools (Pillow)
# ============================================================

def image_resize(input_path: str, output_path: str,
                 width: int = None, height: int = None) -> dict:
    """Resize image."""
    try:
        from PIL import Image
        img = Image.open(input_path)
        if width and height:
            img = img.resize((width, height), Image.Resampling.LANCZOS)
        elif width:
            ratio = width / img.width
            img = img.resize((width, int(img.height * ratio)), Image.Resampling.LANCZOS)
        elif height:
            ratio = height / img.height
            img = img.resize((int(img.width * ratio), height), Image.Resampling.LANCZOS)
        img.save(output_path)
        return {"ok": True, "output": output_path, "size": list(img.size)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def image_composite(layers: list, output_path: str, width: int = 1920, height: int = 1080) -> dict:
    """Composite multiple images (layers) into one. layers = [{"path": ..., "x": 0, "y": 0, "opacity": 1.0}]"""
    try:
        from PIL import Image
        base = Image.new("RGBA", (width, height), (0, 0, 0, 255))
        for layer in layers:
            img = Image.open(layer["path"]).convert("RGBA")
            if "width" in layer or "height" in layer:
                w = layer.get("width", img.width)
                h = layer.get("height", img.height)
                img = img.resize((w, h), Image.Resampling.LANCZOS)
            opacity = layer.get("opacity", 1.0)
            if opacity < 1.0:
                img.putalpha(int(opacity * 255))
            base.paste(img, (layer.get("x", 0), layer.get("y", 0)), img)
        base.convert("RGB").save(output_path)
        return {"ok": True, "output": output_path}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def image_filter(input_path: str, output_path: str,
                 brightness: float = 1.0, contrast: float = 1.0,
                 blur: int = 0, grayscale: bool = False) -> dict:
    """Apply filters to image."""
    try:
        from PIL import Image, ImageEnhance, ImageFilter
        img = Image.open(input_path)
        if brightness != 1.0:
            img = ImageEnhance.Brightness(img).enhance(brightness)
        if contrast != 1.0:
            img = ImageEnhance.Contrast(img).enhance(contrast)
        if blur > 0:
            img = img.filter(ImageFilter.GaussianBlur(blur))
        if grayscale:
            img = img.convert("L")
        img.save(output_path)
        return {"ok": True, "output": output_path}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def generate_thumbnail(video_path: str, output_path: str, time: float = 1.0) -> dict:
    """Extract thumbnail from video at specified time."""
    args = [
        "-ss", str(time), "-i", video_path,
        "-vframes", "1", "-q:v", "2", output_path
    ]
    r = _run_ffmpeg(args)
    if r.get("ok") and os.path.exists(output_path):
        return {"ok": True, "output": output_path}
    return {"ok": False, "error": r.get("stderr", "thumbnail failed")}


# ============================================================
# Video Transition
# ============================================================

def video_add_transition(input_path: str, output_path: str,
                         transition_type: str = "fade", duration: float = 1.0) -> dict:
    """Add fade in/out transition to video."""
    vf = f"fade=t=in:st=0:d={duration},fade=t=out:st=9999:d={duration}"
    # Get duration to set fade out correctly
    probe = video_probe(input_path)
    if probe.get("ok"):
        dur = probe["duration"]
        vf = f"fade=t=in:st=0:d={duration},fade=t=out:st={dur - duration}:d={duration}"

    args = [
        "-i", input_path,
        "-vf", vf,
        "-c:a", "copy", output_path
    ]
    r = _run_ffmpeg(args)
    if r.get("ok") and os.path.exists(output_path):
        return {"ok": True, "output": output_path}
    return {"ok": False, "error": r.get("stderr", "transition failed")}


# ============================================================
# Audio Tools
# ============================================================

def audio_extract(video_path: str, output_path: str) -> dict:
    """Extract audio from video."""
    args = ["-i", video_path, "-vn", "-c:a", "copy", output_path]
    r = _run_ffmpeg(args)
    if r.get("ok") and os.path.exists(output_path):
        return {"ok": True, "output": output_path}
    return {"ok": False, "error": r.get("stderr", "extract audio failed")}


def audio_trim(input_path: str, output_path: str, start: float, end: float) -> dict:
    """Trim audio."""
    duration = end - start
    args = [
        "-ss", str(start), "-i", input_path,
        "-t", str(duration), "-c", "copy", output_path
    ]
    r = _run_ffmpeg(args)
    if r.get("ok") and os.path.exists(output_path):
        return {"ok": True, "output": output_path}
    return {"ok": False, "error": r.get("stderr", "audio trim failed")}


def audio_normalize(input_path: str, output_path: str, target_db: float = -16.0) -> dict:
    """Normalize audio volume."""
    args = [
        "-i", input_path,
        "-af", f"loudnorm=I={target_db}:TP=-1.5:LRA=11",
        output_path
    ]
    r = _run_ffmpeg(args)
    if r.get("ok") and os.path.exists(output_path):
        return {"ok": True, "output": output_path}
    return {"ok": False, "error": r.get("stderr", "normalize failed")}


# ============================================================
# Video Speed
# ============================================================

def video_speed(input_path: str, output_path: str, speed: float = 1.0) -> dict:
    """Change video speed. speed=2.0 = 2x faster, speed=0.5 = half speed."""
    if speed <= 0:
        return {"ok": False, "error": "speed must be > 0"}
    pts = 1.0 / speed
    args = [
        "-i", input_path,
        "-vf", f"setpts={pts}*PTS",
        "-af", f"atempo={min(max(speed, 0.5), 2.0)}",
        output_path
    ]
    r = _run_ffmpeg(args)
    if r.get("ok") and os.path.exists(output_path):
        probe = video_probe(output_path)
        return {"ok": True, "output": output_path, "duration": probe.get("duration", 0)}
    return {"ok": False, "error": r.get("stderr", "speed change failed")}


# ============================================================
# Video Crop
# ============================================================

def video_crop(input_path: str, output_path: str,
               x: int = 0, y: int = 0, width: int = None, height: int = None) -> dict:
    """Crop video to region. If width/height not set, crops to center square."""
    probe = video_probe(input_path)
    if not probe.get("ok"):
        return {"ok": False, "error": "cannot probe video"}
    vw = probe.get("video", {}).get("width", 1920)
    vh = probe.get("video", {}).get("height", 1080)
    if not width and not height:
        side = min(vw, vh)
        width = side
        height = side
        x = (vw - side) // 2
        y = (vh - side) // 2
    elif not width:
        width = vw
    elif not height:
        height = vh

    args = [
        "-i", input_path,
        "-vf", f"crop={width}:{height}:{x}:{y}",
        "-c:a", "copy", output_path
    ]
    r = _run_ffmpeg(args)
    if r.get("ok") and os.path.exists(output_path):
        return {"ok": True, "output": output_path, "size": [width, height]}
    return {"ok": False, "error": r.get("stderr", "crop failed")}


# ============================================================
# Video to GIF
# ============================================================

def video_to_gif(input_path: str, output_path: str,
                 start: float = 0, duration: float = 5.0, fps: int = 15) -> dict:
    """Convert video segment to GIF."""
    palette_path = os.path.join(tempfile.gettempdir(), "palette.png")
    # Generate palette for better quality
    _run_ffmpeg([
        "-ss", str(start), "-t", str(duration), "-i", input_path,
        "-vf", f"fps={fps},palettegen=stats_mode=diff",
        "-y", palette_path
    ])
    # Generate GIF with palette
    args = [
        "-ss", str(start), "-t", str(duration), "-i", input_path,
        "-i", palette_path,
        "-lavfi", f"fps={fps} [x]; [x][1:v] paletteuse=dither=bayer:bayer_scale=5",
        output_path
    ]
    r = _run_ffmpeg(args)
    try:
        os.remove(palette_path)
    except Exception:
        pass
    if r.get("ok") and os.path.exists(output_path):
        size_kb = os.path.getsize(output_path) / 1024
        return {"ok": True, "output": output_path, "size_kb": round(size_kb, 1)}
    return {"ok": False, "error": r.get("stderr", "gif conversion failed")}


# ============================================================
# Video Color Grade
# ============================================================

def video_color_grade(input_path: str, output_path: str,
                      brightness: float = 0.0, contrast: float = 1.0,
                      saturation: float = 1.0, gamma: float = 1.0,
                      temperature: float = 0.0) -> dict:
    """Color grade video. brightness: -1.0 to 1.0, contrast/saturation: 0.0 to 3.0,
    gamma: 0.1 to 10.0, temperature: -1.0 (cool) to 1.0 (warm)."""
    filters = []
    if brightness != 0.0:
        filters.append(f"eq=brightness={brightness}")
    if contrast != 1.0:
        filters.append(f"eq=contrast={contrast}")
    if saturation != 1.0:
        filters.append(f"eq=saturation={saturation}")
    if gamma != 1.0:
        filters.append(f"eq=gamma={gamma}")
    if temperature != 0.0:
        # Colorbalance for temperature
        rs = max(-1, min(1, temperature * 0.3))
        gs = 0
        bs = max(-1, min(1, -temperature * 0.3))
        filters.append(f"colorbalance=rs={rs}:gs={gs}:bs={bs}")

    if not filters:
        return {"ok": False, "error": "no color adjustments specified"}

    vf = ",".join(filters)
    args = [
        "-i", input_path,
        "-vf", vf,
        "-c:a", "copy", output_path
    ]
    r = _run_ffmpeg(args)
    if r.get("ok") and os.path.exists(output_path):
        return {"ok": True, "output": output_path}
    return {"ok": False, "error": r.get("stderr", "color grade failed")}


# ============================================================
# Video Remove Audio
# ============================================================

def video_remove_audio(input_path: str, output_path: str) -> dict:
    """Remove audio track from video (mute)."""
    args = [
        "-i", input_path,
        "-an", "-c:v", "copy", output_path
    ]
    r = _run_ffmpeg(args)
    if r.get("ok") and os.path.exists(output_path):
        return {"ok": True, "output": output_path}
    return {"ok": False, "error": r.get("stderr", "remove audio failed")}
