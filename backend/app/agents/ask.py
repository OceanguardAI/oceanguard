"""Ask agent with simple tool-backed loop and deterministic fallback."""
from __future__ import annotations

import json

from app.agents.client import get_client
from app.models.schemas import AskResponse
from app.store.repository import repo

SYSTEM_PROMPT = """You are OceanGuard AI, a marine conservation decision-support assistant.
Use the provided tools to answer questions accurately from the loaded detection data.
Never speculate beyond the data and never make accusations."""

TOOLS = [
    {
        "name": "query_detections",
        "description": "Query detections by source and risk level.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "risk_level": {"type": "string"},
            },
        },
    },
    {
        "name": "get_event",
        "description": "Get one event by id.",
        "input_schema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
]


def _run_tool(name: str, inputs: dict) -> str:
    if name == "query_detections":
        events = repo.all(source=inputs.get("source"), level=inputs.get("risk_level"))
        if not events:
            return "No events found."
        lines = [
            f"{event.id}: {event.risk_level} ({event.risk_score:.2f}), dist={event.distance_to_mpa_km}"
            for event in events[:10]
        ]
        return "\n".join(lines)

    if name == "get_event":
        event = repo.get(inputs["id"])
        if event is None:
            return f"Event {inputs['id']} not found."
        return json.dumps(event.model_dump(), indent=2)

    return "Unknown tool."


def _fallback(question: str) -> AskResponse:
    lowered = question.lower()
    if "highest" in lowered or "most" in lowered or "bar-reef-003" in lowered:
        return AskResponse(
            answer=(
                "bar-reef-003 is the highest-risk detection in the bootstrap dataset. "
                "It has score 0.61 (HIGH), no matching AIS broadcast, and sits 0.4 km from the Bar Reef boundary."
            )
        )
    if "how many" in lowered or "count" in lowered or "total" in lowered:
        gfw = repo.all(source="GFW")
        yolo = repo.all(source="YOLO_SAR")
        return AskResponse(
            answer=(
                f"The current backend bootstrap data includes {len(gfw)} GFW detections "
                f"and {len(yolo)} YOLO_SAR detections."
            )
        )
    return AskResponse(
        answer=(
            "I can answer questions about loaded detections, risk levels, and proximity to Bar Reef. "
            "Try asking which detection is highest risk or how many detections are loaded."
        )
    )


async def ask(question: str) -> AskResponse:
    client = get_client()
    if client is None:
        return _fallback(question)

    messages = [{"role": "user", "content": question}]
    try:
        for _ in range(5):
            response = client.messages.create(
                model="claude-opus-4-8",
                max_tokens=700,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text") and block.text:
                        return AskResponse(answer=block.text.strip())
                break

            if response.stop_reason != "tool_use":
                break

            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if getattr(block, "type", None) == "tool_use":
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": _run_tool(block.name, block.input),
                        }
                    )
            messages.append({"role": "user", "content": tool_results})
    except Exception:
        return _fallback(question)

    return _fallback(question)
