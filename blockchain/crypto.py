from __future__ import annotations

import hashlib
from typing import Iterable, List


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def merkle_root(hashes: Iterable[bytes]) -> bytes:
    """Compute a simple Merkle root from an iterable of byte hashes."""
    nodes: List[bytes] = list(hashes)
    if not nodes:
        return b"\x00" * 32
    while len(nodes) > 1:
        if len(nodes) % 2 == 1:
            nodes.append(nodes[-1])
        it = iter(nodes)
        nodes = [sha256(a + b) for a, b in zip(it, it)]
    return nodes[0]
