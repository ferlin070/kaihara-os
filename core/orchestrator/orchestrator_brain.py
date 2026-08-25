"""
Orchestrator Brain — Kaihara's executive decision-making system.
"""

import json
import logging

logger = logging.getLogger("kaihara.orchestrator_brain")


class OrchestratorBrain:

    FLEET_REGISTRY = {
        "kaihara": {
            "name": "Kaihara (Orchestrator)",
            "role": "Chief Executive — orchestrates all agents",
            "tools": ["generate_pdf", "send_telegram", "web_search", "memory", "all_fleet_agents"],
            "skills": ["orchestration", "delegation", "analysis", "report_generation"],
            "description": "The main AI brain. Coordinates all agents, makes decisions, generates reports.",
        },
        "research": {
            "name": "Research Agent",
            "role": "Data Collection & Analysis",
            "tools": ["web_search", "scrape_website", "search_places"],
            "skills": ["web_research", "data_analysis", "trend_identification", "competitive_intelligence"],
            "description": "Gathers information from the web, analyzes data, produces research reports.",
        },
        "marketing": {
            "name": "Marketing Agent",
            "role": "Digital Marketing & CRM",
            "tools": ["crm", "campaigns", "content_creation", "seo_audit", "lead_management"],
            "skills": ["email_marketing", "social_media", "seo", "copywriting", "customer_analysis"],
            "description": "Handles marketing campaigns, CRM, content creation, SEO.",
        },
        "security": {
            "name": "Security Agent",
            "role": "Cybersecurity & Penetration Testing",
            "tools": ["dns_lookup", "reverse_dns", "port_scan", "service_enum", "subdomain_enum",
                       "vuln_scan", "xss_test", "sqli_test", "idor_test", "full_recon", "run_pentest"],
            "skills": ["reconnaissance", "vulnerability_assessment", "penetration_testing", "security_audit"],
            "description": "Performs security scans, vulnerability assessments, and penetration tests.",
        },
        "deploy": {
            "name": "Deploy Agent",
            "role": "Infrastructure & DevOps",
            "tools": ["docker_ps", "docker_compose", "git_status", "git_pull", "lxc_list",
                       "systemctl", "nginx_reload", "health_check", "rollback"],
            "skills": ["docker_management", "git_operations", "lxc_management", "systemd", "deployment"],
            "description": "Manages servers, containers, deployments, and infrastructure.",
        },
        "editor": {
            "name": "Editor Agent",
            "role": "Content Creation & Media",
            "tools": ["video_probe", "video_trim", "video_concat", "video_overlay", "video_add_audio",
                       "video_add_text", "video_add_subtitles", "video_from_images", "video_export",
                       "image_resize", "image_composite", "image_filter", "generate_thumbnail",
                       "audio_extract", "audio_trim", "audio_normalize",
                       "search_stock_image", "search_stock_video",
                       "generate_poster", "generate_banner", "generate_instagram_post",
                       "generate_youtube_thumbnail", "generate_quote_image"],
            "skills": ["video_editing", "tts", "image_gen", "document_creation", "media_management",
                       "stock_media", "poster_design", "thumbnail_creation"],
            "description": "Creates videos, audio, images, PDFs, presentations. Has FFmpeg, MoviePy, Pillow, Pexels API, Edge TTS, Google Drive, Pinterest.",
        },
        "meta": {
            "name": "Meta Agent",
            "role": "Self-Monitoring & Optimization",
            "tools": ["pattern_detection", "suggestion_generation", "performance_analysis"],
            "skills": ["self_reflection", "pattern_recognition", "optimization", "learning"],
            "description": "Monitors system performance, detects patterns, suggests improvements.",
        },
    }

    CHANNEL_INFO = {
        "telegram": {
            "name": "Telegram",
            "bot": "@my_chserver_bot",
            "chat_id": "8275355102",
            "status": "configured",
            "capabilities": ["send_text", "send_document", "send_photo", "receive_messages"],
        },
        "whatsapp": {
            "name": "WhatsApp",
            "bridge": "Baileys v6.7",
            "status": "connected",
            "capabilities": ["send_text", "receive_messages", "media"],
        },
        "email": {
            "name": "Email (Gmail)",
            "account": "ghazwahgroup@gmail.com",
            "smtp": "smtp.gmail.com:587",
            "imap": "imap.gmail.com:993",
            "status": "configured",
            "capabilities": ["send_email", "receive_email"],
        },
    }

    SYSTEM_INFO = {
        "host": {"name": "cloudhosting", "ip": "192.168.1.99", "gpu": "RTX 3060 Ti 8GB", "ram": "125GB", "cores": "28"},
        "core_api": {"ct": 203, "port": 7000, "status": "active"},
        "dashboard": {"ct": 204, "port": 5173, "status": "active"},
        "telegram_runner": {"ct": 205, "status": "active"},
        "pentest_tools": {"ct": 206, "status": "active"},
        "kernel_runner": {"ct": 207, "status": "active"},
        "gpu_servers": {
            "tesla_t4": {"ip": "192.168.10.10", "tailscale": "100.92.235.77", "vram": "15GB", "models": ["gemma-4-E4B", "qwen2.5:14b"]},
            "rtx_5060ti": {"ip": "192.168.1.100", "tailscale": "100.74.222.77", "vram": "16GB", "models": ["qwen3:32b", "qwen2.5:32b"]},
        },
    }

    def get_fleet_summary(self):
        lines = ["## Fleet Agent Summary\n"]
        for key, agent in self.FLEET_REGISTRY.items():
            tools_str = ", ".join(agent["tools"][:5])
            if len(agent["tools"]) > 5:
                tools_str += f" (+{len(agent['tools'])-5} more)"
            lines.append(f"### {agent['name']}")
            lines.append(f"- **Role:** {agent['role']}")
            lines.append(f"- **Tools:** {tools_str}")
            lines.append(f"- **Skills:** {', '.join(agent['skills'][:3])}")
            lines.append("")
        return "\n".join(lines)

    def get_channel_summary(self):
        lines = ["## Communication Channels\n"]
        for key, ch in self.CHANNEL_INFO.items():
            lines.append(f"### {ch['name']}")
            lines.append(f"- **Status:** {ch['status']}")
            lines.append(f"- **Capabilities:** {', '.join(ch['capabilities'])}")
            lines.append("")
        return "\n".join(lines)

    def get_system_summary(self):
        lines = ["## System Infrastructure\n"]
        h = self.SYSTEM_INFO["host"]
        lines.append(f"### Host: {h['name']}")
        lines.append(f"- IP: {h['ip']}, GPU: {h['gpu']}, RAM: {h['ram']}, CPU: {h['cores']} cores\n")
        lines.append("### Containers")
        for name, info in self.SYSTEM_INFO.items():
            if isinstance(info, dict) and "ct" in info:
                lines.append(f"- **{name}**: CT {info['ct']} ({info.get('status', 'unknown')})")
        lines.append("\n### GPU Servers")
        for name, info in self.SYSTEM_INFO.get("gpu_servers", {}).items():
            lines.append(f"- **{name}**: {info['ip']} — {info['vram']} — Models: {', '.join(info['models'])}")
        return "\n".join(lines)

    def get_full_context(self):
        return (
            "# ORCHESTRATOR CONTEXT\n\n"
            "You are Kaihara — the CEO/Orchestrator of this AI fleet.\n"
            "You have these agents under you: research, marketing, security, deploy, editor, meta.\n"
            "You can: 1) Answer directly using your knowledge 2) Delegate to agents 3) Synthesize results.\n"
            "When user asks about something, determine WHICH AGENT handles it, then answer or delegate.\n"
            "NEVER say you cannot access files or Telegram — you have tools for PDF, Telegram, web search.\n\n"
            + self.get_fleet_summary() + "\n"
            + self.get_channel_summary() + "\n"
            + self.get_system_summary()
        )


brain = OrchestratorBrain()
