"""Fake Groq SDK client shaped like AsyncGroq's chat.completions.create."""
from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any


def reply(text: str | None = None, *, finish: str = "stop", tool_calls: list[tuple] | None = None):
    """One chat completion; tool_calls are (id, name, args) tuples."""
    calls = [
        SimpleNamespace(id=cid, function=SimpleNamespace(name=name, arguments=json.dumps(args)))
        for cid, name, args in tool_calls or []
    ]
    message = SimpleNamespace(content=text, tool_calls=calls or None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason=finish)])


class FakeGroq:
    """Returns queued replies in order and records every request."""

    def __init__(self, *replies: Any) -> None:
        self._replies = list(replies)
        self.requests: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs: Any):
        self.requests.append(kwargs)
        return self._replies.pop(0) if len(self._replies) > 1 else self._replies[0]
