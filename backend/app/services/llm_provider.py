"""Provider-independent LLM interface.

Every LLM-touching feature (ambiguous-case classification adjudication,
RAG answer synthesis) talks to this interface, never to a concrete SDK.
MockLLMProvider keeps DEMO_MODE fully functional with zero network calls;
OpenAICompatibleLLMProvider talks to any OpenAI-compatible /chat/completions
endpoint when LLM_MODE is actually configured (spec sections 3-4).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache

from app.core.config import get_settings


class BaseLLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def complete(self, system: str, user: str, max_tokens: int = 512) -> str: ...


class MockLLMProvider(BaseLLMProvider):
    """DEMO_MODE stand-in. HybridClassifier never actually calls this
    (LLM adjudication is skipped entirely when LLM_MODE is off — see
    docs/decisions.md ADR on cost-aware routing), but it keeps the
    interface non-null for tests and for any caller that doesn't
    special-case demo mode itself."""

    name = "mock"

    def complete(self, system: str, user: str, max_tokens: int = 512) -> str:
        return '{"ontology_id": null, "confidence": 0.0, "reason": "LLM_MODE is disabled; no adjudication performed"}'


class OpenAICompatibleLLMProvider(BaseLLMProvider):
    name = "openai_compatible"

    def __init__(self, api_base: str, api_key: str, model: str):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model

    def complete(self, system: str, user: str, max_tokens: int = 512) -> str:
        import httpx

        resp = httpx.post(
            f"{self.api_base}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "max_tokens": max_tokens,
                "temperature": 0,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


@lru_cache
def get_llm_provider() -> BaseLLMProvider:
    settings = get_settings()
    if settings.effective_llm_mode:
        return OpenAICompatibleLLMProvider(settings.llm_api_base, settings.llm_api_key, settings.llm_model)
    return MockLLMProvider()
