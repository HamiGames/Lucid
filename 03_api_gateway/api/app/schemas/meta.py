"""
File: /app/03_api_gateway/api/app/schemas/meta.py
x-lucid-file-path: /app/03_api_gateway/api/app/schemas/meta.py
x-lucid-file-type: python
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    time: str
    version: str
