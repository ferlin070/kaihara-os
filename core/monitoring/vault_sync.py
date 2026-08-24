"""
Vault Reverse Sync — watch Obsidian vault for edits, ingest into memory.
Edit nota dalam vault → auto masuk Memory Tree (two-way sync).
"""

import asyncio
import json
import os
import time
from pathlib import Path

STATE_FILE = "data/.vault_sync_state.json"
POLL_INTERVAL = 60  # seconds


def _load_state(data_dir: str) -> dict:
    p = os.path.join(data_dir, STATE_FILE)
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(data_dir: str, state: dict):
    p = os.path.join(data_dir, STATE_FILE)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as f:
        json.dump(state, f)


def _scan_vault(vault_path: str) -> dict[str, float]:
    """Return {relative_path: mtime} for all .md files."""
    result = {}
    vault = Path(vault_path)
    if not vault.exists():
        return result
    for root, _dirs, files in os.walk(vault):
        # Skip PRD/generated folders — those are outputs
        rel_root = os.path.relpath(root, vault)
        if rel_root.startswith("prd") or rel_root.startswith("."):
            continue
        for f in files:
            if f.endswith(".md"):
                fp = os.path.join(root, f)
                try:
                    rel = os.path.relpath(fp, vault)
                    result[rel] = os.path.getmtime(fp)
                except OSError:
                    pass
    return result


async def watch_vault(memory, vault_path: str, data_dir: str = "data"):
    """Polling watcher: ingest new/changed .md files into memory tree."""
    state = _load_state(data_dir)
    print(f"[vault_sync] watching {vault_path}", flush=True)

    while True:
        try:
            current = await asyncio.to_thread(_scan_vault, vault_path)
            new_or_changed = []
            for rel, mtime in current.items():
                prev = state.get(rel, 0)
                if mtime > prev:
                    new_or_changed.append((rel, mtime))

            for rel, mtime in sorted(new_or_changed)[:20]:  # cap per cycle
                fp = os.path.join(vault_path, rel)
                try:
                    content = await asyncio.to_thread(
                        lambda p=fp: Path(p).read_text(encoding="utf-8"))
                    if len(content.strip()) < 10:
                        continue
                    topic = "daily" if rel.startswith("memory/daily") else (
                        "core" if rel.startswith("memory/core") else
                        rel.split("/")[0])
                    memory.store(
                        f"[Obsidian edit: {rel}]\n{content[:3000]}",
                        source="vault",
                        agent="obsidian-sync",
                    )
                    state[rel] = mtime
                    print(f"[vault_sync] ingested {rel}", flush=True)
                except Exception as e:
                    print(f"[vault_sync] error {rel}: {e}", flush=True)

            if new_or_changed:
                _save_state(data_dir, state)
        except Exception as e:
            print(f"[vault_sync] cycle error: {e}", flush=True)

        await asyncio.sleep(POLL_INTERVAL)


from pathlib import Path  # noqa: E402
