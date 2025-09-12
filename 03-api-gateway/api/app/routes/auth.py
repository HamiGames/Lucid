from fastapi import APIRouter, HTTPException, status
from app.schemas import (
    LoginRequest,
    RefreshRequest,
    LogoutRequest,
    TokenPair,
    ErrorResponse,
)

router = APIRouter()


def _not_implemented() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=ErrorResponse(
            error_code="not_implemented",
            message="Auth flows land in Cluster C; skeleton only.",
            detail=None,
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
