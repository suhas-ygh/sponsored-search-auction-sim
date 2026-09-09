"""LLM client abstraction.

Provider-agnostic and dependency-free (stdlib urllib only). Auto-detects
credentials from the environment:

    ANTHROPIC_API_KEY            -> Anthropic Messages API
    OPENAI_API_KEY               -> OpenAI-compatible chat completions
    OPENAI_BASE_URL              -> custom gateway (OpenRouter, etc.)
    ANTHROPIC_MODEL / OPENAI_MODEL -> model override

Use FakeLLMClient for tests and evals.
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Protocol


class LLMClient(Protocol):
    def complete(self, messages: list[dict], system: str = "",
                 max_tokens: int = 1024) -> str:
        """messages: [{"role": "user"|"assistant", "content": str}]. Returns text."""


class FakeLLMClient:
    """Deterministic script for tests/evals. Pops one reply per call."""

    def __init__(self, replies: list[str]):
        self._replies = list(replies)
        self.calls: list[dict] = []

    def complete(self, messages: list[dict], system: str = "",
                 max_tokens: int = 1024) -> str:
        self.calls.append({"messages": messages, "system": system})
        if not self._replies:
            raise AssertionError("FakeLLMClient ran out of scripted replies")
        return self._replies.pop(0)


def _post_json(url: str, headers: dict, payload: dict, timeout: int = 60) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


class AnthropicClient:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        self.api_key = api_key or os.environ["ANTHROPIC_API_KEY"]
        self.model = model or os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5")

    def complete(self, messages: list[dict], system: str = "",
                 max_tokens: int = 1024) -> str:
        data = _post_json(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
            {"model": self.model, "max_tokens": max_tokens,
             "system": system, "messages": messages},
        )
        return "".join(
            b.get("text", "") for b in data.get("content", [])
            if b.get("type") == "text"
        )


class OpenAIClient:
    """Also serves any OpenAI-compatible gateway via OPENAI_BASE_URL."""

    def __init__(self, api_key: str | None = None, model: str | None = None,
                 base_url: str | None = None):
        self.api_key = api_key or os.environ["OPENAI_API_KEY"]
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-5-mini")
        self.base_url = (base_url or os.environ.get(
            "OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")

    def complete(self, messages: list[dict], system: str = "",
                 max_tokens: int = 1024) -> str:
        msgs = ([{"role": "system", "content": system}] if system else []) + messages
        data = _post_json(
            f"{self.base_url}/chat/completions",
            {"Authorization": f"Bearer {self.api_key}"},
            {"model": self.model, "max_tokens": max_tokens, "messages": msgs},
        )
        return data["choices"][0]["message"]["content"] or ""


def get_client() -> LLMClient:
    """Pick a provider from the environment. Raises a helpful error if none."""
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicClient()
    if os.environ.get("OPENAI_API_KEY"):
        return OpenAIClient()
    raise RuntimeError(
        "No LLM API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY "
        "(optional overrides: ANTHROPIC_MODEL, OPENAI_MODEL, OPENAI_BASE_URL)."
    )
