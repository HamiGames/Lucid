from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional


class LoginRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: str

    @field_validator("password")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v:
            raise ValueError("Password cannot be empty")
        return v

    @field_validator("email")
    @classmethod
    def _username_or_email(cls, _v, values):
        # ensure at least one of username/email is provided
        if not values.get("username") and not values.get("email"):
            raise ValueError("Either username or email must be provided")
        return _v


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
