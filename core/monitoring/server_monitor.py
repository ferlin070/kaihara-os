"""
Server Monitor — pantau semua server: up/down, latency, internet.
Servers: Proxmox hosts, GPU/RTX servers, CTs, desktops (LAN + Tailscale).
"""

import asyncio
import time
from typing import Any

# Server registry: name -> {lan, ts (tailscale ip), type, note}
SERVERS: list[dict] = [
    {"name": "cloudhosting",     "role": "Proxmox Host",   "lan": "192.168.1.99",  "ts": None,              "ports": [8006, 22]},
    {"name": "dfkserver1",       "role": "Proxmox Host",   "lan": None,            "ts": "100.115.128.43",  "ports": [8006, 22]},
    {"name": "gpu-tesla-t4",     "role": "GPU Server",     "lan": None,            "ts": "100.92.235.77",   "ports": [22]},
    {"name": "rtx-5060ti",       "role": "GPU Server",     "lan": None,            "ts": "100.74.222.77",   "ports": [22]},
    {"name": "docker-server",    "role": "Docker Node",    "lan": None,            "ts": "100.70.85.121",   "ports": [22]},
    {"name": "desktop-pc",       "role": "Workstation",    "lan": None,            "ts": "100.121.124.18",  "ports": []},
    # Kaihara CTs
    {"name": "kaihara-core",      "role": "CT 203", "lan": "192.168.1.211", "ts": None, "ports": [7000]},
    {"name": "kaihara-dashboard", "role": "CT 204", "lan": "192.168.1.212", "ts": None, "ports": [80]},
    {"name": "kaihara-channels",  "role": "CT 205", "lan": "192.168.1.213", "ts": None, "ports": []},
    {"name": "kaihara-security",  "role": "CT 206", "lan": "192.168.1.214", "ts": None, "ports": []},
    {"name": "kaihara-kernel",    "role": "CT 207", "lan": "192.168.1.215", "ts": None, "ports": []},
    # CT dikekal
    {"name": "test10",          "role": "CT 100 Web",     "lan": "192.168.1.21",  "ts": None, "ports": [80, 22]},
    {"name": "storage01",       "role": "CT 101 Storage", "lan": "192.168.1.22",  "ts": None, "ports": [22]},
    {"name": "obsidian-vault",  "role": "CT 104 Vault",   "lan": "192.168.1.141", "ts": None, "ports": []},
    {"name": "9router",         "role": "CT 107 AI Proxy","lan": "192.168.1.41",  "ts": None, "ports": [20128]},
    {"name": "ai-stack",        "role": "CT 201 Ollama",  "lan": "192.168.1.248", "ts": None, "ports": [11434]},
    {"name": "mara-ai-server",  "role": "CT 300",         "lan": "192.168.1.30",  "ts": None, "ports": []},
]

INTERNET_CHECKS = ["1.1.1.1", "8.8.8.8"]


async def _ping(ip: str, timeout_s: float = 2.0) -> dict:
    """ICMP ping. Returns {'up': bool, 'latency_ms': float|None}."""
    if not ip:
        return {"up": False, "latency_ms": None}
    t0 = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "1", "-W", str(int(timeout_s)), ip,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        code = await asyncio.wait_for(proc.wait(), timeout=timeout_s + 1)
        latency = round((time.monotonic() - t0) * 1000, 1)
        return {"up": code == 0, "latency_ms": latency if code == 0 else None}
    except Exception:
        return {"up": False, "latency_ms": None}


async def _tcp_check(ip: str, port: int, timeout_s: float = 2.0) -> bool:
    """TCP connect check for a service port."""
    if not ip or not port:
        return False
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port), timeout=timeout_s)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception:
        return False


async def check_internet() -> dict:
    """Check our own internet connectivity (DNS + ICMP to public IPs)."""
    results = {}
    overall = False
    for target in INTERNET_CHECKS:
        r = await _ping(target, 2.0)
        results[target] = r["up"]
        if r["up"]:
            overall = True
    # DNS test
    dns_ok = False
    try:
        import socket
        loop = asyncio.get_event_loop()
        await asyncio.wait_for(loop.getaddrinfo("rootsys.cloud", 443), timeout=5)
        dns_ok = True
        overall = True
    except Exception:
        pass
    return {
        "internet_up": overall,
        "icmp": results,
        "dns_ok": dns_ok,
    }


async def check_all_servers() -> dict:
    """Ping all servers concurrently + TCP service checks."""
    async def one(s: dict) -> dict:
        lan_r = await _ping(s["lan"]) if s["lan"] else {"up": False, "latency_ms": None}
        ts_r = await _ping(s["ts"]) if s["ts"] else {"up": False, "latency_ms": None}
        up = lan_r["up"] or ts_r["up"]
        latency = next((r["latency_ms"] for r in (lan_r, ts_r) if r["up"]), None)
        via = "lan" if lan_r["up"] else ("tailscale" if ts_r["up"] else None)

        services = {}
        if up and s.get("ports"):
            checks = await asyncio.gather(*[
                _tcp_check(s["lan"] or s["ts"], p) for p in s["ports"]])
            services = dict(zip(s["ports"], checks))

        return {
            "name": s["name"],
            "role": s["role"],
            "ip": s["lan"] or s["ts"],
            "via": via,
            "status": "UP" if up else "DOWN",
            "latency_ms": latency,
            "services": services,
        }

    results = await asyncio.gather(*[one(s) for s in SERVERS])
    up_count = sum(1 for r in results if r["status"] == "UP")
    return {
        "servers": results,
        "summary": {"total": len(results), "up": up_count,
                    "down": len(results) - up_count},
    }


# ------------------------------------------------------------------
# Host agent integration (cloudhosting :7100)
# ------------------------------------------------------------------

HOST_AGENT = "http://192.168.1.99:7100"

# Cache: ping sweep is expensive (~2-15s). Serve cached instantly,
# refresh in background when stale (stale-while-revalidate).
_cache: dict | None = None
_cache_ts: float = 0.0
_CACHE_TTL = 45  # seconds
_refreshing = False


async def fetch_host_data() -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{HOST_AGENT}/all")
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return None


async def check_all() -> dict:
    """Full monitoring with 45s cache. Returns cached instantly,
    refreshes in background when stale."""
    global _cache, _cache_ts, _refreshing
    now = time.time()
    if _cache is not None and (now - _cache_ts) < _CACHE_TTL:
        data = dict(_cache)
        data["cached"] = True
        data["age_s"] = round(now - _cache_ts, 1)
        return data
    if _cache is not None and not _refreshing:
        # stale-while-revalidate: serve old, refresh bg
        _refreshing = True
        asyncio.create_task(_refresh_bg())
        data = dict(_cache)
        data["cached"] = True
        data["stale"] = True
        return data
    return await _do_check()


async def _refresh_bg():
    global _cache, _cache_ts, _refreshing
    try:
        await _do_check()
    finally:
        _refreshing = False


async def _do_check() -> dict:
    global _cache, _cache_ts
    host_task = asyncio.create_task(fetch_host_data())
    servers = await check_all_servers()

    # Merge tailscale status for TS-only devices
    host = await host_task
    ts_map = {}
    if host:
        for p in host.get("tailscale", []):
            ts_map[p.get("hostname", "").lower()] = p

    for s in servers["servers"]:
        key = s["name"].lower()
        # fuzzy match to tailscale hostname
        match = None
        for hn, p in ts_map.items():
            if key in hn or hn in key or \
               (key.startswith("dfk") and "dfk" in hn) or \
               ("gpu" in key and "gpu" in hn) or \
               ("rtx" in key and "rtx" in hn) or \
               ("docker" in key and "docker" in hn and "server" in key) or \
               ("desktop" in key and "desktop" in hn):
                match = p
                break
        if match:
            s["tailscale_online"] = bool(match.get("online"))
            # TS-only device: presence in tailnet = it's online
            if not s["latency_ms"] and s["tailscale_online"]:
                s["status"] = "UP"
                s["via"] = "tailscale"
        else:
            s["tailscale_online"] = None

    internet = None
    host_system = None
    guests = None
    if host:
        internet = host.get("internet")
        host_system = host.get("system")
        guests = host.get("guests")

    up_count = sum(1 for r in servers["servers"] if r["status"] == "UP")
    _cache = {
        "servers": servers["servers"],
        "summary": {"total": len(servers["servers"]), "up": up_count,
                    "down": len(servers["servers"]) - up_count},
        "internet": internet,
        "host_system": host_system,
        "proxmox_guests": guests,
        "timestamp": time.time(),
    }
    _cache_ts = time.time()
    return dict(_cache)
import httpx
