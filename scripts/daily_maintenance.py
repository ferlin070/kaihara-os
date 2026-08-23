"""
Daily maintenance for Kaihara OS:
1. Deep Dream — memory distillation (3AM)
2. Database backup
3. Vault backup
4. Log cleanup
Run via cron: 0 3 * * *
"""

import sys
import sqlite3
import subprocess
import tarfile
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

DATA_DIR = ROOT / "data"
VAULT_DIR = ROOT / "obsidian-vault"
BACKUP_DIR = DATA_DIR / "backups"
BACKUP_DIR.mkdir(exist_ok=True)

def deep_dream():
    """Distill daily memories into long-term core memory."""
    try:
        from core.brain.memory_tree import MemoryTree
        mt = MemoryTree(
            db_path=str(DATA_DIR / "kaihara.db"),
            vault_path=str(VAULT_DIR),
            config={},
        )
        result = mt.deep_dream()
        print(f"[deep_dream] {result}")
    except Exception as e:
        print(f"[deep_dream] ERROR: {e}")

def backup_database():
    """Backup SQLite database."""
    try:
        db = DATA_DIR / "kaihara.db"
        if not db.exists():
            print("[backup_db] No database found")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = BACKUP_DIR / f"kaihara_db_{ts}.tar.gz"
        with tarfile.open(dest, "w:gz") as tar:
            tar.add(db, arcname="kaihara.db")
        print(f"[backup_db] Saved: {dest.name} ({dest.stat().st_size // 1024}KB)")
    except Exception as e:
        print(f"[backup_db] ERROR: {e}")

def backup_vault():
    """Backup Obsidian vault."""
    try:
        if not VAULT_DIR.exists():
            print("[backup_vault] No vault found")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = BACKUP_DIR / f"vault_{ts}.tar.gz"
        with tarfile.open(dest, "w:gz") as tar:
            tar.add(VAULT_DIR, arcname="obsidian-vault")
        print(f"[backup_vault] Saved: {dest.name} ({dest.stat().st_size // 1024}KB)")
    except Exception as e:
        print(f"[backup_vault] ERROR: {e}")

def cleanup_old_backups(keep_days: int = 7):
    """Remove backups older than keep_days."""
    try:
        cutoff = datetime.now().timestamp() - (keep_days * 86400)
        removed = 0
        for f in BACKUP_DIR.glob("*.tar.gz"):
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        print(f"[cleanup] Removed {removed} old backups")
    except Exception as e:
        print(f"[cleanup] ERROR: {e}")

if __name__ == "__main__":
    print(f"=== Kaihara Daily Maintenance — {datetime.now()} ===")
    deep_dream()
    backup_database()
    backup_vault()
    cleanup_old_backups()
    print("=== Done ===")
