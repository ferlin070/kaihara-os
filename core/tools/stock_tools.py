"""
Stock Tools — Pexels API search + download for stock photos and videos.
Free: 200 requests/hour, 20,000/month.
"""

import os
import json
import time
import httpx
from pathlib import Path


PEXELS_API_BASE = "https://api.pexels.com"
DEFAULT_DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "media", "stock")


def _get_api_key(config: dict = None) -> str | None:
    """Get Pexels API key from config or environment."""
    if config and config.get("pexels_api_key"):
        return config["pexels_api_key"]
    return os.environ.get("PEXELS_API_KEY")


def _get_headers(api_key: str) -> dict:
    return {"Authorization": api_key}


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


# ============================================================
# Search Photos
# ============================================================

def search_stock_image(query: str, per_page: int = 10, page: int = 1,
                       orientation: str = None, size: str = None,
                       color: str = None, config: dict = None) -> dict:
    """Search Pexels for stock photos.
    orientation: landscape, portrait, square
    size: large, medium, small
    color: red, orange, yellow, green, turquoise, blue, violet, pink, brown, gray, black, white
    """
    api_key = _get_api_key(config)
    if not api_key:
        return {"ok": False, "error": "PEXELS_API_KEY not set. Get free key at pexels.com/api"}

    params = {"query": query, "per_page": min(per_page, 80), "page": page}
    if orientation:
        params["orientation"] = orientation
    if size:
        params["size"] = size
    if color:
        params["color"] = color

    try:
        r = httpx.get(f"{PEXELS_API_BASE}/v1/search", headers=_get_headers(api_key),
                       params=params, timeout=15)
        if r.status_code != 200:
            return {"ok": False, "error": f"Pexels API error: {r.status_code}"}
        data = r.json()
        results = []
        for photo in data.get("photos", []):
            results.append({
                "id": photo["id"],
                "width": photo["width"],
                "height": photo["height"],
                "photographer": photo["photographer"],
                "photographer_url": photo["photographer_url"],
                "url": photo["url"],
                "src": {
                    "original": photo["src"]["original"],
                    "large2x": photo["src"]["large2x"],
                    "large": photo["src"]["large"],
                    "medium": photo["src"]["medium"],
                    "small": photo["src"]["small"],
                    "tiny": photo["src"]["tiny"],
                },
            })
        return {
            "ok": True,
            "query": query,
            "total_results": data.get("total_results", 0),
            "page": data.get("page", page),
            "per_page": data.get("per_page", per_page),
            "photos": results,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# Search Videos
# ============================================================

def search_stock_video(query: str, per_page: int = 10, page: int = 1,
                       orientation: str = None, size: str = None,
                       config: dict = None) -> dict:
    """Search Pexels for stock videos.
    orientation: landscape, portrait, square
    size: large, medium, small
    """
    api_key = _get_api_key(config)
    if not api_key:
        return {"ok": False, "error": "PEXELS_API_KEY not set. Get free key at pexels.com/api"}

    params = {"query": query, "per_page": min(per_page, 80), "page": page}
    if orientation:
        params["orientation"] = orientation
    if size:
        params["size"] = size

    try:
        r = httpx.get(f"{PEXELS_API_BASE}/videos/search", headers=_get_headers(api_key),
                       params=params, timeout=15)
        if r.status_code != 200:
            return {"ok": False, "error": f"Pexels API error: {r.status_code}"}
        data = r.json()
        results = []
        for video in data.get("videos", []):
            video_files = video.get("video_files", [])
            # Pick best quality file
            best_file = None
            for f in sorted(video_files, key=lambda x: x.get("width", 0), reverse=True):
                if f.get("file_type") == "video/mp4":
                    best_file = f
                    break
            if not best_file and video_files:
                best_file = video_files[0]

            results.append({
                "id": video["id"],
                "width": video.get("width", 0),
                "height": video.get("height", 0),
                "duration": video.get("duration", 0),
                "url": video.get("url", ""),
                "image": video.get("image", ""),
                "best_file": {
                    "url": best_file.get("link", ""),
                    "width": best_file.get("width", 0),
                    "height": best_file.get("height", 0),
                    "quality": best_file.get("quality", ""),
                    "file_type": best_file.get("file_type", ""),
                } if best_file else None,
                "all_files": [
                    {
                        "url": f.get("link", ""),
                        "width": f.get("width", 0),
                        "height": f.get("height", 0),
                        "quality": f.get("quality", ""),
                    } for f in video_files
                ],
            })
        return {
            "ok": True,
            "query": query,
            "total_results": data.get("total_results", 0),
            "page": data.get("page", page),
            "per_page": data.get("per_page", per_page),
            "videos": results,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# Download
# ============================================================

def download_stock_image(url: str, output_dir: str = None,
                         filename: str = None, config: dict = None) -> dict:
    """Download a stock image from Pexels URL."""
    if not output_dir:
        output_dir = os.path.join(DEFAULT_DOWNLOAD_DIR, "images")
    _ensure_dir(output_dir)

    if not filename:
        filename = f"pexels_{int(time.time())}.jpg"
    output_path = os.path.join(output_dir, filename)

    try:
        r = httpx.get(url, timeout=60, follow_redirects=True)
        if r.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(r.content)
            return {
                "ok": True,
                "output": output_path,
                "size_kb": round(len(r.content) / 1024, 1),
            }
        return {"ok": False, "error": f"Download failed: {r.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def download_stock_video(url: str, output_dir: str = None,
                         filename: str = None, config: dict = None) -> dict:
    """Download a stock video from Pexels URL."""
    if not output_dir:
        output_dir = os.path.join(DEFAULT_DOWNLOAD_DIR, "videos")
    _ensure_dir(output_dir)

    if not filename:
        filename = f"pexels_{int(time.time())}.mp4"
    output_path = os.path.join(output_dir, filename)

    try:
        r = httpx.get(url, timeout=120, follow_redirects=True)
        if r.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(r.content)
            return {
                "ok": True,
                "output": output_path,
                "size_mb": round(len(r.content) / (1024 * 1024), 1),
            }
        return {"ok": False, "error": f"Download failed: {r.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# Curated Photos
# ============================================================

def get_curated_photos(per_page: int = 10, page: int = 1,
                       config: dict = None) -> dict:
    """Get curated photos from Pexels."""
    api_key = _get_api_key(config)
    if not api_key:
        return {"ok": False, "error": "PEXELS_API_KEY not set"}

    try:
        r = httpx.get(f"{PEXELS_API_BASE}/v1/curated", headers=_get_headers(api_key),
                       params={"per_page": per_page, "page": page}, timeout=15)
        if r.status_code != 200:
            return {"ok": False, "error": f"Pexels API error: {r.status_code}"}
        data = r.json()
        return {
            "ok": True,
            "photos": [
                {
                    "id": p["id"],
                    "photographer": p["photographer"],
                    "src": p["src"]["large"],
                } for p in data.get("photos", [])
            ],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# Popular Videos
# ============================================================

def get_popular_videos(per_page: int = 10, page: int = 1,
                       min_width: int = None, min_duration: int = None,
                       config: dict = None) -> dict:
    """Get popular videos from Pexels."""
    api_key = _get_api_key(config)
    if not api_key:
        return {"ok": False, "error": "PEXELS_API_KEY not set"}

    params = {"per_page": per_page, "page": page}
    if min_width:
        params["min_width"] = min_width
    if min_duration:
        params["min_duration"] = min_duration

    try:
        r = httpx.get(f"{PEXELS_API_BASE}/videos/popular", headers=_get_headers(api_key),
                       params=params, timeout=15)
        if r.status_code != 200:
            return {"ok": False, "error": f"Pexels API error: {r.status_code}"}
        data = r.json()
        return {
            "ok": True,
            "videos": [
                {
                    "id": v["id"],
                    "duration": v.get("duration", 0),
                    "image": v.get("image", ""),
                } for v in data.get("videos", [])
            ],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
