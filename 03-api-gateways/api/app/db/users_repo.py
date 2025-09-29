from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

from bson import ObjectId
from pymongo import ASCENDING, ReturnDocument
from pymongo.collection import Collection

from app.db.connection import get_db

# ---- Project params / constants (Cluster B) ----
USERS_COLLECTION = "users"


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _oid(id_or_str: str | ObjectId) -> ObjectId:
    return id_or_str if isinstance(id_or_str, ObjectId) else ObjectId(id_or_str)


def _public_user(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Mongo document to a safe/public dict (no password_hash)."""
    if not doc:
        return doc
    d = dict(doc)
    d["id"] = str(d.pop("_id"))
    d.pop("password_hash", None)

    # 🔧 Map roles -> role (keep original roles too, if present)
    if "role" not in d:
        roles = d.get("roles") or []
        d["role"] = roles[0] if isinstance(roles, list) and roles else None

    return d


@dataclass
class UsersRepo:
    """Data-access layer for the 'users' collection (no business logic here)."""

    collection: Collection

    @classmethod
    def from_db(cls) -> "UsersRepo":
        return cls(get_db()[USERS_COLLECTION])

    # ---- Queries ----

    def get_by_id(self, user_id: str | ObjectId) -> Optional[Dict[str, Any]]:
        doc = self.collection.find_one({"_id": _oid(user_id)})
        return _public_user(doc) if doc else None

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        doc = self.collection.find_one({"email": email.lower()})
        return _public_user(doc) if doc else None

    def list_users(self, *, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        page = max(1, int(page))
        page_size = max(1, min(100, int(page_size)))
        skip = (page - 1) * page_size

        cursor = (
            self.collection.find({}, projection={"password_hash": 0})
            .sort("_id", ASCENDING)
            .skip(skip)
            .limit(page_size)
        )
        items = [_public_user(d) for d in cursor]
        total = (
            self.collection.estimated_document_count()
        )  # O(1) estimate; change to count_documents({}) if you need exact

        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": int(total),
        }

    # ---- Mutations ----

    def create_user(
        self,
        *,
        email: str,
        username: str,
        password_hash: str,
        roles: Optional[List[str]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        doc: Dict[str, Any] = {
            "email": email.lower(),
            "username": username,
            "password_hash": password_hash,
            "roles": roles or ["user"],
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
        }
        if extra:
            doc.update(extra)

        inserted = self.collection.insert_one(doc)
        doc["_id"] = inserted.inserted_id
        return _public_user(doc)

    def update_user(
        self,
        user_id: str | ObjectId,
        *,
        username: Optional[str] = None,
        roles: Optional[List[str]] = None,
        password_hash: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        set_ops: Dict[str, Any] = {"updated_at": _utc_now()}
        if username is not None:
            set_ops["username"] = username
        if roles is not None:
            set_ops["roles"] = roles
        if password_hash is not None:
            set_ops["password_hash"] = password_hash
        if extra:
            set_ops.update(extra)

        updated = self.collection.find_one_and_update(
            {"_id": _oid(user_id)},
            {"$set": set_ops},
            return_document=ReturnDocument.AFTER,
        )
        return _public_user(updated) if updated else None

    def delete_user(self, user_id: str | ObjectId) -> bool:
        res = self.collection.delete_one({"_id": _oid(user_id)})
        return res.deleted_count == 1
