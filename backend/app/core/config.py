from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    gemini_api_key: str = ""
    gemini_use_gcp: bool = False
    google_genai_use_vertexai: bool = False
    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"
    gemini_model: str = "gemini-2.5-flash"
    agent_max_tool_rounds: int = 5
    agent_narrator_max_tokens: int = 500
    agent_briefing_max_tokens: int = 400
    agent_patrol_max_tokens: int = 600
    agent_ask_max_tokens: int = 700
    data_dir: Path = Path(__file__).resolve().parents[2] / "data"
    # NoDecode: let our validator parse a plain/comma-separated string from env.
    # Without it pydantic-settings tries to JSON-decode the value first, which
    # crashes when the env var is a single URL (e.g. the Cloud Run frontend URL).
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # --- Live data ingestion (Global Fishing Watch + AISStream) ---
    gfw_api_token: str = ""
    aisstream_api_key: str = ""
    # Monitored area: min_lon, min_lat, max_lon, max_lat (default = Bar Reef, Sri Lanka).
    gfw_region_bbox: list[float] = [79.4, 8.0, 79.9, 8.8]
    # How many days back to query SAR detections each ingest run.
    gfw_lookback_days: int = 90
    # Auto-ingest live data at startup when a GFW token is present.
    gfw_ingest_on_startup: bool = True

    @field_validator("gfw_region_bbox", mode="before")
    @classmethod
    def _split_bbox(cls, value: object) -> object:
        if isinstance(value, str):
            return [float(item.strip()) for item in value.split(",") if item.strip()]
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            text = value.strip()
            # Accept either a JSON array or a comma-separated list of origins.
            if text.startswith("["):
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    pass
            return [item.strip() for item in text.split(",") if item.strip()]
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()
