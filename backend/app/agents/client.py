"""Singleton Anthropic client. Returns None if API key is missing."""
from __future__ import annotations
import anthropic
from app.core.config import settings

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic | None:
    global _client
    if _client is not None:
        return _client
    if not settings.anthropic_api_key:
        return None
    _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client
