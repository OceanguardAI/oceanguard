"""Shared-secret protection for routes that change or refresh server state."""
from __future__ import annotations

import hmac

from fastapi import Header, HTTPException

from app.core.config import settings


def write_protection_enabled() -> bool:
    return bool(settings.admin_api_key.strip())


def require_admin(x_api_key: str | None = Header(default=None)) -> None:
    """Require `X-API-Key` to match ADMIN_API_KEY when one is configured.

    With no key configured the routes stay open so local development and the
    offline pipeline keep working; /ingest/status reports `write_protected`
    so an unprotected deployment is visible.
    """
    expected = settings.admin_api_key.strip()
    if not expected:
        return
    if x_api_key is None or not hmac.compare_digest(x_api_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Valid X-API-Key required.")
