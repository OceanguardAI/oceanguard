"""Configuration for the YOLO SAR inference service.

Credentials come from the environment (Cloud Run injects them from GitHub
Secrets). The Sentinel Hub client id/secret are the same pair the backend uses
for the evidence-card chips.
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Sentinel Hub OAuth (same credentials as the backend SAR chips). Defaults to
    # the Copernicus Data Space Ecosystem (free tier), where the client was made.
    sentinelhub_client_id: str = ""
    sentinelhub_client_secret: str = ""
    sentinelhub_token_url: str = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    sentinelhub_process_url: str = "https://sh.dataspace.copernicus.eu/api/v1/process"

    # Model + inference.
    model_path: Path = Path(__file__).resolve().parent.parent / "models" / "best.pt"
    conf_threshold: float = 0.25

    # Inference chip geometry. Tighter + denser than the display chip so the
    # HRSID-trained model sees ships at a resolution close to what it learned:
    # ~0.02 deg half-width (~4.4 km across) at 640 px = ~7 m/px.
    chip_half_deg: float = 0.02
    chip_px: int = 640

    # CORS for the backend proxy / direct frontend calls.
    cors_origins: str = "*"


settings = Settings()
