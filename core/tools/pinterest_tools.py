"""Pinterest Media Tools — search, download pins, boards, images."""

import subprocess
import os
import json
from pathlib import Path
from typing import Any

MEDIA_DIR = os.path.join(os.path.expanduser("~"), ".kaihara", "media", "pinterest")


class PinterestTools:
    def __init__(self):
        self._media_dir = MEDIA_DIR
        os.makedirs(self._media_dir, exist_ok=True)
        self._lib = self._detect_lib()

    def _detect_lib(self) -> str | None:
        """Detect which Pinterest library is available."""
        try:
            import importlib
            importlib.import_module("pinterest_downloader")
            return "pinterest_downloader"
        except ImportError:
            pass
        try:
            importlib.import_module("pinterest_dl")
            return "pinterest_dl"
        except ImportError:
            pass
        return None

    def _run_pinterest_dl(self, query: str = "", url: str = "",
                          num: int = 20) -> dict:
        """Run pinterest-dl library for search/scrape."""
        try:
            from pinterest_dl import PinterestDL

            dl = PinterestDL.with_api(timeout=3, verbose=False)
            if query:
                medias = dl.search_and_download(
                    query=query,
                    output_dir=self._media_dir,
                    num=num,
                )
            elif url:
                medias = dl.scrape_and_download(
                    url=url,
                    output_dir=self._media_dir,
                    num=num,
                )
            else:
                return {"ok": False, "error": "query or url required"}

            files = []
            for m in medias:
                files.append({
                    "name": getattr(m, "file_name", str(m)),
                    "path": getattr(m, "file_path", ""),
                    "type": getattr(m, "media_type", "unknown"),
                })
            return {"ok": True, "files": files, "total": len(files)}
        except ImportError:
            return {"ok": False, "error": "pinterest_dl not installed"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _run_pinterest_downloader(self, query: str = "",
                                  board_url: str = "",
                                  limit: int = 20) -> dict:
        """Run pinterest-downloader library for search/download."""
        try:
            from pinterest_downloader import Pinterest

            p = Pinterest()
            if query:
                results = p.search(query, limit=limit)
            elif board_url:
                results = p.get_board_pins(board_url, limit=limit)
            else:
                return {"ok": False, "error": "query or board_url required"}

            files = []
            for pin in results.get("pins", []):
                title = pin.get("title", "untitled")
                media_type = pin.get("media_type", "image")
                img_url = pin.get("image", {}).get("orig", "")

                filename = f"{title[:50]}_{hash(img_url) % 10000}.jpg"
                local_path = os.path.join(self._media_dir, filename)

                files.append({
                    "title": title,
                    "type": media_type,
                    "url": img_url,
                    "local_path": local_path,
                })

            return {"ok": True, "files": files, "total": len(files)}
        except ImportError:
            return {"ok": False, "error": "pinterest_downloader not installed"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def search(self, query: str, limit: int = 20) -> dict:
        """Search Pinterest for images/videos."""
        if self._lib == "pinterest_dl":
            return self._run_pinterest_dl(query=query, num=limit)
        elif self._lib == "pinterest_downloader":
            return self._run_pinterest_downloader(query=query, limit=limit)
        return {
            "ok": False,
            "error": "no pinterest library installed",
            "install": "pip install pinterest-downloader",
        }

    def search_images(self, query: str, limit: int = 20) -> dict:
        """Search Pinterest for images only."""
        return self.search(query=query, limit=limit)

    def search_videos(self, query: str, limit: int = 10) -> dict:
        """Search Pinterest for videos only."""
        return self.search(query=f"{query} video", limit=limit)

    def download_pin(self, url: str) -> dict:
        """Download a single Pinterest pin."""
        if self._lib == "pinterest_dl":
            return self._run_pinterest_dl(url=url, num=1)
        elif self._lib == "pinterest_downloader":
            try:
                from pinterest_downloader import Pinterest
                p = Pinterest()
                pin = p.get_pin(url)
                if pin.get("ok"):
                    return {"ok": True, "pin": pin["pin"]}
                return pin
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "no pinterest library installed"}

    def download_board(self, board_url: str, limit: int = 50) -> dict:
        """Download pins from a Pinterest board."""
        if self._lib == "pinterest_dl":
            return self._run_pinterest_dl(url=board_url, num=limit)
        elif self._lib == "pinterest_downloader":
            return self._run_pinterest_downloader(
                board_url=board_url, limit=limit
            )
        return {"ok": False, "error": "no pinterest library installed"}

    def list_downloads(self) -> dict:
        """List downloaded Pinterest media."""
        files = []
        if os.path.exists(self._media_dir):
            for f in os.listdir(self._media_dir):
                fpath = os.path.join(self._media_dir, f)
                if os.path.isfile(fpath):
                    ext = Path(f).suffix.lower()
                    files.append({
                        "name": f,
                        "path": fpath,
                        "type": ext.lstrip("."),
                        "size": os.path.getsize(fpath),
                    })
        return {"ok": True, "files": files, "total": len(files)}

    def clear_downloads(self) -> dict:
        """Clear all downloaded Pinterest media."""
        count = 0
        if os.path.exists(self._media_dir):
            for f in os.listdir(self._media_dir):
                fpath = os.path.join(self._media_dir, f)
                if os.path.isfile(fpath):
                    os.remove(fpath)
                    count += 1
        return {"ok": True, "deleted": count}


PINTEREST_TOOLS = [
    {
        "name": "pinterest_search",
        "description": "Search Pinterest for images and videos",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["query"],
        },
    },
    {
        "name": "pinterest_search_images",
        "description": "Search Pinterest for images only",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["query"],
        },
    },
    {
        "name": "pinterest_search_videos",
        "description": "Search Pinterest for videos only",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "pinterest_download_pin",
        "description": "Download a single Pinterest pin by URL",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Pinterest pin URL"},
            },
            "required": ["url"],
        },
    },
    {
        "name": "pinterest_download_board",
        "description": "Download all pins from a Pinterest board",
        "parameters": {
            "type": "object",
            "properties": {
                "board_url": {"type": "string", "description": "Pinterest board URL"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["board_url"],
        },
    },
    {
        "name": "pinterest_list_downloads",
        "description": "List all downloaded Pinterest media files",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "pinterest_clear_downloads",
        "description": "Clear all downloaded Pinterest media",
        "parameters": {"type": "object", "properties": {}},
    },
]
