from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    time: str
    version: str
