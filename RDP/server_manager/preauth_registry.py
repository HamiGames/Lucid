"""
File: RDP/server_manager/preauth_registry.py
Short-lived pre-auth token issuance/verification and user registry for lucid-auth-service handshakes.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import threading
import time
import uuid
from typing import Any, Dict, Optional, Tuple


def _b64u_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii").rstrip("=")


def _b64u_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


class PreauthRegistry:
    """In-memory pre-auth tokens and user_id -> registration_key registry (replace with Redis/Mongo as needed)."""

    def __init__(self, secret: str, default_ttl_seconds: int = 600) -> None:
        self._secret = secret.encode("utf-8") if isinstance(secret, str) else secret
        self._ttl = default_ttl_seconds
        self._lock = threading.Lock()
        self._registry: Dict[str, Dict[str, Any]] = {}

    def issue_token(self, client_metadata: Optional[Dict[str, Any]] = None) -> Tuple[str, int]:
        now = time.time()
        exp = now + self._ttl
        payload = {
            "exp": exp,
            "iat": now,
            "jti": str(uuid.uuid4()),
            "meta": client_metadata or {},
        }
        body = _b64u_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        sig = _b64u_encode(hmac.new(self._secret, body.encode("ascii"), hashlib.sha256).digest())
        token = f"{body}.{sig}"
        return token, int(self._ttl)

    def verify_token(
        self,
        token: str,
        intent: str,
        user_id: Optional[str] = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        if not token or "." not in token:
            return False, "invalid_token", {}
        body, sig = token.rsplit(".", 1)
        expect = _b64u_encode(hmac.new(self._secret, body.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(expect, sig):
            return False, "bad_signature", {}
        try:
            payload = json.loads(_b64u_decode(body).decode("utf-8"))
        except Exception:
            return False, "bad_payload", {}
        if time.time() > float(payload.get("exp", 0)):
            return False, "expired", {}
        if intent not in ("login", "register"):
            return False, "bad_intent", {}
        if intent == "login" and user_id:
            row = self._registry.get(user_id)
            if not row:
                return False, "not_registered", {}
        return True, "", {"jti": payload.get("jti"), "meta": payload.get("meta") or {}}

    def register_user(self, user_id: str, registration_key: str) -> Tuple[bool, str]:
        if not user_id or not registration_key:
            return False, "missing_fields"
        with self._lock:
            self._registry[user_id] = {
                "registration_key": registration_key,
                "registered_at": time.time(),
            }
        return True, ""

    def get_registration_key(self, user_id: str) -> Optional[str]:
        with self._lock:
            row = self._registry.get(user_id)
            return row.get("registration_key") if row else None


_instance: Optional[PreauthRegistry] = None


def get_preauth_registry() -> PreauthRegistry:
    global _instance
    if _instance is None:
        secret = os.environ.get("LUCID_PREAUTH_SECRET", "dev-lucid-preauth-change-in-production")
        ttl = int(os.environ.get("LUCID_PREAUTH_TTL_SECONDS", "600"))
        _instance = PreauthRegistry(secret, default_ttl_seconds=ttl)
    return _instance
