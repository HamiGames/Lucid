# src/api/config.py
from pydantic import BaseModel
import os
from functools import lru_cache


class Settings(BaseModel):
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "lucid-api")
    VERSION: str = os.getenv("VERSION", "0.1.0")
    LUCID_ENV: str = os.getenv("LUCID_ENV", "dev")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
