"""
System Tools — comprehensive system metrics via psutil.
CPU, RAM, disk, network, processes — all in one module.
Cross-platform (Windows + Linux).
"""

import os
import time
import psutil
import platform
from datetime import datetime


def get_system_stats() -> dict:
    """Get comprehensive system stats in one call."""
    # CPU
    cpu = psutil.cpu_percent(interval=0.5, percpu=True)
    cpu_avg = sum(cpu) / len(cpu) if cpu else 0
    try:
        load = list(os.getloadavg())
    except (AttributeError, OSError):
        load = [cpu_avg / 100 * psutil.cpu_count(), 0, 0]

    # Memory
    ram = psutil.virtual_memory()
    swap = psutil.swap_memory()

    # Disk
    disk = psutil.disk_usage("/")
    try:
        disk_io = psutil.disk_io_counters()
        io_stats = {
            "read_mb": round(disk_io.read_bytes / (1024**2), 1),
            "write_mb": round(disk_io.write_bytes / (1024**2), 1),
            "read_count": disk_io.read_count,
            "write_count": disk_io.write_count,
        } if disk_io else None
    except Exception:
        io_stats = None

    # Network
    net = psutil.net_io_counters()
    try:
        per_nic = psutil.net_io_counters(pernic=True)
        nic_list = []
        for name, counters in per_nic.items():
            if counters.bytes_sent > 0 or counters.bytes_recv > 0:
                nic_list.append({
                    "name": name,
                    "sent_mb": round(counters.bytes_sent / (1024**2), 1),
                    "recv_mb": round(counters.bytes_recv / (1024**2), 1),
                    "packets_sent": counters.packets_sent,
                    "packets_recv": counters.packets_recv,
                    "errin": counters.errin,
                    "errout": counters.errout,
                    "dropin": counters.dropin,
                    "dropout": counters.dropout,
                })
    except Exception:
        nic_list = []

    # Network interface status
    try:
        if_addrs = psutil.net_if_stats()
        nic_status = []
        for name, stats in if_addrs.items():
            nic_status.append({
                "name": name,
                "is_up": stats.isup,
                "speed_mbps": stats.speed,
                "mtu": stats.mtu,
            })
    except Exception:
        nic_status = []

    # Connections
    try:
        conns = psutil.net_connections(kind="inet")
        established = sum(1 for c in conns if c.status == "ESTABLISHED")
    except Exception:
        conns = []
        established = 0

    # Processes
    procs = psutil.pids()
    top_cpu = []
    top_ram = []
    try:
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = p.info
                if info["cpu_percent"] and info["cpu_percent"] > 0:
                    top_cpu.append({
                        "pid": info["pid"],
                        "name": info["name"][:30],
                        "cpu": round(info["cpu_percent"], 1),
                    })
                if info["memory_percent"] and info["memory_percent"] > 0:
                    top_ram.append({
                        "pid": info["pid"],
                        "name": info["name"][:30],
                        "ram_pct": round(info["memory_percent"], 1),
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        top_cpu.sort(key=lambda x: x["cpu"], reverse=True)
        top_ram.sort(key=lambda x: x["ram_pct"], reverse=True)
    except Exception:
        pass

    # Uptime
    try:
        boot = psutil.boot_time()
        uptime_sec = time.time() - boot
    except Exception:
        uptime_sec = 0

    # System info
    try:
        temps = psutil.sensors_temperatures()
        temp = None
        for entries in temps.values():
            if entries:
                temp = entries[0].current
                break
    except Exception:
        temp = None

    return {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "platform": platform.system(),
            "hostname": platform.node(),
            "python": platform.python_version(),
            "uptime_seconds": int(uptime_sec),
        },
        "cpu": {
            "percent": round(cpu_avg, 1),
            "per_core": [round(c, 1) for c in cpu],
            "count_logical": psutil.cpu_count(),
            "count_physical": psutil.cpu_count(logical=False),
            "load_1m": round(load[0], 2),
            "load_5m": round(load[1], 2),
            "load_15m": round(load[2], 2),
            "freq_mhz": round(psutil.cpu_freq().current, 0) if psutil.cpu_freq() else None,
        },
        "memory": {
            "ram_total_gb": round(ram.total / (1024**3), 1),
            "ram_used_gb": round(ram.used / (1024**3), 1),
            "ram_available_gb": round(ram.available / (1024**3), 1),
            "ram_percent": ram.percent,
            "swap_total_gb": round(swap.total / (1024**3), 1),
            "swap_used_gb": round(swap.used / (1024**3), 1),
            "swap_percent": swap.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024**3), 1),
            "used_gb": round(disk.used / (1024**3), 1),
            "free_gb": round(disk.free / (1024**3), 1),
            "percent": disk.percent,
            "io": io_stats,
        },
        "network": {
            "total_sent_mb": round(net.bytes_sent / (1024**2), 1),
            "total_recv_mb": round(net.bytes_recv / (1024**2), 1),
            "total_packets_sent": net.packets_sent,
            "total_packets_recv": net.packets_recv,
            "errin": net.errin,
            "errout": net.errout,
            "dropin": net.dropin,
            "dropout": net.dropout,
            "connections": len(conns),
            "established": established,
            "interfaces": nic_list,
            "interface_status": nic_status,
        },
        "processes": {
            "total": len(procs),
            "top_cpu": top_cpu[:5],
            "top_ram": top_ram[:5],
        },
        "temperature": temp,
    }


def get_network_speed() -> dict:
    """Measure network speed using a quick download test."""
    import httpx
    test_urls = [
        ("http://speedtest.tele2.net/10MB.zip", 10),
        ("http://speedtest.tele2.net/1MB.zip", 1),
    ]
    for url, size_mb in test_urls:
        try:
            start = time.time()
            with httpx.Client(timeout=15) as client:
                resp = client.get(url)
                elapsed = time.time() - start
                if elapsed > 0:
                    speed_mbps = (len(resp.content) / (1024**2)) / elapsed
                    return {
                        "download_mbps": round(speed_mbps, 2),
                        "test_size_mb": size_mb,
                        "elapsed_sec": round(elapsed, 2),
                        "method": "http_download",
                    }
        except Exception:
            continue
    return {"download_mbps": 0, "error": "Speed test failed"}


def get_bandwidth_rate() -> dict:
    """Get current bandwidth rate (bytes/sec) by sampling over 1 second."""
    net1 = psutil.net_io_counters()
    time.sleep(1)
    net2 = psutil.net_io_counters()

    return {
        "bytes_sent_per_sec": net2.bytes_sent - net1.bytes_sent,
        "bytes_recv_per_sec": net2.bytes_recv - net1.bytes_recv,
        "packets_sent_per_sec": net2.packets_sent - net1.packets_sent,
        "packets_recv_per_sec": net2.packets_recv - net1.packets_recv,
        "mbps_sent": round((net2.bytes_sent - net1.bytes_sent) * 8 / (1024**2), 2),
        "mbps_recv": round((net2.bytes_recv - net1.bytes_recv) * 8 / (1024**2), 2),
    }


def get_disk_partitions() -> list[dict]:
    """Get all disk partitions and their usage."""
    partitions = []
    for p in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(p.mountpoint)
            partitions.append({
                "device": p.device,
                "mountpoint": p.mountpoint,
                "fstype": p.fstype,
                "total_gb": round(usage.total / (1024**3), 1),
                "used_gb": round(usage.used / (1024**3), 1),
                "free_gb": round(usage.free / (1024**3), 1),
                "percent": usage.percent,
            })
        except (PermissionError, OSError):
            continue
    return partitions


def ping_host(host: str = "8.8.8.8", count: int = 4) -> dict:
    """Ping a host and return latency stats."""
    import subprocess
    try:
        param = "-n" if platform.system().lower() == "windows" else "-c"
        result = subprocess.run(
            ["ping", param, str(count), host],
            capture_output=True, text=True, timeout=15
        )
        output = result.stdout
        # Parse average latency
        import re
        if platform.system().lower() == "windows":
            match = re.search(r"Average = (\d+)ms", output)
        else:
            match = re.search(r"avg = [\d.]+/([\d.]+)/", output)
        avg_ms = float(match.group(1)) if match else None
        return {
            "host": host,
            "avg_latency_ms": avg_ms,
            "packets_sent": count,
            "success": avg_ms is not None,
        }
    except Exception as e:
        return {"host": host, "error": str(e), "success": False}
