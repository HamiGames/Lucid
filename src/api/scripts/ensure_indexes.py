from __future__ import annotations

from collections import OrderedDict
from typing import Iterable, Tuple

from pymongo import ASCENDING
from pymongo.collection import Collection

from src.api.db.connection import get_db


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


if __name__ == "__main__":
    main()
