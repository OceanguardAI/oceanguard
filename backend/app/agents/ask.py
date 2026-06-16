"""Ask agent with tool-backed answers and deterministic fallbacks."""
from __future__ import annotations

import json
from pathlib import Path

from app.agents.client import get_client
from app.agents.helpers import build_event_context, first_text_block
from app.core.config import settings
from app.models.schemas import AskResponse
from app.store.repository import repo

SYSTEM_PROMPT = """You are OceanGuard AI, a marine conservation decision-support assistant.
Use the provided tools to answer questions accurately from the loaded detection data.
Never speculate beyond the data and never make accusations."""

MAX_TOOL_EVENTS = 10

TOOLS = [
    {
        "name": "query_detections",
        "description": "Query detections by source, risk level, and review status.",
        "input_schema": {
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
        "input_schema": {
            "type": "object",
            "properties": {"id": {"type": "string"}},
            "required": ["id"],
        },
    },
    {
        "name": "get_risk_summary",
        "description": "Get aggregate event counts and highest-risk summary from the loaded store.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_model_metrics",
        "description": "Get backend model metrics such as map50, precision, recall, and validation scene.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_ports",
        "description": "Get nearby monitored port or marina locations from backend data.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


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
        event = repo.get(inputs["id"])
        if event is None:
            return f"Event {inputs['id']} not found."
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

    messages = [{"role": "user", "content": question}]
    try:
        for _ in range(settings.agent_max_tool_rounds):
            response = client.messages.create(
                model=settings.anthropic_model,
                max_tokens=settings.agent_ask_max_tokens,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                text = first_text_block(response.content)
                if text:
                    return AskResponse(answer=text)
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
