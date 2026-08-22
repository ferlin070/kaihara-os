"""
Google Drive Integration — backup, file access, Obsidian sync, report upload.

4 functions:
  1. Backup: auto backup Kaihara data (SQLite, config, vault) to GDrive
  2. File access: read/write files on GDrive (storage agent)
  3. Obsidian sync: sync vault between local and GDrive
  4. Report upload: upload pentest/analysis reports to GDrive

Uses rclone for simplicity (no Google API SDK needed).
Alternative: use google-api-python-client for direct API access.

Setup:
  1. Install rclone: curl https://rclone.org/install.sh | bash
  2. Configure: rclone config → create "gdrive" remote
  3. Or connect to existing CT 101 (storage01) rclone instance
"""

import subprocess
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any


class GoogleDrive:
    """Google Drive integration via rclone."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.remote_name = self.config.get("remote_name", "gdrive")
        self.backup_folder = self.config.get("backup_folder", "kaihara-backup")
        self.vault_folder = self.config.get("vault_folder", "kaihara-vault")
        self.report_folder = self.config.get("report_folder", "kaihara-reports")
        self._rclone_path = self._find_rclone()
        self._connected = False

    def _find_rclone(self) -> str | None:
        """Find rclone binary."""
        try:
            result = subprocess.run(
                ["which", "rclone"], capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def is_available(self) -> bool:
        """Check if rclone is installed and configured."""
        if not self._rclone_path:
            return False
        try:
            result = subprocess.run(
                [self._rclone_path, "listremotes"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                remotes = result.stdout.strip().split("\n")
                self._connected = any(
                    r.strip(":") == self.remote_name for r in remotes
                )
                return self._connected
        except Exception:
            pass
        return False

    # ============================================================
    # 1. BACKUP — auto backup Kaihara data to GDrive
    # ============================================================

    def backup(self, source_dir: str,
               subfolder: str = "") -> dict:
        """Backup a directory to Google Drive."""
        if not self.is_available():
            return {"error": "rclone not available or not configured"}
        dest = f"{self.remote_name}:{self.backup_folder}"
        if subfolder:
            dest += f"/{subfolder}"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            result = subprocess.run(
                [self._rclone_path, "sync", source_dir, dest,
                 "--transfers", "4", "--checkers", "8",
                 "--stats", "1s", "--log-level", "INFO"],
                capture_output=True, text=True, timeout=3600
            )
            return {
                "success": result.returncode == 0,
                "source": source_dir,
                "destination": dest,
                "timestamp": timestamp,
                "output": result.stderr[-500:] if result.stderr else "",
            }
        except subprocess.TimeoutExpired:
            return {"error": "Backup timed out (1hr limit)"}
        except Exception as e:
            return {"error": str(e)}

    def backup_database(self, db_path: str) -> dict:
        """Backup SQLite database to GDrive."""
        return self.backup(
            os.path.dirname(db_path) or ".",
            subfolder=f"database/{datetime.now().strftime('%Y-%m-%d')}"
        )

    def backup_config(self, config_dir: str) -> dict:
        """Backup config directory to GDrive."""
        return self.backup(config_dir, subfolder="config")

    def backup_all(self, data_dir: str, config_dir: str,
                    vault_dir: str) -> dict:
        """Full backup: database + config + vault."""
        results = {}
        results["database"] = self.backup(
            data_dir, subfolder=f"database/{datetime.now().strftime('%Y-%m-%d')}"
        )
        results["config"] = self.backup(config_dir, subfolder="config")
        results["vault"] = self.backup(vault_dir, subfolder="vault")
        all_ok = all(r.get("success") for r in results.values())
        return {
            "success": all_ok,
            "results": results,
            "timestamp": datetime.now().isoformat(),
        }

    # ============================================================
    # 2. FILE ACCESS — read/write files on GDrive
    # ============================================================

    def list_files(self, path: str = "") -> dict:
        """List files on Google Drive."""
        if not self.is_available():
            return {"error": "rclone not available"}
        remote_path = f"{self.remote_name}:{self.backup_folder}"
        if path:
            remote_path += f"/{path}"
        try:
            result = subprocess.run(
                [self._rclone_path, "lsjson", remote_path],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                files = json.loads(result.stdout)
                return {"files": files, "path": remote_path}
            return {"error": result.stderr}
        except Exception as e:
            return {"error": str(e)}

    def upload_file(self, local_path: str,
                     remote_path: str = "") -> dict:
        """Upload a file to Google Drive."""
        if not self.is_available():
            return {"error": "rclone not available"}
        dest = f"{self.remote_name}:{self.report_folder}"
        if remote_path:
            dest += f"/{remote_path}"
        try:
            result = subprocess.run(
                [self._rclone_path, "copy", local_path, dest,
                 "--progress"],
                capture_output=True, text=True, timeout=600
            )
            return {
                "success": result.returncode == 0,
                "local": local_path,
                "remote": dest,
            }
        except Exception as e:
            return {"error": str(e)}

    def download_file(self, remote_path: str,
                       local_path: str) -> dict:
        """Download a file from Google Drive."""
        if not self.is_available():
            return {"error": "rclone not available"}
        src = f"{self.remote_name}:{remote_path}"
        try:
            result = subprocess.run(
                [self._rclone_path, "copy", src, local_path],
                capture_output=True, text=True, timeout=600
            )
            return {
                "success": result.returncode == 0,
                "remote": src,
                "local": local_path,
            }
        except Exception as e:
            return {"error": str(e)}

    def read_file(self, remote_path: str) -> dict:
        """Read a text file from Google Drive."""
        if not self.is_available():
            return {"error": "rclone not available"}
        src = f"{self.remote_name}:{remote_path}"
        try:
            result = subprocess.run(
                [self._rclone_path, "cat", src],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return {"content": result.stdout, "path": remote_path}
            return {"error": result.stderr}
        except Exception as e:
            return {"error": str(e)}

    # ============================================================
    # 3. OBSIDIAN VAULT SYNC — sync between local and GDrive
    # ============================================================

    def sync_vault(self, local_vault_dir: str,
                    direction: str = "bidirectional") -> dict:
        """Sync Obsidian vault with Google Drive."""
        if not self.is_available():
            return {"error": "rclone not available"}
        remote_vault = f"{self.remote_name}:{self.vault_folder}"
        try:
            if direction == "bidirectional":
                result = subprocess.run(
                    [self._rclone_path, "bisync", local_vault_dir,
                     remote_vault, "--resilient", "--log-level", "INFO"],
                    capture_output=True, text=True, timeout=600
                )
            elif direction == "upload":
                result = subprocess.run(
                    [self._rclone_path, "sync", local_vault_dir,
                     remote_vault, "--transfers", "4"],
                    capture_output=True, text=True, timeout=600
                )
            elif direction == "download":
                result = subprocess.run(
                    [self._rclone_path, "sync", remote_vault,
                     local_vault_dir, "--transfers", "4"],
                    capture_output=True, text=True, timeout=600
                )
            else:
                return {"error": f"Unknown direction: {direction}"}
            return {
                "success": result.returncode == 0,
                "direction": direction,
                "local": local_vault_dir,
                "remote": remote_vault,
                "output": result.stderr[-300:] if result.stderr else "",
            }
        except Exception as e:
            return {"error": str(e)}

    # ============================================================
    # 4. REPORT UPLOAD — upload reports to GDrive
    # ============================================================

    def upload_report(self, local_path: str,
                       report_name: str = "") -> dict:
        """Upload a report (pentest, analysis, etc.) to GDrive."""
        if not report_name:
            report_name = os.path.basename(local_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        remote_path = f"{timestamp}_{report_name}"
        return self.upload_file(local_path, remote_path)

    def list_reports(self) -> dict:
        """List all reports on GDrive."""
        return self.list_files("")

    # ============================================================
    # STATUS
    # ============================================================

    def status(self) -> dict:
        return {
            "available": self.is_available(),
            "rclone_path": self._rclone_path,
            "remote_name": self.remote_name,
            "folders": {
                "backup": self.backup_folder,
                "vault": self.vault_folder,
                "reports": self.report_folder,
            },
        }

    def setup_instructions(self) -> str:
        """Return setup instructions."""
        return """
Google Drive Setup (rclone):

1. Install rclone:
   curl https://rclone.org/install.sh | bash

2. Configure Google Drive remote:
   rclone config
   → n (new remote)
   → Name: gdrive
   → Storage: drive (Google Drive)
   → Client ID: (leave blank, press Enter)
   → Client Secret: (leave blank, press Enter)
   → Scope: 1 (full access)
   → Root folder: (leave blank)
   → Service account: (leave blank)
   → Open browser for auth: Y
   → (login with Google account)
   → Configure as Shared Drive: n
   → q (quit)

3. Test:
   rclone ls gdrive:

4. Or connect to CT 101 (storage01 .22):
   If rclone already configured on CT 101:
   ssh root@192.168.1.22
   rclone config show
   → Copy config to CT 203
"""
