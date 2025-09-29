from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Tuple

from cryptography.fernet import Fernet, InvalidToken
from tronpy.keys import PrivateKey


@dataclass(frozen=True)
class WalletKeys:
    private_key_hex: str
    public_key_hex: str
    address_base58: str


def generate_tron_wallet() -> WalletKeys:
    pk = PrivateKey.random()
    private_key_hex = pk.hex()
    pub = pk.public_key
    return WalletKeys(
        private_key_hex=private_key_hex,
        public_key_hex=pub.hex(),
        address_base58=pub.to_base58check_address(),
    )


def _fernet_from_secret(secret: str | bytes | None) -> Fernet:
    """
    Accept:
      - 32-byte urlsafe base64 string (preferred)
      - raw 32 bytes (we'll base64-url encode)
      - empty/None -> ephemeral key (NOT for production)
    """
    if not secret:
        # Ephemeral (process lifetime). Caller should have provided a proper secret.
        key = base64.urlsafe_b64encode(os.urandom(32))
        return Fernet(key)

    if isinstance(secret, str):
        try:
            # if already urlsafe b64, this should decode to length 32
            raw = base64.urlsafe_b64decode(secret)
            if len(raw) != 32:
                # treat as raw
                raise ValueError("decoded length != 32")
            return Fernet(secret.encode("utf-8"))
        except Exception:
            # assume raw hex or raw bytes in str; normalize
            s = secret.encode("utf-8", "ignore")
            if len(s) == 32:
                key = base64.urlsafe_b64encode(s)
            else:
                # If hex-like, try to decode hex to 32 bytes (not strict)
                try:
                    raw = bytes.fromhex(secret)
                    if len(raw) != 32:
                        raise ValueError("hex length not 32")
                    key = base64.urlsafe_b64encode(raw)
                except Exception:
                    # fall back: hash to 32 bytes
                    import hashlib

                    raw = hashlib.sha256(s).digest()
                    key = base64.urlsafe_b64encode(raw)
            return Fernet(key)
    else:
        if len(secret) != 32:
            import hashlib

            secret = hashlib.sha256(secret).digest()
        key = base64.urlsafe_b64encode(secret)
        return Fernet(key)


def encrypt_privkey_hex(priv_hex: str, secret: str | bytes | None) -> str:
    f = _fernet_from_secret(secret)
    token = f.encrypt(priv_hex.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_privkey_hex(token: str, secret: str | bytes | None) -> str:
    f = _fernet_from_secret(secret)
    try:
        return f.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as e:
        raise ValueError("Invalid encryption secret or token") from e
