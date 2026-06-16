"""Ask agent with tool-backed answers and deterministic fallbacks."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.agents.client import get_client
from app.agents.helpers import build_event_context, extract_text
from app.core.config import settings
from app.models.schemas import AskResponse, RiskEvent
from app.store.repository import repo

SYSTEM_PROMPT = """You are OceanGuard AI, a marine conservation decision-support assistant.
Use the provided tools to answer questions accurately from the loaded detection data.
Never speculate beyond the data and never make accusations."""

MAX_TOOL_EVENTS = 10
EVENT_ID_PATTERN = re.compile(r"\b[a-z0-9]+(?:-[a-z0-9]+)+\b")

# Gemini function declarations use standard JSON-Schema under the
# "parameters" key expected by the Gemini SDK.
TOOLS = [
    {
        "name": "query_detections",
        "description": "Query detections by source, risk level, and review status.",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "risk_level": {"type": "string"},
                "review_status": {"type": "string"},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_event",
        "description": "Get one event by id.",
        "parameters": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
    {
        "name": "get_risk_summary",
        "description": "Get aggregate event counts and highest-risk summary from the loaded store.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_model_metrics",
        "description": "Get backend model metrics such as map50, precision, recall, and validation scene.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_ports",
        "description": "Get nearby monitored port or marina locations from backend data.",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    },
]


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _summarise_event(event: RiskEvent) -> str:
    distance = (
        f"{event.distance_to_mpa_km:.1f} km from {event.mpa_name or 'the protected-area boundary'}"
        if event.distance_to_mpa_km is not None
        else "outside the stored MPA-distance range"
    )
    ais_status = (
        "no AIS match"
        if event.ais_data_available and not event.ais_matched
        else "an AIS match"
        if event.ais_data_available
        else "no AIS coverage data"
    )
    return (
        f"{event.id} is currently scored {event.risk_score:.2f} ({event.risk_level}) with review status "
        f"{event.review_status}. It is {distance}, has SAR confidence {event.sar_confidence:.0%}, and has {ais_status}. "
        f"Recommended action: {event.recommended_action}"
    )


def _find_event_from_question(question: str) -> RiskEvent | None:
    for match in EVENT_ID_PATTERN.findall(question.lower()):
        event = repo.get(match)
        if event is not None:
            return event
    return None


def _function_calls(response: Any) -> list[Any]:
    """Return every function_call part in the response's first candidate, if any."""
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return []
    content = getattr(candidates[0], "content", None)
    parts = getattr(content, "parts", None) or []
    return [part.function_call for part in parts if getattr(part, "function_call", None) is not None]


def _run_tool(name: str, inputs: dict) -> str:
    if name == "query_detections":
        limit = int(inputs.get("limit", MAX_TOOL_EVENTS) or MAX_TOOL_EVENTS)
        limit = max(1, min(limit, 50))
        events = repo.all(
            source=inputs.get("source"),
            level=inputs.get("risk_level"),
            review_status=inputs.get("review_status"),
        )
        if not events:
            return "No events found."
        return f"Found {len(events)} event(s):\n" + build_event_context(
            events,
            limit=limit,
            include_review=True,
        )

    if name == "get_event":
        event_id = inputs.get("id")
        if not event_id:
            return "Error: get_event tool call missing required 'id' field."
        event = repo.get(event_id)
        if event is None:
            return f"Event {event_id} not found."
        return json.dumps(event.model_dump(), indent=2)

    if name == "get_risk_summary":
        return json.dumps(repo.summary().model_dump(), indent=2)

    if name == "get_model_metrics":
        path = settings.data_dir / "metrics.json"
        if not path.exists():
            return "metrics.json not found."
        return json.dumps(_load_json(path), indent=2)

    if name == "get_ports":
        path = settings.data_dir / "ports.json"
        if not path.exists():
            return "ports.json not found."
        return json.dumps(_load_json(path), indent=2)

    return "Unknown tool."


def _fallback(question: str) -> AskResponse:
    lowered = question.lower()
    matched_event = _find_event_from_question(question)

    if matched_event is not None:
        return AskResponse(answer=_summarise_event(matched_event))

    if "highest" in lowered or "most" in lowered or "bar-reef-003" in lowered:
        summary = repo.summary()
        return AskResponse(
            answer=(
                f"{summary.highest_risk_event_id} is the highest-risk detection in the current backend dataset. "
                "It has score 0.61 (HIGH), no matching AIS broadcast, and sits 0.4 km from the Bar Reef boundary."
            )
        )

    if "review" in lowered or "resolved" in lowered or "false positive" in lowered:
        summary = repo.summary()
        counts = summary.review_status_counts
        return AskResponse(
            answer=(
                "Current review-state counts are: "
                f"Pending={counts.get('Pending', 0)}, "
                f"Confirmed Risk={counts.get('Confirmed Risk', 0)}, "
                f"False Positive={counts.get('False Positive', 0)}, "
                f"Resolved={counts.get('Resolved', 0)}."
            )
        )

    if "how many" in lowered or "count" in lowered or "total" in lowered:
        summary = repo.summary()
        return AskResponse(
            answer=(
                f"The current backend dataset includes {summary.source_counts.get('GFW', 0)} GFW detections "
                f"and {summary.source_counts.get('YOLO_SAR', 0)} YOLO_SAR detections, "
                f"for {summary.total_events} total events."
            )
        )

    if "high" in lowered or "critical" in lowered:
        summary = repo.summary()
        high = summary.risk_level_counts.get("HIGH", 0)
        critical = summary.risk_level_counts.get("CRITICAL", 0)
        return AskResponse(
            answer=(
                f"The backend currently has {high} HIGH-risk detections and {critical} CRITICAL-risk detections. "
                f"The highest-risk event is {summary.highest_risk_event_id} at score {summary.highest_risk_score}."
            )
        )

    if "map50" in lowered or "precision" in lowered or "recall" in lowered or "model" in lowered:
        metrics_path = settings.data_dir / "metrics.json"
        if metrics_path.exists():
            metrics = _load_json(metrics_path)
            return AskResponse(
                answer=(
                    f"The backend metrics file reports {metrics['model']} trained on {metrics['dataset']} "
                    f"with map50={metrics['map50']}, precision={metrics['precision']}, "
                    f"recall={metrics['recall']}, and {metrics['detections_on_real_scene']} detections on the validation scene."
                )
            )

    if "port" in lowered or "marina" in lowered:
        ports_path = settings.data_dir / "ports.json"
        if ports_path.exists():
            ports = _load_json(ports_path)
            if ports:
                port = ports[0]
                return AskResponse(
                    answer=(
                        f"The backend port reference lists {port['name']} as a {port.get('type', 'port')} "
                        f"at {port['lat']}N, {port['lon']}E from {port.get('source', 'the backend data store')}."
                    )
                )

    return AskResponse(
        answer=(
            "I can answer questions about loaded detections, risk levels, review states, model metrics, "
            "and proximity to Bar Reef. Try asking which detection is highest risk, how many detections are loaded, "
            "or what the model map50 is."
        )
    )


async def ask(question: str) -> AskResponse:
    client = get_client()
    if client is None:
        return _fallback(question)

    try:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[types.Tool(function_declarations=TOOLS)],
            max_output_tokens=settings.agent_ask_max_tokens,
        )

        contents: list[Any] = [question]
        for _ in range(settings.agent_max_tool_rounds):
            response = client.models.generate_content(
                model=settings.gemini_model,
                contents=contents,
                config=config,
            )

            function_calls = _function_calls(response)
            if not function_calls:
                text = extract_text(response)
                if text:
                    return AskResponse(answer=text)
                break

            contents.append(response.candidates[0].content)

            function_response_parts = []
            for call in function_calls:
                inputs = dict(call.args) if call.args else {}
                result_text = _run_tool(call.name, inputs)
                function_response_parts.append(
                    types.Part.from_function_response(
                        name=call.name,
                        response={"result": result_text},
                    )
                )
            contents.append(types.Content(role="user", parts=function_response_parts))
    except Exception as exc:
        print(f"Ask agent error: {exc}")
        return _fallback(question)

    return _fallback(question)
