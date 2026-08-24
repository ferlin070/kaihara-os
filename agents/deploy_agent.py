"""
Deploy Agent — deployment, CI/CD, server management, rollback.
Handles Docker, Git, Proxmox LXC, Systemd, Nginx, Database, Health checks.
"""

import json
from agents.base_agent import BaseAgent
from core.tools.deploy_tools import (
    docker_ps, docker_compose, docker_build, docker_logs, docker_exec,
    docker_inspect, docker_cleanup,
    git_status, git_pull, git_deploy, git_rollback,
    lxc_list, lxc_manage, lxc_status,
    systemctl, service_status, nginx_reload,
    apt_install, disk_check, log_view, port_check,
    db_backup, full_deploy, health_check, rollback,
    record_deploy, get_deploy_history,
)


class DeployAgent(BaseAgent):
    """Deployment and infrastructure management agent."""

    AGENT_TYPE = "deploy"

    # Deployment actions that require approval
    APPROVAL_REQUIRED = {
        "deploy_to_production", "push_to_git", "restart_service",
        "modify_database", "install_package", "git_rollback", "lxc_manage",
        "full_deploy", "db_backup",
    }

    def __init__(self, config=None, memory=None, model_router=None,
                 token_juice=None, approval_gate=None, **kwargs):
        super().__init__(
            config=config, memory=memory, model_router=model_router,
            token_juice=token_juice, approval_gate=approval_gate, **kwargs,
        )
        self.proxmox_host = (config or {}).get("proxmox_host", "192.168.1.99")
        self.repo_path = (config or {}).get("repo_path", "/mnt/kaihara-core")
        self._register_tools()

    def _register_tools(self):
        # Docker tools
        self.register_tool("docker_ps", self._docker_ps)
        self.register_tool("docker_compose", self._docker_compose)
        self.register_tool("docker_build", self._docker_build)
        self.register_tool("docker_logs", self._docker_logs)
        self.register_tool("docker_exec", self._docker_exec)
        self.register_tool("docker_inspect", self._docker_inspect)
        self.register_tool("docker_cleanup", self._docker_cleanup)

        # Git tools
        self.register_tool("git_status", self._git_status)
        self.register_tool("git_pull", self._git_pull)
        self.register_tool("git_deploy", self._git_deploy)
        self.register_tool("git_rollback", self._git_rollback)

        # Proxmox tools
        self.register_tool("lxc_list", self._lxc_list)
        self.register_tool("lxc_manage", self._lxc_manage)
        self.register_tool("lxc_status", self._lxc_status)

        # Service tools
        self.register_tool("systemctl", self._systemctl)
        self.register_tool("service_status", self._service_status)
        self.register_tool("nginx_reload", self._nginx_reload)

        # Server tools
        self.register_tool("apt_install", self._apt_install)
        self.register_tool("disk_check", self._disk_check)
        self.register_tool("log_view", self._log_view)
        self.register_tool("port_check", self._port_check)

        # Database tools
        self.register_tool("db_backup", self._db_backup)

        # Pipeline tools
        self.register_tool("full_deploy", self._full_deploy)
        self.register_tool("health_check", self._health_check)
        self.register_tool("rollback", self._rollback)

        # History
        self.register_tool("deploy_history", self._deploy_history)

    # ---- Docker ----

    async def _docker_ps(self, all_containers: bool = False) -> dict:
        return docker_ps(all_containers)

    async def _docker_compose(self, action: str, service: str = None,
                              project_dir: str = ".") -> dict:
        result = docker_compose(action, service, project_dir)
        record_deploy(f"docker_compose_{action}", result)
        return result

    async def _docker_build(self, image: str, path: str = ".",
                            tag: str = "latest") -> dict:
        result = docker_build(image, path, tag)
        record_deploy("docker_build", result)
        return result

    async def _docker_logs(self, container: str, lines: int = 50) -> dict:
        return docker_logs(container, lines)

    async def _docker_exec(self, container: str, command: str) -> dict:
        return docker_exec(container, command)

    async def _docker_inspect(self, container: str) -> dict:
        return docker_inspect(container)

    async def _docker_cleanup(self) -> dict:
        result = docker_cleanup()
        record_deploy("docker_cleanup", result)
        return result

    # ---- Git ----

    async def _git_status(self) -> dict:
        return git_status(self.repo_path)

    async def _git_pull(self) -> dict:
        result = git_pull(self.repo_path)
        record_deploy("git_pull", result)
        return result

    async def _git_deploy(self, branch: str = "master") -> dict:
        result = git_deploy(self.repo_path, branch)
        record_deploy("git_deploy", result)
        return result

    async def _git_rollback(self, commits: int = 1) -> dict:
        result = git_rollback(self.repo_path, commits)
        record_deploy("git_rollback", result)
        return result

    # ---- Proxmox ----

    async def _lxc_list(self) -> dict:
        return lxc_list(self.proxmox_host)

    async def _lxc_manage(self, vmid: str, action: str) -> dict:
        result = lxc_manage(vmid, action, self.proxmox_host)
        record_deploy(f"lxc_{action}_{vmid}", result)
        return result

    async def _lxc_status(self, vmid: str) -> dict:
        return lxc_status(vmid, self.proxmox_host)

    # ---- Services ----

    async def _systemctl(self, action: str, service: str) -> dict:
        result = systemctl(action, service)
        record_deploy(f"systemctl_{action}_{service}", result)
        return result

    async def _service_status(self, service: str) -> dict:
        return service_status(service)

    async def _nginx_reload(self) -> dict:
        result = nginx_reload()
        record_deploy("nginx_reload", result)
        return result

    # ---- Server ----

    async def _apt_install(self, packages: list) -> dict:
        result = apt_install(packages)
        record_deploy("apt_install", result)
        return result

    async def _disk_check(self) -> dict:
        return disk_check()

    async def _log_view(self, log_file: str, lines: int = 50) -> dict:
        return log_view(log_file, lines)

    async def _port_check(self, port: int) -> dict:
        return port_check(port)

    # ---- Database ----

    async def _db_backup(self, db_type: str, db_name: str,
                         output_dir: str = "/tmp") -> dict:
        result = db_backup(db_type, db_name, output_dir)
        record_deploy("db_backup", result)
        return result

    # ---- Pipeline ----

    async def _full_deploy(self, service_name: str = None,
                           branch: str = "master") -> dict:
        result = full_deploy(self.repo_path, service_name, branch,
                             self.proxmox_host)
        record_deploy("full_deploy", result)
        return result

    async def _health_check(self) -> dict:
        return health_check(self.repo_path)

    async def _rollback(self, commits: int = 1,
                        service_name: str = None) -> dict:
        result = rollback(self.repo_path, commits, service_name)
        record_deploy("rollback", result)
        return result

    async def _deploy_history(self, limit: int = 20) -> dict:
        return {"history": get_deploy_history(limit)}

    # ---- Main task runner ----

    async def run_task(self) -> dict:
        """Run deployment health check as background task."""
        return await self._health_check()
