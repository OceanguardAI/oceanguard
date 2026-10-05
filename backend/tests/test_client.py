from __future__ import annotations

import asyncio
import sys
from types import ModuleType, SimpleNamespace

import pytest

from app.agents import client
from tests.groq_fakes import FakeGroq, reply


@pytest.fixture(autouse=True)
def _reset_client(monkeypatch):
    monkeypatch.setattr(client, "_client", None)
    monkeypatch.setattr(client, "_client_key", None)


def test_provider_is_enabled_only_with_an_api_key(monkeypatch) -> None:
    monkeypatch.setattr(client.settings, "groq_api_key", "")
    assert client.groq_provider_enabled() is False
    assert client.get_client() is None

    monkeypatch.setattr(client.settings, "groq_api_key", "test-key")
    assert client.groq_provider_enabled() is True


def test_get_client_builds_and_caches_an_async_client(monkeypatch) -> None:
    built: list[dict] = []
    fake_groq = ModuleType("groq")
    fake_groq.AsyncGroq = lambda **kwargs: built.append(kwargs) or SimpleNamespace(kind="client")
    monkeypatch.setitem(sys.modules, "groq", fake_groq)
    monkeypatch.setattr(client.settings, "groq_api_key", "test-key")

    first = client.get_client()
    assert first is client.get_client()
    assert built == [{"api_key": "test-key", "timeout": client.settings.groq_timeout_s, "max_retries": 1}]

    monkeypatch.setattr(client.settings, "groq_api_key", "rotated-key")
    assert client.get_client() is not first


def test_complete_sends_system_prompt_and_options(monkeypatch) -> None:
    monkeypatch.setattr(client.settings, "groq_model", "test-model")
    fake = FakeGroq(reply(" Hello. "))

    result = asyncio.run(
        client.complete(
            fake,
            system="be brief",
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=50,
            json_object=True,
        )
    )

    request = fake.requests[0]
    assert request["model"] == "test-model"
    assert request["max_tokens"] == 50
    assert request["response_format"] == {"type": "json_object"}
    assert request["messages"][0] == {"role": "system", "content": "be brief"}
    assert "tools" not in request
    assert (result.text, result.truncated, result.tool_calls) == ("Hello.", False, [])


def test_complete_normalises_tool_calls_and_truncation() -> None:
    fake = FakeGroq(reply(None, finish="length", tool_calls=[("call_1", "get_event", {"id": "e-1"})]))

    result = asyncio.run(client.complete(fake, system="s", messages=[], max_tokens=5))

    assert result.truncated is True
    assert [(c.id, c.name, c.args) for c in result.tool_calls] == [("call_1", "get_event", {"id": "e-1"})]
    assert result.message["tool_calls"][0]["function"] == {"name": "get_event", "arguments": '{"id": "e-1"}'}
