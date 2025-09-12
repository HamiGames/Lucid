from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(example="ok")
    service: str = Field(example="lucid-api")
    time: str = Field(description="ISO-8601 UTC timestamp")
    version: str = Field(example="0.1.0")
