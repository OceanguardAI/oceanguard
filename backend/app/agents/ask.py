"""Ask agent: agentic loop with tool use."""
from __future__ import annotations
import json
from app.agents.client import get_client
from app.models.schemas import AskResponse
from app.store.repository import repo


SYSTEM_PROMPT = """You are OceanGuard AI, a marine conservation decision-support assistant.
You help conservation officers understand vessel detection data.
You have tools to query detection data. Use them to give accurate, factual answers.
Never speculate beyond the data. Never make accusations. Never identify individuals.
Answer in 2-4 sentences. If uncertain, say so."""

TOOLS = [
    {
        "name": "query_detections",
        "description": "Query risk events. Use source='GFW' for dark vessel detections near Bar Reef, 'YOLO_SAR' for xView3 model validation detections.",
        "input_schema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Filter by source: 'GFW' or 'YOLO_SAR'",
                },
                "risk_level": {
                    "type": "string",
                    "description": "Filter by risk level: LOW, MEDIUM, HIGH, CRITICAL",
                },
            },
        },
    },
    {
        "name": "get_event",
        "description": "Get full details for a specific detection by ID (e.g. 'bar-reef-003').",
        "input_schema": {
            "type": "object",
            "properties": {
                "id": {
                    "type": "string",
                    "description": "The event ID, e.g. 'bar-reef-003'",
                }
            },
            "required": ["id"],
        },
    },
]


def _run_tool(name: str, inputs: dict) -> str:
    """Execute a tool call and return the result as a string."""
    if name == "query_detections":
        events = repo.all(
            source=inputs.get("source"),
            level=inputs.get("risk_level"),
        )
        if not events:
            return "No events found matching the filter."
        lines = [
            f"{e.id}: {e.risk_level} ({e.risk_score:.2f}), "
            f"{'near_mpa' if e.near_mpa else 'not near mpa'}, "
            f"dist={e.distance_to_mpa_km} km"
            for e in events[:10]
        ]
        return f"Found {len(events)} event(s):\n" + "\n".join(lines)

    elif name == "get_event":
        event = repo.get(inputs["id"])
        if event is None:
            return f"Event '{inputs['id']}' not found."
        return json.dumps(event.model_dump(), indent=2)

    return f"Unknown tool: {name}"


def _fallback(question: str) -> AskResponse:
    """Keyword-based fallback when no API key is available."""
    q = question.lower()

    if "bar-reef-003" in q or "highest" in q or "most" in q:
        return AskResponse(
            answer=(
                "bar-reef-003 is the highest-risk detection at 8.51N 79.68E. "
                "It is 0.4 km from Bar Reef Marine Sanctuary with a risk score of 0.61 (HIGH) "
                "and no matching AIS broadcast. A conservation officer should verify this detection."
            )
        )
    if "dark vessel" in q or "what is" in q or "what does" in q:
        return AskResponse(
            answer=(
                "A dark vessel is a ship that has disabled or is not broadcasting its AIS transponder. "
                "SAR satellites detect all vessels regardless of AIS status. "
                "OceanGuard cross-references SAR detections with AIS data — unmatched detections are flagged for review."
            )
        )
    if "mpa" in q or "bar reef" in q:
        return AskResponse(
            answer=(
                "Bar Reef Marine Sanctuary is a protected marine area off the northwest coast of Sri Lanka (WDPA ID 4783). "
                "Any vessel detected within 5 km is flagged as near-MPA. "
                "bar-reef-003 is 0.4 km from its boundary — the closest detection in this dataset."
            )
        )
    if "how many" in q or "total" in q or "count" in q:
        gfw  = repo.all(source="GFW")
        high = [e for e in gfw if e.risk_level in ("HIGH", "CRITICAL")]
        return AskResponse(
            answer=(
                f"There are {len(gfw)} GFW dark-vessel detections near Bar Reef Marine Sanctuary. "
                f"{len(high)} are rated HIGH or CRITICAL risk. "
                "bar-reef-003 is the only one within 1 km of the MPA boundary."
            )
        )

    return AskResponse(
        answer=(
            "I can help with questions about the dark vessel detections near Bar Reef Marine Sanctuary. "
            "Try asking about specific detections (e.g. bar-reef-003), risk levels, or distances to the MPA."
        )
    )


async def ask(question: str) -> AskResponse:
    client = get_client()
    if client is None:
        return _fallback(question)

    messages = [{"role": "user", "content": question}]

    try:
        # Agentic loop: Claude calls tools until it produces a final text answer
        for _ in range(5):  # max 5 tool rounds
            response = client.messages.create(
                model="claude-opus-4-8",
                max_tokens=800,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if hasattr(block, "text"):
                        return AskResponse(answer=block.text.strip())
                break

            if response.stop_reason == "tool_use":
                assistant_content = response.content
                tool_results = []
                for block in assistant_content:
                    if block.type == "tool_use":
                        result_text = _run_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result_text,
                        })
                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({"role": "user", "content": tool_results})
            else:
                break

        return _fallback(question)

    except Exception as e:
        print(f"Ask agent error: {e}")
        return _fallback(question)
