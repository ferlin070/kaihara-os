"""
Sandbox - Docker-based isolated execution for agent commands.
Inspired by NemoClaw (#56 NVIDIA) sandboxed execution pattern.
"""

import subprocess
import json
import os
from typing import Any


class Sandbox:
    """Docker-based sandbox for executing untrusted code/commands."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.enabled = self.config.get("sandbox_enabled", True)
        self.default_image = self.config.get("sandbox_image", "python:3.12-slim")
        self.timeout = self.config.get("sandbox_timeout", 120)
        self.network = self.config.get("sandbox_network", "none")
        self.memory_limit = self.config.get("sandbox_memory", "512m")
        self.cpu_limit = self.config.get("sandbox_cpu", "0.5")

    def is_available(self) -> bool:
        """Check if Docker is available."""
        if not self.enabled:
            return False
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True, timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, Exception):
            return False

    async def execute(self, command: list[str] | str,
                      image: str = None,
                      workdir: str = "/sandbox",
                      env: dict | None = None,
                      volumes: dict | None = None) -> dict:
        """Execute command in Docker sandbox."""
        if not self.enabled:
            return await self._execute_direct(command, workdir, env)

        if not self.is_available():
            # No Docker on this host — run directly (tools installed natively)
            return await self._execute_direct(command, workdir, env)

        image = image or self.default_image
        docker_cmd = self._build_docker_command(
            command, image, workdir, env, volumes
        )

        try:
            result = subprocess.run(
                docker_cmd,
                capture_output=True,
                timeout=self.timeout,
                text=True,
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode,
                "sandbox": True,
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": f"Command timed out after {self.timeout}s",
                "output": "",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
            }

    def _build_docker_command(self, command, image, workdir,
                               env, volumes):
        cmd = ["docker", "run", "--rm"]
        cmd.extend(["--network", self.network])
        cmd.extend(["--memory", self.memory_limit])
        cmd.extend(["--cpus", self.cpu_limit])
        cmd.extend(["--workdir", workdir])
        if env:
            for k, v in env.items():
                cmd.extend(["-e", f"{k}={v}"])
        if volumes:
            for host_path, container_path in volumes.items():
                cmd.extend(["-v", f"{host_path}:{container_path}"])
        cmd.append(image)
        if isinstance(command, str):
            cmd.extend(["sh", "-c", command])
        else:
            cmd.extend(command)
        return cmd

    async def _execute_direct(self, command, workdir, env):
        """Fallback: execute directly (no sandbox)."""
        try:
            if isinstance(command, str):
                cmd = command
                shell = True
            else:
                cmd = command
                shell = False
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self.timeout,
                text=True,
                shell=shell,
                env={**os.environ, **(env or {})},
                cwd=workdir if os.path.exists(workdir) else None,
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "returncode": result.returncode,
                "sandbox": False,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "output": "",
            }

    def status(self) -> dict:
        return {
            "enabled": self.enabled,
            "available": self.is_available(),
            "image": self.default_image,
            "timeout": self.timeout,
            "network": self.network,
            "memory": self.memory_limit,
            "cpu": self.cpu_limit,
        }
