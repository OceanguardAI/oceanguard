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

# Static description of how the whole system works, so the agent can answer
# "how does X work" questions (risk scoring, data sources, the dashboard) — not
# just questions about individual detections. Kept in sync with the live scoring
# formula in services/gfw_ingest.py and the chip/model settings.
SYSTEM_KNOWLEDGE = """## How OceanGuard Works

### What it does
OceanGuard finds "dark vessels" — ships whose AIS transponder is off — near Marine
Protected Areas (MPAs). It combines an AIS-based global feed with our own satellite-radar
ship-detection model, then scores and explains each detection for a human officer to review.

### Data sources
- Global Fishing Watch (GFW) API — global SAR vessel detections. A radar hit GFW could not
  match to any AIS identity is the core "dark vessel" signal.
- Sentinel-1 radar (Copernicus / CDSE) — C-band VV backscatter imagery; ships show up as
  bright spots on dark water. Works through cloud, day or night.
- WDPA — World Database on Protected Areas; the marine protected-area boundaries.
- AISStream — live AIS broadcasts, used to confirm whether a contact is "dark".
- Ports — reference port/marina locations for context (distance from port).

### How the risk score is calculated
Each detection gets a transparent, deterministic score (0.00–0.99), built up from:
- 0.25 baseline — any SAR vessel detection.
- +0.20 — no matching AIS identity (a possible dark vessel).
- MPA proximity (the biggest factor):
    +0.45 if INSIDE a protected area,
    +0.30 if within 10 km of one,
    +0.15 if within 50 km.
- +0.05 — repeated detections at the same location.
The total is capped at 0.99. There is no black box — every point can be explained.

Risk levels come from the score:
- CRITICAL: score >= 0.80
- HIGH:     score >= 0.60
- MEDIUM:   score >= 0.45
- LOW:      below 0.45
Example: a dark vessel INSIDE an MPA scores 0.25 + 0.20 + 0.45 = 0.90 -> CRITICAL.

### MPA proximity terms
- "inside MPA" = the detection falls within a protected-area polygon (distance 0 km).
- "near MPA" = within 10 km of a boundary.
- distance_to_mpa_km = great-circle distance to the nearest protected area.

### Our detection model
- YOLO11n, fine-tuned on the HRSID SAR ship dataset (~3.5k images), mAP@50 0.838.
- Runs on demand on a fresh Sentinel-1 chip, fully independent of AIS — so it can find
  vessels the AIS-based feed missed. Officers run it as a single-point check or an
  "area sweep" that tiles a region and flags contacts with no AIS match.

### What the dashboard shows
- A world map with each detection as a dot coloured by risk (red CRITICAL, orange HIGH,
  amber MEDIUM, green LOW); protected areas are dashed teal outlines.
- Top KPIs: total detections, HIGH/CRITICAL count, count near/inside an MPA, pending review.
- Panels: Detections (the full queue), Briefing (a daily summary), Patrols (top targets).
- An Evidence Card per detection: the Sentinel-1 radar chip, AIS status, MPA proximity,
  recommended action, and an independent YOLO radar check.

### Responsible use
OceanGuard is decision support, not automatic accusation. Every output must be verified by
a human officer before any enforcement action.
"""


def _build_system_prompt() -> str:
    """Build a system prompt that embeds a live data snapshot so the agent can
    answer common questions without needing a tool round-trip."""
    summary = repo.summary()

    lines = [
        "You are OceanGuard AI, a marine conservation decision-support assistant.",
        "Answer questions accurately from the live detection data and the system",
        "description embedded below. Explain how the system works when asked",
        "(risk scoring, data sources, the model, the dashboard). Never speculate",
        "beyond what is given and never make accusations.",
        "",
        "Formatting rules (important):",
        "- Write in plain text only. Do NOT use Markdown: no asterisks (* or **),",
        "  no bold markers, no headings (#), no backticks, no italic underscores.",
        "- For bullet lists use a plain dash and space: '- item'. Never use * for bullets.",
        "- When listing detections, show at most 10 results. Always state the total",
        "  count first (e.g. '480 detections are near or inside an MPA.'), then list",
        "  the top 10 by risk score, then say 'Use the map to view the rest.'",
        "- Keep answers concise: 1 short paragraph or a brief list. No walls of text.",
        "",
        SYSTEM_KNOWLEDGE,
        "",
        f"## Live Dataset  ({summary.total_events} events)",
        (
            f"Risk levels — CRITICAL: {summary.risk_level_counts.get('CRITICAL', 0)}, "
            f"HIGH: {summary.risk_level_counts.get('HIGH', 0)}, "
            f"MEDIUM: {summary.risk_level_counts.get('MEDIUM', 0)}, "
            f"LOW: {summary.risk_level_counts.get('LOW', 0)}"
        ),
        f"Sources — {', '.join(f'{k}: {v}' for k, v in summary.source_counts.items())}",
        f"Near or inside MPA: {summary.near_mpa_count} events",
        f"Pending review: {summary.review_status_counts.get('Pending', 0)} events",
        "",
    ]

    # Full detection list — every event, sorted by risk score descending, so the
    # agent can answer questions about any detection without a tool round-trip.
    all_events = sorted(repo.all(), key=lambda e: e.risk_score, reverse=True)
    lines.append(f"## All Detections  ({len(all_events)} events)")
    lines.append(
        "Columns: id | risk | score | lat,lon | MPA proximity | AIS | source | review"
    )
    for e in all_events:
        if e.inside_mpa:
            mpa = f"INSIDE {e.mpa_name or 'MPA'}"
        elif e.near_mpa and e.distance_to_mpa_km is not None:
            mpa = f"{e.distance_to_mpa_km:.1f}km from {e.mpa_name or 'MPA'}"
        elif e.distance_to_mpa_km is not None:
            mpa = f"{e.distance_to_mpa_km:.1f}km from {e.mpa_name or 'MPA'}"
        else:
            mpa = "no-MPA-data"
        ais = (
            "no-AIS" if (e.ais_data_available and not e.ais_matched)
            else "matched" if e.ais_matched
            else "no-coverage"
        )
        lines.append(
            f"- {e.id} | {e.risk_level} | {e.risk_score:.2f} | "
            f"{e.lat:.3f},{e.lon:.3f} | {mpa} | {ais} | {e.source} | {e.review_status}"
        )
    lines.append("")
    lines.append(
        "The list above is the COMPLETE current dataset — every detection is shown. "
        "Filter it directly to answer questions (e.g. rows marked INSIDE or 'km from' are near/inside MPAs). "
        "Use the tools only for full per-event detail (why_flagged, recommended_action, ports, metrics)."
    )
    return "\n".join(lines)

MAX_TOOL_EVENTS = 10
EVENT_ID_PATTERN = re.compile(r"\b[a-z0-9]+(?:-[a-z0-9]+)+\b")

# Gemini function declarations use standard JSON-Schema under the
# "parameters" key expected by the Gemini SDK.
TOOLS = [
    {
        "name": "query_detections",
        "description": "Query detections by source, risk level, review status, and MPA proximity.",
        "parameters": {
            "type": "object",
            "properties": {
                "source": {"type": "string"},
                "risk_level": {"type": "string"},
                "review_status": {"type": "string"},
                "near_mpa": {
                    "type": "boolean",
                    "description": "If true, return only detections inside or near a Marine Protected Area.",
                },
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


def _highest_risk_event() -> RiskEvent | None:
    summary = repo.summary()
    if not summary.highest_risk_event_id:
        return None
    return repo.get(summary.highest_risk_event_id)


def _highest_risk_answer() -> AskResponse:
    top_event = _highest_risk_event()
    if top_event is None:
        return AskResponse(answer="No detections are currently loaded in the backend dataset.")

    distance_text = (
        f"{top_event.distance_to_mpa_km:.1f} km from {top_event.mpa_name or 'the protected-area boundary'}"
        if top_event.distance_to_mpa_km is not None
        else "outside the stored MPA-distance range"
    )
    ais_text = (
        "no matching AIS broadcast"
        if top_event.ais_data_available and not top_event.ais_matched
        else "an AIS match"
        if top_event.ais_data_available
        else "no AIS coverage data"
    )

    return AskResponse(
        answer=(
            f"{top_event.id} is the highest-risk detection in the current backend dataset. "
            f"It has score {top_event.risk_score:.2f} ({top_event.risk_level}), "
            f"has {ais_text}, and sits {distance_text}."
        )
    )


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
        limit = max(1, min(limit, 600))
        near_mpa_raw = inputs.get("near_mpa")
        near_mpa = None if near_mpa_raw is None else bool(near_mpa_raw)
        events = repo.all(
            source=inputs.get("source"),
            level=inputs.get("risk_level"),
            review_status=inputs.get("review_status"),
            near_mpa=near_mpa,
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


def _methodology_answer(lowered: str) -> AskResponse | None:
    """Answer 'how does it work' questions about the system itself (used when the
    LLM is unavailable). Returns None if the question isn't about methodology."""
    if ("risk" in lowered and ("calculat" in lowered or "score" in lowered or "work" in lowered)) or \
       ("score" in lowered and ("how" in lowered or "calculat" in lowered)):
        return AskResponse(answer=(
            "Each detection gets a transparent score from 0.00 to 0.99: a 0.25 baseline for any "
            "SAR vessel, +0.20 if it has no matching AIS identity (a possible dark vessel), then "
            "MPA proximity is the biggest factor — +0.45 if inside a protected area, +0.30 within "
            "10 km, +0.15 within 50 km — plus +0.05 for repeated detections, capped at 0.99. "
            "Levels: CRITICAL >= 0.80, HIGH >= 0.60, MEDIUM >= 0.45, LOW below 0.45. "
            "Example: a dark vessel inside an MPA scores 0.25 + 0.20 + 0.45 = 0.90 (CRITICAL)."
        ))
    if "dark vessel" in lowered or ("dark" in lowered and ("what" in lowered or "mean" in lowered)):
        return AskResponse(answer=(
            "A dark vessel is a ship that radar detects but that has no matching AIS broadcast — "
            "its transponder is off. SAR satellites see the hull regardless, so a radar contact "
            "with no AIS identity near a protected area is the core signal OceanGuard surfaces."
        ))
    if ("data" in lowered or "source" in lowered) and ("what" in lowered or "where" in lowered or "use" in lowered):
        return AskResponse(answer=(
            "OceanGuard uses Global Fishing Watch (global SAR vessel detections), Sentinel-1 radar "
            "via Copernicus/CDSE (for imagery and our own model), WDPA protected-area boundaries, "
            "AISStream live AIS broadcasts, and a reference list of ports."
        ))
    if ("how" in lowered or "what" in lowered) and ("detect" in lowered or "yolo" in lowered or "model" in lowered or "radar" in lowered or "sar" in lowered):
        return AskResponse(answer=(
            "We run our own YOLO11n ship-detection model (fine-tuned on the HRSID SAR dataset, "
            "mAP@50 0.838) directly on fresh Sentinel-1 C-band radar chips. Ships appear as bright "
            "returns on dark water. Because it reads radar — not AIS — it can find vessels the "
            "AIS-based feed missed, either at a single point or across a swept area."
        ))
    return None


def _fallback(question: str) -> AskResponse:
    lowered = question.lower()
    matched_event = _find_event_from_question(question)

    if matched_event is not None:
        return AskResponse(answer=_summarise_event(matched_event))

    methodology = _methodology_answer(lowered)
    if methodology is not None:
        return methodology

    if "highest" in lowered or "most" in lowered or "bar-reef-003" in lowered:
        return _highest_risk_answer()

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
        answer = (
            f"The backend currently has {high} HIGH-risk detections and {critical} CRITICAL-risk detections."
        )
        if summary.highest_risk_event_id and summary.highest_risk_score is not None:
            answer += (
                f" The highest-risk event is {summary.highest_risk_event_id} "
                f"at score {summary.highest_risk_score:.2f}."
            )
        return AskResponse(
            answer=answer
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

    if "near mpa" in lowered or "inside mpa" in lowered or (
        ("mpa" in lowered or "protected area" in lowered or "protected" in lowered)
        and ("ship" in lowered or "vessel" in lowered or "detect" in lowered or "near" in lowered or "inside" in lowered or "give" in lowered or "list" in lowered or "show" in lowered)
    ):
        near_events = repo.all(near_mpa=True)
        if not near_events:
            return AskResponse(answer="No detections are currently flagged as near or inside a Marine Protected Area.")
        near_events_sorted = sorted(near_events, key=lambda e: e.risk_score, reverse=True)
        top = near_events_sorted[:10]
        lines = []
        for e in top:
            dist = f"{e.distance_to_mpa_km:.1f} km from {e.mpa_name or 'MPA'}" if e.distance_to_mpa_km is not None else "inside MPA"
            lines.append(f"- {e.id}: {e.risk_level} (score {e.risk_score:.2f}), {dist}")
        return AskResponse(
            answer=(
                f"There are {len(near_events)} detections near or inside Marine Protected Areas. "
                f"Top {len(top)} by risk score:\n" + "\n".join(lines)
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
            "I can answer questions about the loaded detections (risk levels, review states, MPA "
            "proximity, model metrics) and about how OceanGuard works — how the risk score is "
            "calculated, what a dark vessel is, what data sources we use, and how the detection "
            "model works. Try \"how is the risk score calculated?\" or \"which detection is highest risk?\""
        )
    )


async def ask(question: str) -> AskResponse:
    client = get_client()
    if client is None:
        return _fallback(question)

    try:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=_build_system_prompt(),
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
