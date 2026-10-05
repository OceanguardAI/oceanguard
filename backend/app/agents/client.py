"""Groq chat-completions client shared by every agent."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings

_client: Any | None = None
_client_key: str | None = None


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict[str, Any]


@dataclass
class Completion:
    text: str
    truncated: bool
    tool_calls: list[ToolCall] = field(default_factory=list)
    # Assistant turn in chat format, to append before sending tool results back.
    message: dict[str, Any] = field(default_factory=dict)


def groq_importable() -> bool:
    try:
        import groq  # noqa: F401
    except ImportError:
        return False
    return True


def groq_provider_enabled() -> bool:
    return bool(settings.groq_api_key)


def get_client() -> Any | None:
    global _client, _client_key

    if not groq_provider_enabled() or not groq_importable():
        _client = _client_key = None
        return None
    if _client is None or _client_key != settings.groq_api_key:
        from groq import AsyncGroq

        _client = AsyncGroq(api_key=settings.groq_api_key, timeout=settings.groq_timeout_s, max_retries=1)
        _client_key = settings.groq_api_key
    return _client


async def complete(
    client: Any,
    *,
    system: str,
    messages: list[dict[str, Any]],
    max_tokens: int,
    tools: list[dict[str, Any]] | None = None,
    json_object: bool = False,
) -> Completion:
    """One chat completion, normalised so callers never touch the SDK shape."""
    kwargs: dict[str, Any] = {
        "model": settings.groq_model,
        "messages": [{"role": "system", "content": system}, *messages],
        "max_tokens": max_tokens,
    }
    if settings.groq_reasoning_effort:
        kwargs["reasoning_effort"] = settings.groq_reasoning_effort
    if tools:
        kwargs["tools"] = tools
    if json_object:
        kwargs["response_format"] = {"type": "json_object"}

    choice = (await client.chat.completions.create(**kwargs)).choices[0]
    message = choice.message
    raw_calls = message.tool_calls or []
    text = (message.content or "").strip()

    assistant: dict[str, Any] = {"role": "assistant", "content": message.content or ""}
    if raw_calls:
        assistant["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.function.name, "arguments": call.function.arguments or "{}"},
            }
            for call in raw_calls
        ]
    return Completion(
        text=text,
        truncated=choice.finish_reason == "length",
        tool_calls=[
            ToolCall(call.id, call.function.name, json.loads(call.function.arguments or "{}"))
            for call in raw_calls
        ],
        message=assistant,
    )
