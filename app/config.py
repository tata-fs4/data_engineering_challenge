from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseSettings, validator


class Settings(BaseSettings):
    app_name: str = "Trip Analytics API"
    database_url: str = "sqlite+aiosqlite:///./tripdata.db"
    sync_database_url: str = "sqlite:///./tripdata.db"
    ingestion_chunk_size: int = 1000
    geohash_precision: int = 5
    time_bucket_minutes: int = 60
    environment: Literal["development", "production", "test"] = "development"
    data_dir: Path = Path("data")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @validator("data_dir", pre=True)
    def ensure_data_dir(cls, value: Optional[str]) -> Path:
        path = Path(value) if value is not None else Path("data")
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
