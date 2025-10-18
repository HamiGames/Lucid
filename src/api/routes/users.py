"""
User management routes for Lucid API
Handles user CRUD operations and authentication
"""

from __future__ import annotations

from typing import Dict, Optional

# Robust import for editor/runtime differences
try:
    import bcrypt  # type: ignore
except Exception:  # pragma: no cover
    bcrypt = None  # type: ignore

from fastapi import APIRouter, HTTPException, Query
from pymongo.errors import DuplicateKeyError

from src.api.db.users_repo import UsersRepo
from src.api.schemas.errors import ErrorResponse
from src.api.schemas.users import PaginatedUsers, RegisterRequest, UserPublic

router = APIRouter()


@router.get("", response_model=PaginatedUsers, tags=["users"])
def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Dict[str, object]:
    """Return a paginated list of users."""
    repo = UsersRepo.from_db()
    return repo.list_users(page=page, page_size=page_size)


@router.get(
    "/{user_id}",
    response_model=UserPublic,
    tags=["users"],
    responses={404: {"model": ErrorResponse}},
)
def get_user(user_id: str):
    """Fetch a single user by ID."""
    repo = UsersRepo.from_db()
    user = repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error_code="not_found", message="User not found"
            ).model_dump(),
        )
    return user


@router.post(
    "",
    response_model=UserPublic,
    tags=["users"],
    responses={
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_user(payload: RegisterRequest):
    """
    Create a user.

    Notes:
    - If RegisterRequest has no 'username', fallback to email local-part.
    - Password is hashed with bcrypt before storing.
    """
    if bcrypt is None:  # pragma: no cover
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="missing_dep", message="bcrypt not installed"
            ).model_dump(),
        )

    repo = UsersRepo.from_db()

    username = getattr(payload, "username", None) or payload.email.split("@", 1)[0]
    roles: Optional[list[str]] = getattr(payload, "roles", None)

    password_hash: str = bcrypt.hashpw(
        payload.password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    try:
        user = repo.create_user(
            email=payload.email,
            username=username,
            password_hash=password_hash,
            roles=roles,
        )
        return user
    except DuplicateKeyError:
        # unique index on users.email enforced at DB level
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                error_code="conflict", message="Email already exists"
            ).model_dump(),
        )


@router.delete(
    "/{user_id}",
    status_code=204,
    tags=["users"],
    responses={404: {"model": ErrorResponse}},
)
def delete_user(user_id: str):
    """Delete a user by ID. Returns 204 on success."""
    repo = UsersRepo.from_db()
    ok = repo.delete_user(user_id)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error_code="not_found", message="User not found"
            ).model_dump(),
        )
    # 204: no body
