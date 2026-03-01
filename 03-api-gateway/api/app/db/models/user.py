# Path: 03-api-gateway/api/app/db/models/user.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class User(BaseModel):
    id: Optional[str] = Field(default=None, alias="_id")
    email: EmailStr
    display_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
