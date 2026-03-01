"""
Authentication routes for Lucid API
Handles login, refresh, and logout operations
"""

from fastapi import APIRouter, HTTPException
from starlette.status import HTTP_501_NOT_IMPLEMENTED

from src.api.schemas.auth import LoginRequest, RefreshRequest, LogoutRequest, TokenPair
from src.api.schemas.errors import ErrorResponse

router = APIRouter()


def _not_implemented() -> HTTPException:
    return HTTPException(
        status_code=HTTP_501_NOT_IMPLEMENTED,
        detail=ErrorResponse(
            error_code="not_implemented",
            message="Auth service is not available in Cluster A.",
        ).model_dump(),
    )


@router.post(
    "/login", response_model=TokenPair, responses={501: {"model": ErrorResponse}}
)
def login(_: LoginRequest):
    raise _not_implemented()


@router.post(
    "/refresh", response_model=TokenPair, responses={501: {"model": ErrorResponse}}
)
def refresh(_: RefreshRequest):
    raise _not_implemented()


@router.post(
    "/logout",
    responses={200: {"description": "Logged out"}, 501: {"model": ErrorResponse}},
)
def logout(_: LogoutRequest):
    raise _not_implemented()
