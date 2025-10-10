from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RDPSession(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    host: str  # e.g., raspberry pi host/ip
    port: int
    status: str = "pending"  # pending, active, closed
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
