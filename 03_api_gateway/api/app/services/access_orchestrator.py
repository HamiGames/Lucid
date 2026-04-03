"""
File: 03_api_gateway/api/app/services/access_orchestrator.py
x-lucid-file-path: /app/03_api_gateway/api/app/services/access_orchestrator.py
x-lucid-file-directory: /app/03_api_gateway/api/app/services
x-lucid-file-type: python

Delegates user token validation to lucid-auth-service and access registration / allow-list
to server-management. Does not log tokens, raw upstream bodies, or secret-bearing fields.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, Optional, Tuple

import aiohttp

from api.app.config import Settings, get_settings

try:
    from api.app.utils.logging import get_logger

    logger = get_logger()
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

_session: Optional[aiohttp.ClientSession] = None


async def _http_session(settings: Settings) -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        timeout = aiohttp.ClientTimeout(total=settings.ACCESS_HTTP_TIMEOUT_SECONDS)
        _session = aiohttp.ClientSession(timeout=timeout)
    return _session


async def close_access_http_session() -> None:
    global _session
    if _session and not _session.closed:
        await _session.close()
    _session = None


async def introspect_with_auth_service(
    settings: Settings,
    authorization_value: str,
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    POST lucid-auth-service token introspection. authorization_value is full 'Bearer ...' header value.
    """
    url = settings.auth_introspect_url()
    session = await _http_session(settings)
    headers = {
        "Authorization": authorization_value,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    try:
        async with session.post(url, headers=headers, json={}) as resp:
            text = await resp.text()
            if resp.status != 200:
                logger.info(
                    "Auth introspection denied: status=%s correlation=%s",
                    resp.status,
                    uuid.uuid4(),
                )
                return False, None
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                logger.warning("Auth introspection: non-JSON success body omitted from logs")
                return False, None
            if not data.get("valid"):
                return False, None
            uid = data.get("user_id")
            if not uid:
                return False, None
            return True, {
                "user_id": str(uid),
                "role": str(data.get("role") or "USER"),
                "jti": data.get("jti"),
            }
    except aiohttp.ClientError as e:
        logger.warning("Auth introspection transport error: %s", type(e).__name__)
        return False, None


async def submit_server_management_access(
    settings: Settings,
    user_id: str,
    role: str,
    calling_service: str,
    correlation_id: str,
) -> Tuple[bool, Optional[str]]:
    """
    Ask server-management to register or allow-list the user. Request/response bodies are not logged.
    Returns (allowed, error_code_for_gateway).
    """
    if not settings.SERVER_MANAGEMENT_ENABLED:
        return True, None

    url = settings.server_management_access_url()
    session = await _http_session(settings)
    payload = {
        "user_id": user_id,
        "role": role,
        "calling_service": calling_service,
        "correlation_id": correlation_id,
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Lucid-Correlation-Id": correlation_id,
    }
    if settings.SERVER_MANAGEMENT_GATEWAY_TOKEN:
        headers["X-Lucid-Gateway-Token"] = settings.SERVER_MANAGEMENT_GATEWAY_TOKEN

    try:
        async with session.post(url, headers=headers, json=payload) as resp:
            if resp.status == 404 and settings.SERVER_MANAGEMENT_IGNORE_404:
                logger.info(
                    "Server-management access path missing (404); allowed by policy correlation=%s",
                    correlation_id,
                )
                return True, None
            if resp.status >= 500:
                return False, "LUCID_ERR_5008"
            if resp.status == 403:
                return False, "LUCID_ERR_2004"
            if resp.status != 200:
                return False, "LUCID_ERR_2004"
            text = await resp.text()
            try:
                data = json.loads(text) if text else {}
            except json.JSONDecodeError:
                return False, "LUCID_ERR_2004"
            allowed = data.get("allowed", True)
            if isinstance(allowed, bool) and allowed:
                return True, None
            return False, "LUCID_ERR_2004"
    except aiohttp.ClientError as e:
        logger.warning("Server-management transport error: %s", type(e).__name__)
        return False, "LUCID_ERR_5008"


async def resolve_trusted_gui_access(
    settings: Settings,
    authorization_header: str,
    calling_service: str,
    correlation_id: str,
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Full pipeline: auth introspection then server-management. Returns (ok, user_state, error_code).
    """
    ok, user = await introspect_with_auth_service(settings, authorization_header)
    if not ok or not user:
        return False, None, "LUCID_ERR_2001"

    sm_ok, sm_code = await submit_server_management_access(
        settings,
        user_id=user["user_id"],
        role=user["role"],
        calling_service=calling_service,
        correlation_id=correlation_id,
    )
    if not sm_ok:
        return False, None, sm_code or "LUCID_ERR_2004"

    scope_user = {
        "user_id": user["user_id"],
        "role": user["role"],
        "source": "gui-trusted-delegated",
        "calling_service": calling_service,
    }
    return True, scope_user, None
