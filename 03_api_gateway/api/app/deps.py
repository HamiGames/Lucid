"""
File: /app/03_api_gateway/api/app/deps.py
x-lucid-file-path: /app/03_api_gateway/api/app/deps.py
x-lucid-file-type: python
"""

from api.app.config import get_settings, Settings


def get_config() -> Settings:
    return get_settings()
