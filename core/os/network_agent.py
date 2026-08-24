"""
Network Agent — monitor network: connections, ports, bandwidth rate, packet errors.
Upgraded: bandwidth rate, per-interface, packet errors, interface status.
"""

import time
import socket
import psutil
from core.os.base_os_agent import BaseOSAgent


class NetworkAgent(BaseOSAgent):
    """Monitor network activity."""

    AGENT_TYPE = "network"
    INTERVAL = 180  # Every 3 minutes

    def __init__(self, config=None, audit=None):
        super().__init__(config, audit)
        self._prev_net = None
        self._prev_time = None
        self._monitored_ports = (self.config or {}).get("ports", [7000, 11434])

    async def run_task(self) -> dict:
        # Connections
        try:
            conns = psutil.net_connections(kind="inet")
            established = sum(1 for c in conns if c.status == "ESTABLISHED")
            listening = sum(1 for c in conns if c.status == "LISTEN")
        except Exception:
            conns = []
            established = 0
            listening = 0

        # Port checks
        port_status = {}
        for port in self._monitored_ports:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=2):
                    port_status[str(port)] = "open"
            except Exception:
                port_status[str(port)] = "closed"

        # Bandwidth rate
        now = time.time()
        current_net = psutil.net_io_counters()
        rate = None
        if self._prev_net and self._prev_time:
            dt = now - self._prev_time
            if dt > 0:
                rate = {
                    "bytes_sent_per_sec": round(
                        (current_net.bytes_sent - self._prev_net.bytes_sent) / dt
                    ),
                    "bytes_recv_per_sec": round(
                        (current_net.bytes_recv - self._prev_net.bytes_recv) / dt
                    ),
                    "packets_sent_per_sec": round(
                        (current_net.packets_sent - self._prev_net.packets_sent) / dt
                    ),
                    "packets_recv_per_sec": round(
                        (current_net.packets_recv - self._prev_net.packets_recv) / dt
                    ),
                    "mbps_sent": round(
                        (current_net.bytes_sent - self._prev_net.bytes_sent) * 8 / dt / (1024**2), 2
                    ),
                    "mbps_recv": round(
                        (current_net.bytes_recv - self._prev_net.bytes_recv) * 8 / dt / (1024**2), 2
                    ),
                }
        self._prev_net = current_net
        self._prev_time = now

        # Per-interface
        interfaces = []
        try:
            per_nic = psutil.net_io_counters(pernic=True)
            for name, counters in per_nic.items():
                if counters.bytes_sent > 0 or counters.bytes_recv > 0:
                    interfaces.append({
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
            pass

        # Interface status
        if_status = []
        try:
            stats = psutil.net_if_stats()
            for name, s in stats.items():
                if_status.append({
                    "name": name,
                    "is_up": s.isup,
                    "speed_mbps": s.speed,
                    "mtu": s.mtu,
                })
        except Exception:
            pass

        # Alerts
        alerts = []
        for port, status in port_status.items():
            if status == "closed":
                alerts.append({
                    "action": "port_down",
                    "severity": "warning",
                    "message": f"Port {port} not listening",
                })
        if current_net.errin > 0 or current_net.errout > 0:
            alerts.append({
                "action": "packet_errors",
                "severity": "warning",
                "message": f"Packet errors: in={current_net.errin} out={current_net.errout}",
            })

        return {
            "connections": len(conns),
            "established": established,
            "listening": listening,
            "port_status": port_status,
            "total": {
                "sent_mb": round(current_net.bytes_sent / (1024**2), 1),
                "recv_mb": round(current_net.bytes_recv / (1024**2), 1),
                "packets_sent": current_net.packets_sent,
                "packets_recv": current_net.packets_recv,
                "errin": current_net.errin,
                "errout": current_net.errout,
                "dropin": current_net.dropin,
                "dropout": current_net.dropout,
            },
            "rate": rate,
            "interfaces": interfaces,
            "interface_status": if_status,
            "alerts": alerts,
        }
