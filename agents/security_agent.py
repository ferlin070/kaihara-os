"""
Security Agent — real security capabilities with tool access.
Unlike GenericAgent, this agent can actually run security tools.
"""

import json
import socket
import subprocess
from datetime import datetime
from typing import Any

from agents.base_agent import BaseAgent, GenericAgent


class SecurityAgent(GenericAgent):
    """Security agent with real tool capabilities."""

    AGENT_TYPE = "security"
    SOUL_FILE = "security.md"

    def __init__(self, config: dict, memory=None, model_router=None,
                 token_juice=None, approval_gate=None,
                 sandbox=None, audit=None, pentest=None):
        super().__init__(config=config, memory=memory,
                         model_router=model_router,
                         token_juice=token_juice,
                         approval_gate=approval_gate)
        self.sandbox = sandbox
        self.audit = audit
        self.pentest = pentest
        self._register_tools()

    def _register_tools(self):
        """Register all security tools."""
        self.register_tool("dns_lookup", self._dns_lookup)
        self.register_tool("reverse_dns", self._reverse_dns)
        self.register_tool("port_scan", self._port_scan)
        self.register_tool("service_enum", self._service_enum)
        self.register_tool("subdomain_enum", self._subdomain_enum)
        self.register_tool("vuln_scan", self._vuln_scan)
        self.register_tool("xss_test", self._xss_test)
        self.register_tool("sqli_test", self._sqli_test)
        self.register_tool("idor_test", self._idor_test)
        self.register_tool("full_recon", self._full_recon)
        self.register_tool("run_pentest", self._run_pentest)

    # ============================================================
    # Tool Implementations
    # ============================================================

    async def _dns_lookup(self, target: str) -> dict:
        """DNS lookup for target."""
        try:
            ip = socket.gethostbyname(target)
            return {"success": True, "target": target, "ip": ip}
        except socket.gaierror as e:
            return {"success": False, "target": target, "error": str(e)}

    async def _reverse_dns(self, ip: str) -> dict:
        """Reverse DNS lookup."""
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            return {"success": True, "ip": ip, "hostname": hostname}
        except Exception as e:
            return {"success": False, "ip": ip, "error": str(e)}

    async def _port_scan(self, target: str, ports: str = "1-1000",
                          scan_type: str = "fast") -> dict:
        """nmap port scan."""
        args = ["nmap"]
        if scan_type == "fast":
            args.append("-F")
        elif scan_type == "stealth":
            args.append("-sS")
        elif scan_type == "version":
            args.extend(["-sV"])
        elif scan_type == "aggressive":
            args.append("-A")
        args.extend(["-p", ports, target])

        if self.sandbox:
            result = await self.sandbox.execute(args, image="instrumentisto/nmap")
        else:
            result = await self._run_command(args)

        return {
            "success": result.get("success", False),
            "target": target,
            "tool": "nmap",
            "scan_type": scan_type,
            "output": result.get("output", ""),
            "error": result.get("error", ""),
        }

    async def _service_enum(self, target: str, port: int = 80) -> dict:
        """Service enumeration via banner grab."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((target, port))
            banner = sock.recv(1024).decode("utf-8", errors="ignore").strip()
            sock.close()
            return {"success": True, "target": target, "port": port, "banner": banner}
        except Exception as e:
            return {"success": False, "target": target, "port": port, "error": str(e)}

    async def _subdomain_enum(self, domain: str) -> dict:
        """Subdomain discovery using DNS brute force."""
        common_subs = [
            "www", "mail", "ftp", "admin", "blog", "api",
            "dev", "staging", "test", "vpn", "ns1", "ns2",
            "shop", "app", "portal", "secure", "auth",
        ]
        found = []
        for sub in common_subs:
            subdomain = f"{sub}.{domain}"
            try:
                ip = socket.gethostbyname(subdomain)
                found.append({"subdomain": subdomain, "ip": ip})
            except socket.gaierror:
                continue
        return {"success": True, "domain": domain, "found": found, "count": len(found)}

    async def _vuln_scan(self, target: str) -> dict:
        """Basic vulnerability scan."""
        vulns = []
        checks = [
            ("https", self._check_https),
            ("security_headers", self._check_security_headers),
            ("directory_listing", self._check_directory_listing),
            ("error_disclosure", self._check_error_disclosure),
            ("xss", self._check_xss),
            ("sqli", self._check_sqli),
        ]
        for name, check_fn in checks:
            try:
                result = await check_fn(target)
                if result.get("vulnerable"):
                    vulns.append({"check": name, **result})
            except Exception as e:
                vulns.append({"check": name, "error": str(e)})
        return {"target": target, "vulnerabilities": vulns, "count": len(vulns)}

    async def _check_https(self, target: str) -> dict:
        """Check if HTTPS is available."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((target, 443))
            sock.close()
            return {"vulnerable": False, "message": "HTTPS available"}
        except Exception:
            return {"vulnerable": True, "message": "HTTPS not available", "severity": "medium"}

    async def _check_security_headers(self, target: str) -> dict:
        """Check for security headers."""
        import urllib.request
        try:
            req = urllib.request.Request(f"http://{target}", method="HEAD")
            req.add_header("User-Agent", "KaiharaSecurityScanner/1.0")
            resp = urllib.request.urlopen(req, timeout=5)
            headers = dict(resp.headers)
            missing = []
            for h in ["X-Frame-Options", "X-Content-Type-Options",
                      "Strict-Transport-Security", "Content-Security-Policy"]:
                if h not in headers:
                    missing.append(h)
            if missing:
                return {"vulnerable": True, "missing_headers": missing, "severity": "medium"}
            return {"vulnerable": False, "message": "All security headers present"}
        except Exception as e:
            return {"vulnerable": False, "error": str(e)}

    async def _check_directory_listing(self, target: str) -> dict:
        """Check for directory listing."""
        import urllib.request
        try:
            req = urllib.request.Request(f"http://{target}/")
            req.add_header("User-Agent", "KaiharaSecurityScanner/1.0")
            resp = urllib.request.urlopen(req, timeout=5)
            body = resp.read().decode("utf-8", errors="ignore")
            if "Index of" in body or "Directory listing" in body:
                return {"vulnerable": True, "message": "Directory listing enabled", "severity": "high"}
            return {"vulnerable": False, "message": "No directory listing found"}
        except Exception:
            return {"vulnerable": False, "message": "Could not check"}

    async def _check_error_disclosure(self, target: str) -> dict:
        """Check for error disclosure."""
        import urllib.request
        try:
            req = urllib.request.Request(f"http://{target}/nonexistent_page_12345")
            req.add_header("User-Agent", "KaiharaSecurityScanner/1.0")
            resp = urllib.request.urlopen(req, timeout=5)
            body = resp.read().decode("utf-8", errors="ignore")
            error_indicators = ["Traceback", "stack trace", "debug", "internal error"]
            for indicator in error_indicators:
                if indicator.lower() in body.lower():
                    return {"vulnerable": True, "message": f"Error disclosure: {indicator}", "severity": "medium"}
            return {"vulnerable": False, "message": "No error disclosure found"}
        except Exception:
            return {"vulnerable": False, "message": "Could not check"}

    async def _check_xss(self, target: str) -> dict:
        """Basic XSS check."""
        import urllib.request
        try:
            payload = "<script>alert(1)</script>"
            url = f"http://{target}/search?q={payload}"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "KaiharaSecurityScanner/1.0")
            resp = urllib.request.urlopen(req, timeout=5)
            body = resp.read().decode("utf-8", errors="ignore")
            if payload in body:
                return {"vulnerable": True, "message": "Reflected XSS found", "severity": "critical", "payload": payload}
            return {"vulnerable": False, "message": "No reflected XSS found"}
        except Exception:
            return {"vulnerable": False, "message": "Could not check"}

    async def _check_sqli(self, target: str) -> dict:
        """Basic SQL injection check."""
        import urllib.request
        try:
            payload = "' OR '1'='1"
            url = f"http://{target}/api?id={payload}"
            req = urllib.request.Request(url)
            req.add_header("User-Agent", "KaiharaSecurityScanner/1.0")
            resp = urllib.request.urlopen(req, timeout=5)
            body = resp.read().decode("utf-8", errors="ignore")
            sql_errors = ["sql syntax", "mysql", "sqlite", "postgresql", "ORA-"]
            for error in sql_errors:
                if error.lower() in body.lower():
                    return {"vulnerable": True, "message": f"SQL error disclosed: {error}", "severity": "critical"}
            return {"vulnerable": False, "message": "No SQL injection detected"}
        except Exception:
            return {"vulnerable": False, "message": "Could not check"}

    async def _xss_test(self, target: str, param: str = "q") -> dict:
        """XSS exploit validation (sandbox only)."""
        if not self.sandbox:
            return {"success": False, "error": "Sandbox required for XSS testing"}
        payload = "<script>alert(document.domain)</script>"
        cmd = f'curl -s "http://{target}/{param}={payload}"'
        result = await self.sandbox.execute(cmd)
        return {
            "success": result.get("success", False),
            "target": target,
            "test": "xss",
            "payload": payload,
            "output": result.get("output", "")[:500],
        }

    async def _sqli_test(self, target: str, param: str = "id") -> dict:
        """SQL injection exploit validation."""
        if not self.sandbox:
            return {"success": False, "error": "Sandbox required for SQLi testing"}
        payload = "' UNION SELECT NULL--"
        cmd = f'curl -s "http://{target}/?{param}={payload}"'
        result = await self.sandbox.execute(cmd)
        return {
            "success": result.get("success", False),
            "target": target,
            "test": "sqli",
            "payload": payload,
            "output": result.get("output", "")[:500],
        }

    async def _idor_test(self, target: str, path: str = "api/user") -> dict:
        """IDOR exploit validation."""
        if not self.sandbox:
            return {"success": False, "error": "Sandbox required for IDOR testing"}
        cmd = f'curl -s "http://{target}/{path}/1" && curl -s "http://{target}/{path}/2"'
        result = await self.sandbox.execute(cmd)
        return {
            "success": result.get("success", False),
            "target": target,
            "test": "idor",
            "output": result.get("output", "")[:500],
        }

    async def _full_recon(self, target: str) -> dict:
        """Run full reconnaissance suite."""
        results = {}
        results["dns"] = await self._dns_lookup(target)
        results["port_scan"] = await self._port_scan(target, scan_type="fast")
        results["subdomains"] = await self._subdomain_enum(target)
        return {"target": target, "results": results}

    async def _run_pentest(self, target: str, approved: bool = False) -> dict:
        """Run full pentest pipeline."""
        if self.pentest:
            return await self.pentest.run(target, approved=approved)
        return {"error": "Pentest pipeline not initialized"}

    async def _run_command(self, cmd: list[str]) -> dict:
        """Run a command directly (fallback)."""
        try:
            result = subprocess.run(
                cmd, capture_output=True, timeout=60, text=True
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
            }
        except FileNotFoundError:
            return {"success": False, "error": f"Command not found: {cmd[0]}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ============================================================
    # Main Run Method
    # ============================================================

    async def run(self, task: str, context: dict | None = None) -> dict:
        """Execute security task with real tools."""
        task_lower = task.lower()

        # Log to audit trail
        if self.audit:
            self.audit.log(self.AGENT_TYPE, "task_start", {"task": task[:200]})

        # Parse intent and dispatch to tools
        try:
            if any(kw in task_lower for kw in ["pentest", "full scan", "security scan"]):
                # Extract target from task
                target = self._extract_target(task)
                if not target:
                    return {"agent": self.AGENT_TYPE, "text": "Please specify a target (e.g., 'pentest example.com')", "status": "error"}

                # Check if target is authorized (no approval needed)
                authorized_domains = ["ghazwahgroup.com", "nakhodacloud.top", "kaihara-ai.nakhodacloud.top", "kaihara-api.nakhodacloud.top"]
                is_authorized = any(d in target for d in authorized_domains)

                # Check approval (skip for authorized domains)
                if self.approval_gate and not is_authorized:
                    req = await self.approval_gate.request(
                        "run_pentest", self.AGENT_TYPE,
                        {"target": target, "task": task}
                    )
                    if req.get("status") == "pending":
                        return {
                            "agent": self.AGENT_TYPE,
                            "text": f"Approval required for pentest on {target}. Please approve in the Security tab.",
                            "status": "pending_approval",
                            "request_id": req.get("request_id"),
                        }

                result = await self._run_pentest(target, approved=True)
                if self.audit:
                    self.audit.log(self.AGENT_TYPE, "pentest_complete", {"target": target}, result, "info")
                return {"agent": self.AGENT_TYPE, "text": json.dumps(result, indent=2), "status": "ok"}

            elif any(kw in task_lower for kw in ["port scan", "nmap", "scan port"]):
                target = self._extract_target(task)
                if not target:
                    return {"agent": self.AGENT_TYPE, "text": "Please specify a target.", "status": "error"}
                result = await self._port_scan(target)
                return {"agent": self.AGENT_TYPE, "text": json.dumps(result, indent=2), "status": "ok"}

            elif any(kw in task_lower for kw in ["dns", "lookup", "resolve"]):
                target = self._extract_target(task)
                if not target:
                    return {"agent": self.AGENT_TYPE, "text": "Please specify a target.", "status": "error"}
                result = await self._dns_lookup(target)
                return {"agent": self.AGENT_TYPE, "text": json.dumps(result, indent=2), "status": "ok"}

            elif any(kw in task_lower for kw in ["subdomain", "subdomains"]):
                target = self._extract_target(task)
                if not target:
                    return {"agent": self.AGENT_TYPE, "text": "Please specify a domain.", "status": "error"}
                result = await self._subdomain_enum(target)
                return {"agent": self.AGENT_TYPE, "text": json.dumps(result, indent=2), "status": "ok"}

            elif any(kw in task_lower for kw in ["vuln", "vulnerability", "vulnerabilities"]):
                target = self._extract_target(task)
                if not target:
                    return {"agent": self.AGENT_TYPE, "text": "Please specify a target.", "status": "error"}
                result = await self._vuln_scan(target)
                return {"agent": self.AGENT_TYPE, "text": json.dumps(result, indent=2), "status": "ok"}

            elif any(kw in task_lower for kw in ["xss", "cross-site"]):
                target = self._extract_target(task)
                if not target:
                    return {"agent": self.AGENT_TYPE, "text": "Please specify a target.", "status": "error"}
                result = await self._xss_test(target)
                return {"agent": self.AGENT_TYPE, "text": json.dumps(result, indent=2), "status": "ok"}

            elif any(kw in task_lower for kw in ["sqli", "sql injection", "sql inject"]):
                target = self._extract_target(task)
                if not target:
                    return {"agent": self.AGENT_TYPE, "text": "Please specify a target.", "status": "error"}
                result = await self._sqli_test(target)
                return {"agent": self.AGENT_TYPE, "text": json.dumps(result, indent=2), "status": "ok"}

            elif any(kw in task_lower for kw in ["recon", "reconnaissance", "gather intel"]):
                target = self._extract_target(task)
                if not target:
                    return {"agent": self.AGENT_TYPE, "text": "Please specify a target.", "status": "error"}
                result = await self._full_recon(target)
                return {"agent": self.AGENT_TYPE, "text": json.dumps(result, indent=2), "status": "ok"}

            elif any(kw in task_lower for kw in ["status", "tools", "capabilities"]):
                tools_list = list(self.tools.keys())
                return {
                    "agent": self.AGENT_TYPE,
                    "text": f"Available tools: {', '.join(tools_list)}",
                    "tools": tools_list,
                    "status": "ok",
                }

            else:
                # Fallback to LLM for general security questions
                response = await self.think(task, context=context or "")
                return {"agent": self.AGENT_TYPE, "text": response, "status": "ok"}

        except Exception as e:
            if self.audit:
                self.audit.log(self.AGENT_TYPE, "task_error", {"task": task[:200], "error": str(e)}, severity="error")
            return {"agent": self.AGENT_TYPE, "text": f"Error: {str(e)}", "status": "error"}

    def _extract_target(self, task: str) -> str | None:
        """Extract target domain/IP from task text."""
        import re
        # Match domain or IP patterns
        patterns = [
            r'(?:on|for|to|at|scan|test)\s+([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,})',
            r'([a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,})',
            r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
        ]
        for pattern in patterns:
            match = re.search(pattern, task, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def status(self) -> dict:
        """Extended status with tool info."""
        base_status = super().status()
        base_status.update({
            "tools": list(self.tools.keys()),
            "sandbox_available": self.sandbox.is_available() if self.sandbox else False,
            "audit_enabled": self.audit is not None,
            "approval_gate_enabled": self.approval_gate is not None,
            "pentest_available": self.pentest is not None,
        })
        return base_status
