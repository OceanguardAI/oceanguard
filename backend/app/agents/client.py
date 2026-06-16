"""Gemini client singleton for either API-key or Google Cloud auth."""
from __future__ import annotations

from typing import Any

from app.core.config import settings

_client: Any | None = None
_client_signature: tuple[str, str, str] | None = None


def genai_importable() -> bool:
    try:
        from google import genai  # noqa: F401
    except ImportError:
        return False
    return True


def gemini_provider_mode() -> str:
    return "gcp" if (settings.gemini_use_gcp or settings.google_genai_use_vertexai) else "api_key"


def gemini_provider_enabled() -> bool:
    if settings.gemini_use_gcp or settings.google_genai_use_vertexai:
        return bool(settings.google_cloud_project and settings.google_cloud_location)
    return bool(settings.gemini_api_key)


def get_client() -> Any | None:
    global _client, _client_signature

    mode = gemini_provider_mode()
    signature = (
        mode,
        settings.google_cloud_project if mode == "gcp" else settings.gemini_api_key,
        settings.google_cloud_location if mode == "gcp" else "",
    )

    if _client is not None and _client_signature == signature:
        return _client

    if not gemini_provider_enabled():
        _client = None
        _client_signature = None
        return None
    if not genai_importable():
        _client = None
        _client_signature = None
        return None

    from google import genai

    if mode == "gcp":
        _client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project,
            location=settings.google_cloud_location,
        )
    else:
        _client = genai.Client(api_key=settings.gemini_api_key)

    _client_signature = signature
    return _client
