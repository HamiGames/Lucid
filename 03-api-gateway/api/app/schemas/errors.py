from pydantic import BaseModel, Field
from typing import Any, Optional


class ErrorResponse(BaseModel):
    error_code: str = Field(example="not_implemented")
    message: str = Field(example="This operation is not available in Cluster A.")
    detail: Optional[Any] = None
