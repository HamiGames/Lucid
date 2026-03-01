from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

# ---- Dependencies -----------------------------------------------------------
try:
    import bcrypt  # type: ignore
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "Missing dependency 'bcrypt'. Install with: pip install bcrypt"
    ) from e

from pymongo.collection import Collection
from pymongo.errors import PyMongoError

from src.api.db.connection import get_db

# ---- Project params / constants (Cluster B) --------------------------------
USERS_COLLECTION = "users"
ENV_FLAG = os.getenv("LUCID_ENV", "dev").lower()  # dev | test | prod

# Dev seed defaults (override via env if you like)
ADMIN_EMAIL: str = os.getenv("SEED_ADMIN_EMAIL", "admin@lucid.dev")
ADMIN_PASSWORD: str = os.getenv("SEED_ADMIN_PASSWORD", "admin123456")

TEST_EMAIL: str = os.getenv("SEED_TEST_EMAIL", "test@lucid.dev")
TEST_PASSWORD: str = os.getenv("SEED_TEST_PASSWORD", "test123456")

# If true, rotate (reset) password hashes on each run
ROTATE_PASSWORDS: bool = os.getenv("SEED_ROTATE_PASSWORDS", "false").lower() in {
    "1",
    "true",
    "yes",
}


# ---- Helpers ----------------------------------------------------------------
def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _hash_password(plain: str) -> str:
    if not plain:
        raise ValueError("Empty password is not allowed for seed data")
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _ensure_user(
    col: Collection,
    *,
    email: str,
    username: str,
    roles: list[str],
    password_plain: Optional[str],
    rotate_passwords: bool,
) -> Dict[str, Any]:
    """
    Idempotent upsert of a user:
      - creates if missing
      - updates username/roles
      - updates password only when rotate_passwords=True and a plaintext is provided
    """
    now = _utc_now()
    doc: Dict[str, Any] = {
        "email": email.lower(),
        "username": username,
        "roles": roles,
        "updated_at": now,
    }

    existing: Optional[Dict[str, Any]] = col.find_one({"email": doc["email"]})

    # Set/rotate password hash as needed
    if (existing is None and password_plain) or (
        existing is not None and rotate_passwords and password_plain
    ):
        doc["password_hash"] = _hash_password(password_plain)

    if existing is None:
        # create
        doc["created_at"] = now
        col.insert_one(doc)
        doc["_status"] = "created"
        return doc

    # update (do not unset existing fields)
    col.update_one({"_id": existing["_id"]}, {"$set": doc})
    existing.update(doc)
    existing["_status"] = "updated_rotated" if "password_hash" in doc else "updated"
    return existing


# ---- Entry point ------------------------------------------------------------
def main() -> None:
    if ENV_FLAG != "dev":
        print(f"[seed] Skipped: LUCID_ENV={ENV_FLAG!r} (only runs in 'dev').")
        sys.exit(0)

    db = get_db()
    users = db[USERS_COLLECTION]

    try:
        admin = _ensure_user(
            users,
            email=ADMIN_EMAIL,
            username="admin",
            roles=["admin", "user"],
            password_plain=ADMIN_PASSWORD,
            rotate_passwords=ROTATE_PASSWORDS,
        )
        print(f"[seed] admin -> {admin['email']} ({admin.get('_status')})")

        test = _ensure_user(
            users,
            email=TEST_EMAIL,
            username="test",
            roles=["user"],
            password_plain=TEST_PASSWORD,
            rotate_passwords=ROTATE_PASSWORDS,
        )
        print(f"[seed] test  -> {test['email']} ({test.get('_status')})")

    except PyMongoError as e:
        print(f"[seed][error] Mongo error: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:  # pragma: no cover
        print(f"[seed][error] {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
