"""OpenRouter adapter implementing LLMProviderPort with EU routing and offline fallback."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
import httpx

from ports.base import LLMProviderPort
from utils.config import load_config, get_secret


class OpenRouterAdapter(LLMProviderPort):
    """Adapter for querying OpenRouter API models with EU sovereignty routing."""

    def __init__(self, api_key: Optional[str] = None):
        cfg = load_config()
        self.model = cfg.get("llm", {}).get("model", "mistralai/mistral-large-2407")
        self.base_url = cfg.get("llm", {}).get("base_url", "https://openrouter.ai/api/v1")
        self.timeout = float(cfg.get("llm", {}).get("timeout_seconds", 45))
        self.provider_routing = cfg.get("llm", {}).get("provider_routing", {})

        # Private secret strictly from .env
        self.api_key = api_key or get_secret("OPENROUTER_API_KEY")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.generate_chat(messages, temperature=temperature, max_tokens=max_tokens)

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        if not self.api_key or self.api_key.strip() in ("", "placeholder_key", "sk-or-your-key-here"):
            raise ValueError(
                "OpenRouter API key is not configured. Please enter a valid OPENROUTER_API_KEY in the sidebar or in .env."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key.strip()}",
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "Aethelgard Infra-GraphRAG",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # EU provider routing controls from config.json
        if self.provider_routing:
            payload["provider"] = self.provider_routing

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                if resp.status_code != 200:
                    err_msg = resp.text
                    try:
                        err_json = resp.json()
                        err_msg = err_json.get("error", {}).get("message", resp.text)
                    except Exception:
                        pass
                    raise RuntimeError(f"OpenRouter API error (HTTP {resp.status_code}): {err_msg}")

                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except httpx.RequestError as e:
            raise RuntimeError(f"OpenRouter network connection error: {str(e)}")

    @staticmethod
    def validate_api_key(api_key: str, base_url: str = "https://openrouter.ai/api/v1") -> tuple[bool, str]:
        """Validate OpenRouter API key against the /auth/key endpoint."""
        clean_key = (api_key or "").strip()
        if not clean_key or clean_key in ("placeholder_key", "sk-or-your-key-here"):
            return False, "API key is missing or empty."

        try:
            headers = {"Authorization": f"Bearer {clean_key}"}
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(f"{base_url}/auth/key", headers=headers)
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    label = data.get("label") or "Default Key"
                    limit = data.get("limit")
                    usage = data.get("usage", 0)
                    limit_str = f"${limit}" if limit else "Unlimited"
                    return True, f"Valid OpenRouter Key ({label} | Usage: ${usage:.2f} / {limit_str})"
                elif resp.status_code == 401:
                    return False, "Invalid API key (HTTP 401 Unauthorized)."
                else:
                    return False, f"OpenRouter check failed (HTTP {resp.status_code}): {resp.text[:100]}"
        except Exception as e:
            return False, f"Connection to OpenRouter failed: {str(e)}"

