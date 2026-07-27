"""
Kimi (Moonshot AI) LLM Adapter for PortAIOS

Provides an LLM adapter backed by the Kimi K2 model family, served through
Fireworks AI's OpenAI-compatible chat completions API. Plugs into
AgentExecutor's `llm` slot (kernel/agent_executor.py) to handle
natural-language requests that don't match a pattern-based intent.
"""

import os
import logging
from typing import Any, Dict, List, Optional

from kernel.env_loader import ensure_env_loaded
ensure_env_loaded()

logger = logging.getLogger("AIOS.KimiAgent")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    requests = None  # type: ignore[assignment]
    REQUESTS_AVAILABLE = False

DEFAULT_BASE_URL = "https://api.fireworks.ai/inference/v1"
DEFAULT_MODEL = "accounts/fireworks/models/kimi-k2p7-code"

SYSTEM_PROMPT = (
    "You are the reasoning backend for the PortAIOS agent. The agent already "
    "handles common OS tasks (files, apps, network, terminal) via pattern "
    "matching; you are only invoked when a user's request didn't match a "
    "known command. Answer directly and concisely — your reply is spoken "
    "aloud via TTS and shown in a small chat panel, so avoid markdown, code "
    "fences, and long explanations."
)


class KimiAgent:
    """LLM adapter backed by Moonshot's Kimi K2 model via Fireworks AI.

    Implements the `interpret(text, context) -> dict` contract expected by
    AgentExecutor's LLM fallback (see `_llm_fallback` in agent_executor.py).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: float = 30.0,
    ):
        if not REQUESTS_AVAILABLE:
            raise RuntimeError("The 'requests' package is required for KimiAgent")

        self.api_key = api_key or os.environ.get("KIMI_API_KEY")
        if not self.api_key:
            raise RuntimeError("KIMI_API_KEY is not set")

        self.base_url = (base_url or os.environ.get("BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.environ.get("KIMI_MODEL") or DEFAULT_MODEL
        self.timeout = timeout

        self.history: List[Dict[str, str]] = []
        self.max_history_turns = 6  # user+assistant pairs kept for context

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 1024, temperature: float = 0.3) -> str:
        """Send a chat-completion request to Kimi and return the reply text."""
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            json={
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    def interpret(self, text: str, context: str = "") -> Dict[str, Any]:
        """Interpret an utterance the pattern matcher couldn't handle.

        Returns {"summary": <reply text>}, per the AgentExecutor LLM
        fallback contract.
        """
        messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
        if context:
            messages.append({"role": "system", "content": context})
        messages.extend(self.history[-self.max_history_turns * 2:])
        messages.append({"role": "user", "content": text})

        reply = self.chat(messages)

        self.history.append({"role": "user", "content": text})
        self.history.append({"role": "assistant", "content": reply})
        del self.history[: max(0, len(self.history) - self.max_history_turns * 2)]

        return {"summary": reply}


def create_kimi_agent() -> Optional[KimiAgent]:
    """Factory used by onboarding_gui.py. Returns None if Kimi isn't configured
    so the caller can fall back to pattern-matching-only mode."""
    try:
        agent = KimiAgent()
        logger.info(f"Kimi agent ready (model={agent.model})")
        return agent
    except Exception as e:
        logger.info(f"Kimi agent not available: {e}")
        return None
