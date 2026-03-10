# app/db/__init__.py
from api.app.db.connection import (
    get_db,
    get_client,
    ping,
    _resolve_uri,
    _resolve_db_name,
    close_client,
)  # re-export for stable imports
from api.app.db.users_repo import UsersRepo, USERS_COLLECTION


__all__ = [
    'get_db',
    'get_client',
    'ping',
    'close_client',
    '_resolve_uri',
    '_resolve_db_name',
    'UsersRepo',
    'USERS_COLLECTION',
]