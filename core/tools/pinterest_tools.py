"""Image Search Tools — DuckDuckGo Images (relevant results, no API key)."""

import os
import re
import httpx
from typing import Any

MEDIA_DIR = os.path.join(os.path.expanduser("~"), ".kaihara", "media", "images")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}


class PinterestTools:
    def __init__(self):
        self._media_dir = MEDIA_DIR
        os.makedirs(self._media_dir, exist_ok=True)

    async def search_images(self, query: str, limit: int = 10) -> dict:
        """Search real images via Openverse API (free, no key)."""
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as c:
                r = await c.get(
                    "https://api.openverse.org/v1/images/",
                    params={"q": query, "page_size": limit * 3},
                    headers={"User-Agent": "KaiharaOS/1.0"})
                data = r.json()
                results = []
                for item in data.get("results", []):
                    w = int(item.get("width") or 0)
                    h = int(item.get("height") or 0)
                    url = item.get("url") or ""
                    thumb = item.get("thumbnail") or ""
                    if not url or (w and h and (w < 300 or h < 200)):
                        continue
                    results.append({
                        "url": url,
                        "thumbnail": thumb,
                        "title": item.get("title") or query,
                        "width": w,
                        "height": h,
                        "source": item.get("foreign_landing_url", ""),
                    })
                    if len(results) >= limit:
                        break
                if results:
                    return {"ok": True, "images": results, "count": len(results)}
                return {"ok": False, "error": "tiada hasil"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def search_videos(self, query: str, limit: int = 5) -> dict:
        return {"ok": True, "videos": [], "count": 0}

    async def download_pin(self, url: str) -> dict:
        try:
            filename = url.split("/")[-1].split("?")[0][:60] or "image.jpg"
            if "." not in filename:
                filename += ".jpg"
            filepath = os.path.join(self._media_dir, filename)
            async with httpx.AsyncClient(timeout=30, follow_redirects=True, headers=UA) as c:
                r = await c.get(url)
            with open(filepath, "wb") as f:
                f.write(r.content)
            return {"ok": True, "filepath": filepath, "size": len(r.content)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def download_board(self, board_url: str, limit: int = 50) -> dict:
        return {"ok": True, "downloaded": 0, "files": []}

    async def search_full(self, query: str, img_limit: int = 100, vid_limit: int = 30) -> dict:
        images = await self.search_images(query, img_limit)
        videos = await self.search_videos(query, vid_limit)
        return {"ok": True, "images": images.get("images", []),
                "videos": videos.get("videos", []), "query": query}
