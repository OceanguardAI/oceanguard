from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

from app.agents import client


def test_provider_helpers_default_to_api_key_mode() -> None:
    original_use_gcp = client.settings.gemini_use_gcp
    original_vertex_flag = client.settings.google_genai_use_vertexai
    original_api_key = client.settings.gemini_api_key
    try:
        client.settings.gemini_use_gcp = False
        client.settings.google_genai_use_vertexai = False
        client.settings.gemini_api_key = ""

        assert client.gemini_provider_mode() == "api_key"
        assert client.gemini_provider_enabled() is False

        client.settings.gemini_api_key = "test-key"
        assert client.gemini_provider_enabled() is True
    finally:
        client.settings.gemini_use_gcp = original_use_gcp
        client.settings.google_genai_use_vertexai = original_vertex_flag
        client.settings.gemini_api_key = original_api_key


def test_get_client_builds_vertex_client_when_gcp_mode_enabled(monkeypatch) -> None:
    original_use_gcp = client.settings.gemini_use_gcp
    original_vertex_flag = client.settings.google_genai_use_vertexai
    original_project = client.settings.google_cloud_project
    original_location = client.settings.google_cloud_location
    original_client = client._client
    original_signature = client._client_signature

    fake_google = ModuleType("google")
    fake_google.genai = SimpleNamespace(
        Client=lambda **kwargs: SimpleNamespace(kind="client", kwargs=kwargs)
    )

    try:
        client.settings.gemini_use_gcp = True
        client.settings.google_genai_use_vertexai = False
        client.settings.google_cloud_project = "oceanguard-test"
        client.settings.google_cloud_location = "global"
        client._client = None
        client._client_signature = None

        monkeypatch.setattr(client, "genai_importable", lambda: True)
        monkeypatch.setitem(sys.modules, "google", fake_google)

        built = client.get_client()

        assert built.kind == "client"
        assert built.kwargs["vertexai"] is True
        assert built.kwargs["project"] == "oceanguard-test"
        assert built.kwargs["location"] == "global"
        assert client.gemini_provider_mode() == "gcp"
        assert client.gemini_provider_enabled() is True
    finally:
        client.settings.gemini_use_gcp = original_use_gcp
        client.settings.google_genai_use_vertexai = original_vertex_flag
        client.settings.google_cloud_project = original_project
        client.settings.google_cloud_location = original_location
        client._client = original_client
        client._client_signature = original_signature
