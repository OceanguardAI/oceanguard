"""Anthropic client singleton. Returns None when no API key is configured."""
from __future__ import annotations

from typing import Any

from app.core.config import settings

_client: Any | None = None


def get_client() -> Any | None:
    global _client
    if _client is not None:
        return _client
    if not settings.anthropic_api_key:
        return None
    try:
        import anthropic
    except ImportError:
        return None

    _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client
