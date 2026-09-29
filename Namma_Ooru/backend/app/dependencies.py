"""Dependency providers used by FastAPI routers."""

from __future__ import annotations

from functools import lru_cache

from app.ai import AIProvider, LocalMockAIProvider


@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    """Supply the deterministic local provider until a runtime provider is configured."""
    return LocalMockAIProvider()
