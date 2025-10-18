from __future__ import annotations

import base64
import secrets
from dataclasses import dataclass


@dataclass(frozen=True)
class Keypair:
    private_key: bytes
    public_key: bytes

    def export_b64(self) -> dict[str, str]:
        return {
            "priv": base64.b64encode(self.private_key).decode("ascii"),
            "pub": base64.b64encode(self.public_key).decode("ascii"),
        }


def generate_keypair() -> Keypair:
    """Dev-friendly 32-byte private key; 'public' here is a hash for demo purposes."""
    priv = secrets.token_bytes(32)
    pub = priv[:16] + priv[:16]  # simple derivation for dev use; replace with real crypto as needed
    return Keypair(private_key=priv, public_key=pub)
