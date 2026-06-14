from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    data_dir: Path = Path(__file__).parent.parent.parent / "data"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
