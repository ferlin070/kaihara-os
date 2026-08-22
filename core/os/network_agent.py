"""
Network Agent - monitor traffic, check connections, firewall rules.
"""

import subprocess
import socket
from datetime import datetime

from core.os.base_os_agent import BaseOSAgent


class NetworkAgent(BaseOSAgent):
    """Monitor network: connections, traffic, firewall."""

    AGENT_TYPE = "os_network"
    INTERVAL = 180  # 3 minutes

    def __init__(self, config=None, audit=None):
        super().__init__(config, audit)
        self.monitored_ports = config.get(
            "monitored_ports", [7000, 11434]
        )

    async def run_task(self) -> dict:
        connections = self._get_connections()
        ports_status = self._check_ports()
        bandwidth = self._get_bandwidth()
        alerts = []
        for port_info in ports_status:
            if not port_info["listening"]:
                alerts.append({
                    "action": "port_not_listening",
                    "severity": "warning",
                    "port": port_info["port"],
                })
        return {
            "agent": self.AGENT_TYPE,
            "connections": connections,
            "ports": ports_status,
            "bandwidth": bandwidth,
            "alerts": alerts,
        }

    def _get_connections(self) -> dict:
        """Get active network connections."""
        try:
            import psutil
            conns = psutil.net_connections(kind="inet")
            established = sum(
                1 for c in conns if c.status == "ESTABLISHED"
            )
            return {
                "total": len(conns),
                "established": established,
            }
        except Exception:
            return {"error": "could not get connections"}

    def _check_ports(self) -> list[dict]:
        """Check if monitored ports are listening."""
        results = []
        for port in self.monitored_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(("127.0.0.1", port))
                sock.close()
                results.append({
                    "port": port,
                    "listening": result == 0,
                })
            except Exception:
                results.append({
                    "port": port,
                    "listening": False,
                })
        return results

    def _get_bandwidth(self) -> dict:
        """Get network bandwidth stats."""
        try:
            import psutil
            net = psutil.net_io_counters()
            return {
                "bytes_sent_mb": round(net.bytes_sent / 1e6, 2),
                "bytes_recv_mb": round(net.bytes_recv / 1e6, 2),
                "packets_sent": net.packets_sent,
                "packets_recv": net.packets_recv,
            }
        except Exception:
            return {"error": "could not get bandwidth"}

    def status(self) -> dict:
        return {**super().status(),
                "monitored_ports": self.monitored_ports,
                "last_result": self._last_result}
