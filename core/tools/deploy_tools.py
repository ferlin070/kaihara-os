"""
Deploy Tools — comprehensive deployment toolkit.
Docker, Git, Proxmox LXC, Systemd, Nginx, Database, Rollback, Health Check.
"""

import os
import subprocess
import shutil
import json
import time
from pathlib import Path
from datetime import datetime


# ============================================================
# Docker Tools
# ============================================================

def docker_ps(all_containers=False) -> dict:
    """List Docker containers."""
    cmd = ["docker", "ps", "--format", "json"]
    if all_containers:
        cmd.append("-a")
    try:
        out = subprocess.check_output(cmd, timeout=30, text=True, stderr=subprocess.PIPE)
        containers = []
        for line in out.strip().split("\n"):
            if line.strip():
                containers.append(json.loads(line))
        return {"ok": True, "containers": containers, "count": len(containers)}
    except FileNotFoundError:
        return {"ok": False, "error": "Docker not installed"}
    except subprocess.CalledProcessError as e:
        return {"ok": False, "error": e.stderr.strip()}


def docker_compose(action: str, service: str = None, project_dir: str = ".") -> dict:
    """Docker Compose up/down/restart/logs."""
    valid = ["up", "down", "restart", "logs", "ps", "build", "pull"]
    if action not in valid:
        return {"ok": False, "error": f"Invalid action. Use: {valid}"}
    cmd = ["docker", "compose", action, "-d"]
    if service:
        cmd.append(service)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                                cwd=project_dir)
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-1000:] if result.stderr else "",
            "action": action,
        }
    except FileNotFoundError:
        return {"ok": False, "error": "docker-compose not installed"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Command timed out (120s)"}


def docker_build(image: str, path: str = ".", tag: str = "latest") -> dict:
    """Build Docker image."""
    cmd = ["docker", "build", "-t", f"{image}:{tag}", path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return {
            "ok": result.returncode == 0,
            "image": f"{image}:{tag}",
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-1000:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Build timed out (300s)"}


def docker_logs(container: str, lines: int = 50) -> dict:
    """Get container logs."""
    cmd = ["docker", "logs", "--tail", str(lines), container]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return {
            "ok": result.returncode == 0,
            "container": container,
            "logs": result.stdout[-3000:] if result.stdout else "",
            "errors": result.stderr[-1000:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Timeout"}


def docker_exec(container: str, command: str) -> dict:
    """Execute command in running container."""
    cmd = ["docker", "exec", container] + command.split()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return {
            "ok": result.returncode == 0,
            "container": container,
            "command": command,
            "stdout": result.stdout[-3000:] if result.stdout else "",
            "stderr": result.stderr[-1000:] if result.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "Exec timed out (60s)"}


def docker_inspect(container: str) -> dict:
    """Inspect container details."""
    cmd = ["docker", "inspect", container]
    try:
        out = subprocess.check_output(cmd, timeout=10, text=True)
        data = json.loads(out)
        if data:
            c = data[0]
            state = c.get("State", {})
            return {
                "ok": True,
                "container": container,
                "status": state.get("Status", "unknown"),
                "running": state.get("Running", False),
                "image": c.get("Config", {}).get("Image", ""),
                "ports": c.get("NetworkSettings", {}).get("Ports", {}),
                "created": c.get("Created", ""),
            }
        return {"ok": False, "error": "Container not found"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def docker_cleanup(days: int = 7) -> dict:
    """Remove stopped containers, dangling images, unused networks."""
    results = {}
    # Remove stopped containers
    try:
        out = subprocess.check_output(
            ["docker", "container", "prune", "-f"], timeout=30, text=True
        )
        results["containers"] = out.strip()
    except Exception as e:
        results["containers"] = str(e)
    # Remove dangling images
    try:
        out = subprocess.check_output(
            ["docker", "image", "prune", "-f"], timeout=30, text=True
        )
        results["images"] = out.strip()
    except Exception as e:
        results["images"] = str(e)
    # Remove unused networks
    try:
        out = subprocess.check_output(
            ["docker", "network", "prune", "-f"], timeout=30, text=True
        )
        results["networks"] = out.strip()
    except Exception as e:
        results["networks"] = str(e)
    return {"ok": True, "cleaned": results}


# ============================================================
# Git Tools
# ============================================================

def git_status(path: str = ".") -> dict:
    """Get git repo status."""
    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=path,
            timeout=10, text=True, stderr=subprocess.PIPE
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=path,
            timeout=10, text=True
        ).strip()
        log_out = subprocess.check_output(
            ["git", "log", "--oneline", "-5"], cwd=path,
            timeout=10, text=True
        ).strip()
        modified = len([l for l in status.split("\n") if l.strip()])
        return {
            "ok": True,
            "branch": branch,
            "modified_files": modified,
            "recent_commits": log_out.split("\n"),
            "dirty": modified > 0,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def git_pull(path: str = ".", branch: str = "master") -> dict:
    """Pull latest changes."""
    try:
        result = subprocess.run(
            ["git", "pull", "origin", branch], cwd=path,
            capture_output=True, text=True, timeout=60
        )
        return {
            "ok": result.returncode == 0,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def git_deploy(path: str = ".", branch: str = "master") -> dict:
    """Full deploy: pull + rebuild services."""
    steps = []
    # Step 1: Stash local changes
    try:
        subprocess.run(["git", "stash"], cwd=path, capture_output=True, timeout=10)
        steps.append({"step": "stash", "ok": True})
    except Exception as e:
        steps.append({"step": "stash", "ok": False, "error": str(e)})

    # Step 2: Pull
    pull = git_pull(path, branch)
    steps.append({"step": "pull", **pull})

    # Step 3: Check for docker-compose
    compose_file = Path(path) / "docker-compose.yml"
    if compose_file.exists():
        build = docker_compose("build", project_dir=path)
        steps.append({"step": "build", **build})
        restart = docker_compose("restart", project_dir=path)
        steps.append({"step": "restart", **restart})

    return {"ok": all(s.get("ok") for s in steps), "steps": steps}


def git_rollback(path: str = ".", commits: int = 1) -> dict:
    """Rollback to previous commit(s)."""
    try:
        # Get current HEAD
        current = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=path, timeout=10, text=True
        ).strip()
        # Reset
        result = subprocess.run(
            ["git", "reset", "--hard", f"HEAD~{commits}"], cwd=path,
            capture_output=True, text=True, timeout=10
        )
        new_head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=path, timeout=10, text=True
        ).strip()
        return {
            "ok": result.returncode == 0,
            "from": current[:8],
            "to": new_head[:8],
            "commits_rolled": commits,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# Proxmox LXC Tools
# ============================================================

def lxc_list(proxmox_host: str = "192.168.1.99") -> dict:
    """List LXC containers via Proxmox API (requires SSH)."""
    try:
        out = subprocess.check_output(
            ["ssh", proxmox_host, "pct list"], timeout=15, text=True
        )
        containers = []
        for line in out.strip().split("\n")[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 2:
                containers.append({
                    "vmid": parts[0],
                    "status": parts[1],
                    "name": parts[2] if len(parts) > 2 else "",
                })
        return {"ok": True, "containers": containers, "count": len(containers)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def lxc_manage(vmid: str, action: str, proxmox_host: str = "192.168.1.99") -> dict:
    """Start/stop/restart LXC container."""
    valid = ["start", "stop", "restart", "shutdown"]
    if action not in valid:
        return {"ok": False, "error": f"Invalid action. Use: {valid}"}
    try:
        result = subprocess.run(
            ["ssh", proxmox_host, "pct", action, vmid],
            capture_output=True, text=True, timeout=60
        )
        return {
            "ok": result.returncode == 0,
            "vmid": vmid,
            "action": action,
            "output": result.stdout[-1000:] if result.stdout else "",
            "error": result.stderr[-500:] if result.stderr else "",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def lxc_status(vmid: str, proxmox_host: str = "192.168.1.99") -> dict:
    """Get LXC container status."""
    try:
        out = subprocess.check_output(
            ["ssh", proxmox_host, "pct", "status", vmid],
            timeout=10, text=True
        )
        return {"ok": True, "vmid": vmid, "status": out.strip()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# Systemd / Service Tools
# ============================================================

def systemctl(action: str, service: str) -> dict:
    """Systemctl start/stop/restart/enable/disable/status."""
    valid = ["start", "stop", "restart", "enable", "disable", "status", "is-active"]
    if action not in valid:
        return {"ok": False, "error": f"Invalid action. Use: {valid}"}
    try:
        result = subprocess.run(
            ["systemctl", action, service],
            capture_output=True, text=True, timeout=30
        )
        return {
            "ok": result.returncode == 0,
            "service": service,
            "action": action,
            "output": result.stdout[-1000:] if result.stdout else "",
            "error": result.stderr[-500:] if result.stderr else "",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def service_status(service: str) -> dict:
    """Check if service is running."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service],
            capture_output=True, text=True, timeout=10
        )
        running = result.stdout.strip() == "active"
        # Get uptime
        try:
            uptime = subprocess.check_output(
                ["systemctl", "show", service, "--property=ActiveEnterTimestamp"],
                timeout=5, text=True
            ).strip().split("=", 1)[-1]
        except Exception:
            uptime = "unknown"
        return {"ok": True, "service": service, "running": running, "since": uptime}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def nginx_reload() -> dict:
    """Reload nginx configuration."""
    try:
        # Test config first
        test = subprocess.run(
            ["nginx", "-t"], capture_output=True, text=True, timeout=10
        )
        if test.returncode != 0:
            return {"ok": False, "error": f"Config test failed: {test.stderr}"}
        # Reload
        result = subprocess.run(
            ["nginx", "-s", "reload"], capture_output=True, text=True, timeout=10
        )
        return {"ok": result.returncode == 0, "action": "reload"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# Server Tools
# ============================================================

def apt_install(packages: list[str]) -> dict:
    """Install packages via apt."""
    try:
        # Update first
        subprocess.run(["apt", "update", "-qq"], timeout=60, capture_output=True)
        # Install
        result = subprocess.run(
            ["apt", "install", "-y", "-qq"] + packages,
            capture_output=True, text=True, timeout=120
        )
        return {
            "ok": result.returncode == 0,
            "packages": packages,
            "output": result.stdout[-2000:] if result.stdout else "",
            "error": result.stderr[-500:] if result.stderr else "",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def disk_check(path: str = "/") -> dict:
    """Check disk usage."""
    try:
        usage = shutil.disk_usage(path)
        return {
            "ok": True,
            "path": path,
            "total_gb": round(usage.total / (1024**3), 1),
            "used_gb": round(usage.used / (1024**3), 1),
            "free_gb": round(usage.free / (1024**3), 1),
            "percent": round(usage.used / usage.total * 100, 1),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def log_view(log_file: str, lines: int = 50) -> dict:
    """View log file tail."""
    try:
        with open(log_file, "r") as f:
            all_lines = f.readlines()
            tail = all_lines[-lines:]
        return {"ok": True, "file": log_file, "lines": len(tail), "logs": "".join(tail)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def port_check(port: int) -> dict:
    """Check if port is listening."""
    import socket
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=3):
            return {"ok": True, "port": port, "status": "open"}
    except Exception:
        return {"ok": True, "port": port, "status": "closed"}


# ============================================================
# Database Tools
# ============================================================

def db_backup(db_type: str, db_name: str, output_dir: str = "/tmp") -> dict:
    """Backup database."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{output_dir}/{db_name}_{timestamp}.sql.gz"

    if db_type == "postgres":
        cmd = f"pg_dump {db_name} | gzip > {output_file}"
    elif db_type == "mysql":
        cmd = f"mysqldump {db_name} | gzip > {output_file}"
    else:
        return {"ok": False, "error": f"Unsupported DB type: {db_type}"}

    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=300
        )
        return {
            "ok": result.returncode == 0,
            "file": output_file,
            "db_type": db_type,
            "db_name": db_name,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ============================================================
# Deployment Pipeline
# ============================================================

def full_deploy(repo_path: str, service_name: str = None,
                branch: str = "master", proxmox_host: str = None) -> dict:
    """Complete deployment pipeline."""
    steps = []

    # 1. Check disk space
    disk = disk_check("/")
    steps.append({"step": "disk_check", **disk})
    if disk.get("ok") and disk.get("percent", 0) > 90:
        return {"ok": False, "error": "Disk space critical", "steps": steps}

    # 2. Git status
    status = git_status(repo_path)
    steps.append({"step": "git_status", **status})

    # 3. Git pull
    pull = git_pull(repo_path, branch)
    steps.append({"step": "git_pull", **pull})

    # 4. Docker build if compose exists
    compose_file = Path(repo_path) / "docker-compose.yml"
    if compose_file.exists():
        build = docker_compose("build", project_dir=repo_path)
        steps.append({"step": "docker_build", **build})
        restart = docker_compose("restart", project_dir=repo_path)
        steps.append({"step": "docker_restart", **restart})

    # 5. Restart service if specified
    if service_name:
        restart = systemctl("restart", service_name)
        steps.append({"step": "service_restart", **restart})

    # 6. Health check
    time.sleep(3)
    health = health_check(repo_path)
    steps.append({"step": "health_check", **health})

    ok = all(s.get("ok", True) for s in steps)
    return {"ok": ok, "steps": steps, "timestamp": datetime.now().isoformat()}


def health_check(path: str = ".") -> dict:
    """Post-deployment health check."""
    checks = []
    # Check main process
    try:
        result = subprocess.run(
            ["pgrep", "-f", "kaihara"], capture_output=True, text=True, timeout=5
        )
        checks.append({"check": "kaihara_process", "ok": result.returncode == 0})
    except Exception:
        checks.append({"check": "kaihara_process", "ok": False})

    # Check API port
    port = port_check(7000)
    checks.append({"check": "api_port", **port})

    # Check disk
    disk = disk_check("/")
    checks.append({"check": "disk_space", "ok": disk.get("percent", 100) < 95})

    return {"ok": all(c.get("ok") for c in checks), "checks": checks}


# ============================================================
# Rollback
# ============================================================

def rollback(repo_path: str, commits: int = 1, service_name: str = None) -> dict:
    """Full rollback: git reset + service restart."""
    steps = []
    # Git rollback
    git_rb = git_rollback(repo_path, commits)
    steps.append({"step": "git_rollback", **git_rb})

    # Restart service
    if service_name:
        restart = systemctl("restart", service_name)
        steps.append({"step": "service_restart", **restart})

    return {"ok": all(s.get("ok") for s in steps), "steps": steps}


# ============================================================
# Deployment History
# ============================================================

_deploy_history = []

def record_deploy(action: str, result: dict, user: str = "system") -> None:
    """Record deployment action."""
    _deploy_history.append({
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "user": user,
        "ok": result.get("ok", False),
    })
    # Keep last 100
    if len(_deploy_history) > 100:
        _deploy_history.pop(0)


def get_deploy_history(limit: int = 20) -> list:
    """Get recent deployment history."""
    return _deploy_history[-limit:]
