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
            # Lib API: search(query, page_size=25) / get_board_pins(url, page_size=25)
            if query:
                results = p.search(query, page_size=limit)
            elif board_url:
                results = p.get_board_pins(board_url, page_size=limit)
            else:
                return {"ok": False, "error": "query or board_url required"}

            pins = results.get("pins", []) if isinstance(results, dict) else []
            files = []
            for pin in pins:
                if not isinstance(pin, dict):
                    continue
                title = str(pin.get("title") or pin.get("description")
                            or "untitled")[:60]
                media_type = pin.get("media_type", "image")
                img = pin.get("image")
                if isinstance(img, dict):
                    img_url = img.get("orig") or img.get("medium") or ""
                else:
                    img_url = str(img or "")
                if not img_url and pin.get("url"):
                    img_url = pin["url"]

                filename = f"{title[:50]}_{abs(hash(img_url)) % 10000}.jpg"
                local_path = os.path.join(self._media_dir, filename)

                files.append({
                    "title": title,
                    "type": media_type,
                    "url": img_url,
                    "local_path": local_path,
                })

            note = ("Pinterest may require login cookies for search "
                    "results." ) if not files else ""
            return {"ok": True, "files": files, "total": len(files),
                    "note": note}
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


# ============================================================
# Full Media Search — pagination + real image/video resolution
# ============================================================

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 Chrome/124.0 Safari/537.36")


def _resolve_pin_media(pin_url: str) -> dict:
    """Fetch a pin page and extract direct i.pinimg/v1.pinimg media URLs."""
    try:
        r = httpx.get(pin_url, headers={"User-Agent": _UA},
                      follow_redirects=True, timeout=15)
        html = r.text
        imgs = re.findall(r"https://i\.pinimg\.com/[^\"\\\\ ]+", html)
        originals = [u for u in imgs if "/originals/" in u]
        others = sorted(set(u.split("?")[0] for u in imgs))
        image = (originals[0] if originals
                 else (others[0] if others else None))
        vids = re.findall(r"https://v1?\.pinimg\.com/[^\"\\\\ ]+\.mp4", html)
        return {
            "pin": pin_url,
            "image": image,
            "video": vids[0] if vids else None,
        }
    except Exception:
        return {"pin": pin_url, "image": None, "video": None}


def _pick_best_image(images) -> tuple[str | None, str | None]:
    """Pick largest image URL + thumbnail from lib images dict."""
    if not isinstance(images, dict):
        return None, None
    best_url, best_w, thumb_url = None, -1, None
    for key, meta in images.items():
        u = meta.get("url") if isinstance(meta, dict) else meta
        if not u:
            continue
        if "originals" in u:
            thumb = images.get("236x", {}).get("url", u)
            return u, thumb
        w = meta.get("width", 0) if isinstance(meta, dict) else 0
        if isinstance(w, int) and w > best_w:
            best_w = w
            best_url = u
            thumb_url = images.get("170x", {}).get("url", u)
    return best_url, (thumb_url or best_url)


def search_full(query: str, target_images: int = 100,
                target_videos: int = 30) -> dict:
    """Search with pagination until enough pins, resolve real media URLs.

    Returns dict with files[] containing:
    title, type(image|video), url(direct media), thumb(image), source(pin url)
    """
    from concurrent.futures import ThreadPoolExecutor

    from pinterest_downloader import Pinterest
    p = Pinterest()

    def _paginate(scope: str, target: int) -> list[dict]:
        collected, bookmark = [], None
        for _page in range(10):  # safety cap
            try:
                kwargs = {"page_size": 25}
                if bookmark:
                    kwargs["bookmark"] = bookmark
                if scope != "pins":
                    kwargs["scope"] = scope
                r = p.search(query, **kwargs)
            except Exception as e:
                if "scope" in str(e).lower():
                    r = p.search(query, page_size=25)
                    if not isinstance(r, dict):
                        break
                    kwargs.pop("scope", None)
                else:
                    break
            pins = r.get("pins", []) if isinstance(r, dict) else []
            if not pins:
                break
            collected.extend(pins)
            bookmark = r.get("bookmark")
            if len(collected) >= target or not bookmark:
                break
        # Dedupe by url
        seen, uniq = set(), []
        for pin in collected:
            u = pin.get("url") or pin.get("link") or ""
            if u and u not in seen:
                seen.add(u)
                uniq.append(pin)
        return uniq[:target]

    # Gather pins via pagination (images + video scope attempt)
    image_pins = _paginate("pins", target_images)
    try:
        video_pins = _paginate("videos", min(target_videos, 30))
    except Exception:
        video_pins = []

    # Build files directly from pins' built-in images dict (fast!)
    seen_ids, files = set(), []
    img_count = vid_count = 0

    def _add_pin(pin, default_type):
        nonlocal img_count, vid_count
        pid = str(pin.get("id", ""))
        if not pid or pid in seen_ids:
            return
        seen_ids.add(pid)
        best, thumb = _pick_best_image(pin.get("images"))
        if not best:
            return
        is_vid = (str(pin.get("media_type", "")).lower() == "video"
                  or default_type == "video")
        title = str(pin.get("description")
                    or pin.get("title")
                    or f"Pin {pid}").strip()[:60] or f"Pin {pid}"
        eng = pin.get("engagement")
        files.append({
            "id": pid,
            "title": title,
            "type": "video" if is_vid else "image",
            "thumb": thumb or best,
            "url": best,
            "source": f"https://www.pinterest.com/pin/{pid}/",
            "engagement": eng if isinstance(eng, int) else None,
        })
        if is_vid:
            vid_count += 1
        else:
            img_count += 1

    for pin in image_pins:
        if img_count >= target_images:
            break
        _add_pin(pin, "image")
    for pin in video_pins:
        if vid_count >= target_videos:
            break
        _add_pin(pin, "video")

    images_count, videos_count = img_count, vid_count
    note = ""
    if not files:
        note = ("Pinterest blocked anonymous access. "
                "Cuba query lain atau tambah cookies.")
    return {
        "ok": True,
        "files": files,
        "total": len(files),
        "images": images_count,
        "videos": videos_count,
        "note": note,
    }
