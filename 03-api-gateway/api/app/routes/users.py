from fastapi import APIRouter, HTTPException, status, Path
from app.schemas import PaginatedUsers, RegisterRequest, UserPublic, ErrorResponse

router = APIRouter()


def _not_implemented() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=ErrorResponse(
            error_code="not_implemented",
            message="Users service lands in Cluster D; skeleton only.",
            detail=None,
        ).model_dump(),
    )


@router.get(
    "", response_model=PaginatedUsers, responses={501: {"model": ErrorResponse}}
)
def list_users(page: int = 1, page_size: int = 20):
    raise _not_implemented()


@router.post(
    "/register", response_model=UserPublic, responses={501: {"model": ErrorResponse}}
)
def register(_: RegisterRequest):
    raise _not_implemented()


@router.get("/me", response_model=UserPublic, responses={501: {"model": ErrorResponse}})
def me():
    raise _not_implemented()


@router.get(
    "/{user_id}", response_model=UserPublic, responses={501: {"model": ErrorResponse}}
)
def get_user(user_id: str = Path(..., description="User identifier")):
    raise _not_implemented()
