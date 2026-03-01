from __future__ import annotations

from collections import OrderedDict
from typing import Iterable, Tuple

from pymongo import ASCENDING
from pymongo.collection import Collection

from app.db.connection import get_db


def _keyspec(pairs: Iterable[Tuple[str, int]]) -> OrderedDict:
    return OrderedDict(pairs)


def _has_index(c: Collection, key_pairs: Iterable[Tuple[str, int]], **opts) -> bool:
    ks = _keyspec(key_pairs)
    for ix in c.list_indexes():
        if OrderedDict(ix["key"]) == ks:
            # match options if provided (unique / expireAfterSeconds)
            for k, v in opts.items():
                if ix.get(k) != v:
                    break
            else:
                return True
    return False


def _ensure_index(c: Collection, key_pairs, name: str, **opts) -> str:
    if _has_index(c, key_pairs, **opts):
        return f"[exists] {c.name}.{name}"
    c.create_index(list(key_pairs), name=name, **opts)
    return f"[created] {c.name}.{name}"


def main() -> None:
    db = get_db()

    users = db["users"]
    sessions = db["sessions"]
    chunks = db["chunks"]
    control_policies = db["control_policies"]

    # Unique email on users
    print(
        _ensure_index(
            users,
            (("email", ASCENDING),),
            name="users_email_unique",
            unique=True,
        )
    )

    # TTL on sessions.expiresAt (expire instantly at that time)
    print(
        _ensure_index(
            sessions,
            (("expiresAt", ASCENDING),),
            name="sessions_expiresAt_ttl",
            expireAfterSeconds=0,
        )
    )

    # Session pipeline indexes
    print(
        _ensure_index(
            sessions,
            (("user_id", ASCENDING), ("started_at", ASCENDING)),
            name="sessions_user_id_started_at",
        )
    )
    
    print(
        _ensure_index(
            sessions,
            (("owner_address", ASCENDING), ("started_at", ASCENDING)),
            name="sessions_owner_address_started_at",
        )
    )
    
    print(
        _ensure_index(
            sessions,
            (("node_id", ASCENDING), ("state", ASCENDING)),
            name="sessions_node_id_state",
        )
    )
    
    print(
        _ensure_index(
            sessions,
            (("state", ASCENDING), ("started_at", ASCENDING)),
            name="sessions_state_started_at",
        )
    )

    # Chunk indexes
    print(
        _ensure_index(
            chunks,
            (("session_id", ASCENDING), ("sequence", ASCENDING)),
            name="chunks_session_id_sequence",
        )
    )
    
    print(
        _ensure_index(
            chunks,
            (("state", ASCENDING),),
            name="chunks_state",
        )
    )

    # Control policy indexes
    print(
        _ensure_index(
            control_policies,
            (("session_id", ASCENDING),),
            name="control_policies_session_id",
        )
    )
    
    print(
        _ensure_index(
            control_policies,
            (("policy_hash", ASCENDING),),
            name="control_policies_policy_hash",
        )
    )


if __name__ == "__main__":
    main()
