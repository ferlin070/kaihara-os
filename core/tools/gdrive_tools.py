"""Google Drive Media Tools — search, browse, download media files."""

import subprocess
import json
import os
from pathlib import Path
from typing import Any

MEDIA_EXTENSIONS = {
    "video": [".mp4", ".avi", ".mkv", ".mov", ".webm", ".flv", ".wmv"],
    "image": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"],
    "audio": [".mp3", ".wav", ".ogg", ".flac", ".m4a"],
}


class GDriveMediaTools:
    def __init__(self, remote_name: str = "gdrive"):
        self.remote_name = remote_name
        self._rclone = self._find_rclone()

    def _find_rclone(self) -> str | None:
        try:
            for p in ["rclone", "/usr/bin/rclone"]:
                result = subprocess.run(
                    [p, "version"], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return p
        except Exception:
            pass
        return None

    def _run_rclone(self, args: list[str], timeout: int = 60) -> dict:
        if not self._rclone:
            return {"ok": False, "error": "rclone not installed"}
        try:
            result = subprocess.run(
                [self._rclone] + args,
                capture_output=True, text=True, timeout=timeout
            )
            return {
                "ok": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "timeout"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def search_media(self, query: str, folder: str = "",
                     media_type: str = "all", limit: int = 20) -> dict:
        """Search for media files in Google Drive."""
        remote = f"{self.remote_name}:"
        if folder:
            remote += folder

        args = ["lsjson", remote, "--fast-list"]
        result = self._run_rclone(args, timeout=30)
        if not result["ok"]:
            return result

        try:
            files = json.loads(result["stdout"])
        except json.JSONDecodeError:
            return {"ok": False, "error": "failed to parse listing"}

        query_lower = query.lower()
        exts = []
        if media_type in ("all", "video"):
            exts.extend(MEDIA_EXTENSIONS["video"])
        if media_type in ("all", "image"):
            exts.extend(MEDIA_EXTENSIONS["image"])
        if media_type in ("all", "audio"):
            exts.extend(MEDIA_EXTENSIONS["audio"])

        matches = []
        for f in files:
            name = f.get("Path", f.get("Name", ""))
            if query_lower in name.lower():
                ext = Path(name).suffix.lower()
                if ext in exts:
                    matches.append({
                        "name": name,
                        "size": f.get("Size", 0),
                        "modified": f.get("ModTime", ""),
                        "type": ext.lstrip("."),
                    })
                    if len(matches) >= limit:
                        break

        return {"ok": True, "results": matches, "total": len(matches)}

    def browse_folder(self, path: str = "") -> dict:
        """Browse folder structure in Google Drive."""
        remote = f"{self.remote_name}:"
        if path:
            remote += path

        result = self._run_rclone(["lsjson", remote], timeout=30)
        if not result["ok"]:
            return result

        try:
            files = json.loads(result["stdout"])
        except json.JSONDecodeError:
            return {"ok": False, "error": "failed to parse listing"}

        folders = [f for f in files if f.get("IsDir")]
        media_files = [f for f in files if not f.get("IsDir")]

        return {
            "ok": True,
            "path": path or "/",
            "folders": [
                {"name": f.get("Path", ""), "size": f.get("Size", 0)}
                for f in folders[:50]
            ],
            "files": [
                {
                    "name": f.get("Path", ""),
                    "size": f.get("Size", 0),
                    "type": Path(f.get("Path", "")).suffix.lower(),
                    "modified": f.get("ModTime", ""),
                }
                for f in media_files[:50]
            ],
            "total_folders": len(folders),
            "total_files": len(media_files),
        }

    def download_media(self, remote_path: str, local_dir: str = "") -> dict:
        """Download a media file from Google Drive."""
        src = f"{self.remote_name}:{remote_path}"
        if not local_dir:
            local_dir = os.path.join(os.path.expanduser("~"), "Downloads")

        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, Path(remote_path).name)

        result = self._run_rclone(
            ["copy", src, local_path, "--progress"],
            timeout=300
        )
        if not result["ok"]:
            return result

        return {
            "ok": True,
            "remote": remote_path,
            "local": local_path,
            "size": os.path.getsize(local_path) if os.path.exists(local_path) else 0,
        }

    def get_storage_info(self) -> dict:
        """Get Google Drive storage info."""
        remote = f"{self.remote_name}:"
        result = self._run_rclone(["about", remote, "--json"], timeout=15)
        if not result["ok"]:
            return result

        try:
            data = json.loads(result["stdout"])
            return {
                "ok": True,
                "used": data.get("used", 0),
                "total": data.get("total", 0),
                "free": data.get("free", 0),
            }
        except json.JSONDecodeError:
            return {"ok": False, "error": "failed to parse storage info"}

    def upload_media(self, local_path: str, remote_folder: str = "") -> dict:
        """Upload a media file to Google Drive."""
        dest = f"{self.remote_name}:"
        if remote_folder:
            dest += remote_folder + "/"
        dest += Path(local_path).name

        result = self._run_rclone(
            ["copy", local_path, dest, "--progress"],
            timeout=300
        )
        if not result["ok"]:
            return result

        return {
            "ok": True,
            "local": local_path,
            "remote": remote_folder or "/",
            "filename": Path(local_path).name,
        }


GDRIVE_TOOLS = [
    {
        "name": "gdrive_search_media",
        "description": "Search for video/image/audio files in Google Drive by name",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query for filename"},
                "folder": {"type": "string", "description": "Subfolder to search in", "default": ""},
                "media_type": {"type": "string", "enum": ["all", "video", "image", "audio"], "default": "all"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["query"],
        },
    },
    {
        "name": "gdrive_browse_folder",
        "description": "Browse folder structure in Google Drive",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to browse", "default": ""},
            },
        },
    },
    {
        "name": "gdrive_download_media",
        "description": "Download a media file from Google Drive to local disk",
        "parameters": {
            "type": "object",
            "properties": {
                "remote_path": {"type": "string", "description": "Path on Google Drive"},
                "local_dir": {"type": "string", "description": "Local directory to save to", "default": ""},
            },
            "required": ["remote_path"],
        },
    },
    {
        "name": "gdrive_get_storage_info",
        "description": "Get Google Drive storage usage info",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "gdrive_upload_media",
        "description": "Upload a local media file to Google Drive",
        "parameters": {
            "type": "object",
            "properties": {
                "local_path": {"type": "string", "description": "Local file path"},
                "remote_folder": {"type": "string", "description": "GDrive folder", "default": ""},
            },
            "required": ["local_path"],
        },
    },
]
