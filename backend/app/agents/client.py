"""Anthropic client singleton. Returns None when no API key is configured."""
from __future__ import annotations

from typing import Any

from app.core.config import settings

_client: Any | None = None
_client_api_key: str = ""


def anthropic_importable() -> bool:
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def get_client() -> Any | None:
    global _client, _client_api_key
    if _client is not None and _client_api_key == settings.anthropic_api_key:
        return _client
    if not settings.anthropic_api_key:
        _client = None
        _client_api_key = ""
        return None
    if not anthropic_importable():
        _client = None
        _client_api_key = ""
        return None
    import anthropic

    _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    _client_api_key = settings.anthropic_api_key
    return _client
