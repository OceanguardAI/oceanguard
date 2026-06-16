from __future__ import annotations

import os

from dotenv import load_dotenv
from google import genai


def main() -> None:
    """Small Vertex AI smoke test for OceanGuard development."""
    load_dotenv()

    project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip()
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "True").strip().lower() == "true"

    if not use_vertex:
        raise RuntimeError("GOOGLE_GENAI_USE_VERTEXAI must be True for this Vertex AI test.")
    if not project:
        raise RuntimeError("GOOGLE_CLOUD_PROJECT is required. Add it to your .env file first.")

    client = genai.Client(vertexai=True, project=project, location=location)
    response = client.models.generate_content(
        model=model,
        contents=(
            "You are OceanGuard AI. Reply in one short sentence confirming that "
            "Vertex AI authentication is working."
        ),
    )

    print("Vertex AI test succeeded.")
    print(response.text)


if __name__ == "__main__":
    main()
