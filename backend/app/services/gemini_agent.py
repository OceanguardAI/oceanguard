from __future__ import annotations

import os

from google import genai

from app.core.config import settings
from app.models.schemas import RiskEvent


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _vertex_project() -> str:
    return settings.google_cloud_project or os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()


def _vertex_location() -> str:
    return settings.google_cloud_location or os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1").strip()


def _vertex_model() -> str:
    return settings.gemini_model or os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()


def _use_vertex_ai() -> bool:
    explicit_flag = os.getenv("GOOGLE_GENAI_USE_VERTEXAI")
    if explicit_flag is not None:
        return _truthy(explicit_flag)
    return settings.gemini_use_gcp


def _get_vertex_client() -> genai.Client:
    """Create a Vertex AI Gemini client using ADC credentials."""
    if not _use_vertex_ai():
        raise RuntimeError(
            "Vertex AI mode is disabled. Set GOOGLE_GENAI_USE_VERTEXAI=True "
            "or GEMINI_USE_GCP=true before calling ask_gemini()."
        )

    project = _vertex_project()
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is required for Vertex AI Gemini calls.")

    return genai.Client(
        vertexai=True,
        project=project,
        location=_vertex_location(),
    )


def ask_gemini(prompt: str) -> str:
    """Send a plain-text prompt to Gemini on Vertex AI and return the text reply."""
    client = _get_vertex_client()
    response = client.models.generate_content(
        model=_vertex_model(),
        contents=prompt,
    )
    text = getattr(response, "text", None)
    return text.strip() if isinstance(text, str) else ""


def explain_vessel_risk_event(event: RiskEvent) -> str:
    """Generate a calm, non-accusatory evidence-card explanation for one event."""
    prompt = f"""
You are OceanGuard AI, a marine monitoring assistant.

Write a short explanation for a dashboard evidence card.
Keep the tone cautious and non-accusatory.
Do not claim illegal activity or intent.
Say this is a possible risk signal that still needs human review.

Event details:
- Event ID: {event.id}
- Source: {event.source}
- Risk score: {event.risk_score:.2f}
- Risk level: {event.risk_level}
- AIS matched: {event.ais_matched}
- AIS data available: {event.ais_data_available}
- Inside MPA: {event.inside_mpa}
- Near MPA: {event.near_mpa}
- MPA name: {event.mpa_name or "Unknown"}
- Distance to MPA (km): {event.distance_to_mpa_km}
- Nearest port: {event.nearest_port or "Unknown"}
- Distance from port (km): {event.distance_from_port_km}
- SAR confidence: {event.sar_confidence:.2f}
- Timestamp: {event.timestamp}

Return 3 to 4 sentences only.
""".strip()

    return ask_gemini(prompt)
