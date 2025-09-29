from pydantic import BaseModel
from typing import Any, Optional


class ErrorResponse(BaseModel):
    error_code: str
    message: str
    detail: Optional[Any] = None
