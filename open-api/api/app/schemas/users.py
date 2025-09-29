from pydantic import BaseModel, EmailStr, Field
from typing import List
from datetime import datetime


class UserPublic(BaseModel):
    id: str = Field()
    email: EmailStr
    role: str = Field()
    created_at: datetime
    updated_at: datetime


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class PaginatedUsers(BaseModel):
    items: List[UserPublic]
    page: int
    page_size: int
    total: int
