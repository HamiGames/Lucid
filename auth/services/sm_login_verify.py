"""Optional lucid-server-manager verification before issuing tokens (login/register)."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


async def verify_with_server_manager(
    base_url: str,
    path: str,
    payload: Dict[str, Any],
    timeout: float = 15.0,
) -> tuple[bool, Optional[str]]:
    url = base_url.rstrip("/") + path
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, json=payload)
            if r.status_code >= 400:
                return False, "server_manager_denied"
            data = r.json()
            if not data.get("ok", True):
                return False, str(data.get("reason") or "denied")
            return True, None
    except httpx.RequestError as e:
        logger.warning("server-manager verify transport: %s", e)
        return False, "server_manager_unreachable"


async def verify_preauth_with_server_manager(
    base_url: str,
    path: str,
    pre_auth_token: str,
    intent: str,
    user_id: Optional[str] = None,
    timeout: float = 15.0,
) -> Tuple[bool, Optional[str], Dict[str, Any]]:
    """POST verify-preauth; returns (ok, reason, claims)."""
    url = base_url.rstrip("/") + path
    body = {"pre_auth_token": pre_auth_token, "intent": intent}
    if user_id:
        body["user_id"] = user_id
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, json=body)
            if r.status_code >= 400:
                return False, "server_manager_denied", {}
            data = r.json()
            if not data.get("ok", True):
                return False, str(data.get("reason") or "denied"), {}
            return True, None, dict(data.get("claims") or {})
    except httpx.RequestError as e:
        logger.warning("server-manager preauth transport: %s", e)
        return False, "server_manager_unreachable", {}


async def registry_user_with_server_manager(
    base_url: str,
    path: str,
    user_id: str,
    registration_key: str,
    timeout: float = 15.0,
) -> Tuple[bool, Optional[str]]:
    url = base_url.rstrip("/") + path
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(
                url,
                json={"user_id": user_id, "registration_key": registration_key},
            )
            if r.status_code >= 400:
                return False, "server_manager_denied"
            data = r.json()
            if not data.get("ok", True):
                return False, str(data.get("detail") or data.get("reason") or "denied")
            return True, None
    except httpx.RequestError as e:
        logger.warning("server-manager registry transport: %s", e)
        return False, "server_manager_unreachable"

