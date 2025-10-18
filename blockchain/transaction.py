from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, Any
import json
from .crypto import sha256_hex


@dataclass(frozen=True)
class Transaction:
    sender: str
    recipient: str
    amount: int
    nonce: int
    data: Dict[str, Any] = field(default_factory=dict)

    def serialize(self) -> bytes:
        return json.dumps(asdict(self), sort_keys=True, separators=(",", ":")).encode("utf-8")

    @property
    def txid(self) -> str:
        return sha256_hex(self.serialize())
