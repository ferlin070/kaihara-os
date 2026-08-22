"""
Model Router — multi-model routing (OpenCode pattern).
Supports 75+ providers, variants, privacy mode, per-agent routing.
"""

import os
import httpx
from typing import Any


class ModelRouter:
    """Route requests to the right LLM based on config."""

    def __init__(self, config: dict):
        self.config = config
        self.providers = config.get("provider", {})
        self.privacy_mode = config.get("privacy", {}).get("mode", True)
        self.default = config.get("model", {}).get("default", "ollama/llama3.1:8b")
        self.small = config.get("model", {}).get("small_model", "ollama/llama3.1:1b")
        self.agent_models = {}
        for key, val in config.items():
            if key.startswith("agent."):
                agent_name = key.split(".", 1)[1]
                self.agent_models[agent_name] = val.get("model", self.default)

    def _parse_model_id(self, model_id: str) -> tuple[str, str]:
        if "/" in model_id:
            provider, model = model_id.split("/", 1)
        else:
            provider, model = "ollama", model_id
        return provider, model

    def _get_provider_config(self, provider: str) -> dict:
        return self.providers.get(provider, {})

    def _check_privacy(self, provider: str) -> bool:
        if not self.privacy_mode:
            return True
        return provider in ("ollama", "llama.cpp", "lmstudio")

    def get_model(self, agent_type: str | None = None,
                  complexity: str = "medium") -> str:
        """Select model based on agent type and task complexity."""
        if agent_type and agent_type in self.agent_models:
            return self.agent_models[agent_type]
        if complexity == "simple":
            return self.small
        return self.default

    async def complete(self, system: str, messages: list[dict],
                       model: str | None = None) -> str:
        """Send completion request to the appropriate provider."""
        model_id = model or self.default
        provider, model_name = self._parse_model_id(model_id)

        if not self._check_privacy(provider):
            return ("[privacy mode: cloud providers disabled. "
                    "Set privacy.mode=false to enable.]")

        provider_config = self._get_provider_config(provider)
        base_url = provider_config.get("base_url")
        api_key = provider_config.get("api_key") or self._get_api_key(provider)
        api_key_header = provider_config.get("api_key_header", "Authorization")

        if provider == "ollama" or (base_url and "11434" in base_url):
            return await self._call_ollama(
                base_url or "http://localhost:11434",
                model_name, system, messages
            )
        return await self._call_openai_compat(
            base_url or "https://api.openai.com/v1",
            api_key, model_name, system, messages,
            api_key_header
        )

    def _get_api_key(self, provider: str) -> str | None:
        env_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
        }
        env_var = env_map.get(provider, f"{provider.upper()}_API_KEY")
        return os.environ.get(env_var)

    async def _call_ollama(self, base_url: str, model: str,
                           system: str, messages: list[dict]) -> str:
        url = f"{base_url}/api/chat"
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}] + messages,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("message", {}).get("content", "")
            except httpx.ConnectError:
                return (f"[Ollama not running at {base_url}. "
                        f"Start with: ollama serve]")
            except Exception as e:
                return f"[Error: {e}]"

    async def _call_openai_compat(self, base_url: str, api_key: str | None,
                                   model: str, system: str,
                                   messages: list[dict],
                                   api_key_header: str = "Authorization") -> str:
        if not api_key:
            return f"[No API key for provider. Set env var or config.]"
        url = f"{base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
        }
        # Support custom header (e.g. X-API-Key for rootsys.cloud)
        if api_key_header.lower() == "authorization":
            headers["Authorization"] = f"Bearer {api_key}"
        else:
            headers[api_key_header] = api_key
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}] + messages,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                body = e.response.text[:200] if e.response else ""
                return f"[API Error {e.response.status_code}: {body}]"
            except Exception as e:
                return f"[Error: {e}]"

    def list_available(self) -> list[str]:
        """List configured providers."""
        available = []
        for name, cfg in self.providers.items():
            base_url = cfg.get("base_url", "")
            has_key = bool(cfg.get("api_key") or self._get_api_key(name))
            if name == "ollama" or (base_url and "11434" in base_url):
                available.append(f"{name} (local, free)")
            elif self.privacy_mode:
                available.append(f"{name} (disabled - privacy mode)")
            elif has_key:
                available.append(f"{name} (cloud, ready)")
            else:
                available.append(f"{name} (cloud, no key)")
        return available
