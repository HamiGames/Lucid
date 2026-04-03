"""
File: /app/03_api_gateway/api/app/middleware/auth.py
x-lucid-file-path: /app/03_api_gateway/api/app/middleware/auth.py
x-lucid-file-directory: /app/03_api_gateway/api/app/middleware
x-lucid-file-type: python

Authentication Middleware

Purpose: Validates requests. GUI integration callers listed in
configs/alignment-mats/gui-services.json may use delegated validation via
lucid-auth-service (token introspection) plus server-management access registration
without local JWT verification against gateway .env.secrets. Other callers keep
local JWT validation when a Bearer token is supplied.
"""


import uuid
from typing import List, Optional, Tuple

from fastapi import Request
from starlette.responses import JSONResponse

from api.app.config import get_settings
from api.app.services.access_orchestrator import resolve_trusted_gui_access
from api.app.services.gui_alignment import is_trusted_gui_caller

try:
    from api.app.utils.logging import get_logger, setup_logging

    logger = get_logger()
    settings = get_settings()
    setup_logging(settings)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)
    settings = get_settings()

# Caller identity for aligned GUI services (must match lucid_service / compose_service / container_name)
HEADER_CALLING_SERVICE = "X-Lucid-Calling-Service"
HEADER_INTERNAL_TOKEN = "X-Lucid-Internal-Token"
HEADER_CORRELATION = "X-Lucid-Correlation-Id"


class AuthMiddleware:
    """Authentication middleware for request processing"""

    PUBLIC_PATHS: List[str] = [
        "/health",
        "/api/v1/meta/info",
        "/api/v1/meta/health",
        "/api/v1/meta/version",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/auth/verify",
        "/api/v1/auth/refresh",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]

    def __init__(self, app):
        self.app = app
        self._settings = get_settings()
        self.jwt_algorithm = self._settings.JWT_ALGORITHM
        self.jwt_secret = self._settings.JWT_SECRET_KEY
        logger.info("AuthMiddleware initialized (GUI delegated auth supported)")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = request.url.path

        if self._is_public_endpoint(path):
            await self.app(scope, receive, send)
            return

        auth_header = request.headers.get("Authorization")
        if not auth_header:
            await self.app(scope, receive, send)
            return

        if not auth_header.startswith("Bearer "):
            response = JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "LUCID_ERR_2001",
                        "message": "Invalid authorization header format",
                    }
                },
            )
            await response(scope, receive, send)
            return

        token = auth_header[7:]
        if not token.strip():
            response = JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "LUCID_ERR_2001",
                        "message": "Invalid authorization header format",
                    }
                },
            )
            await response(scope, receive, send)
            return

        self._settings = get_settings()
        calling = request.headers.get(HEADER_CALLING_SERVICE)
        alignment_path = self._settings.GUI_SERVICES_ALIGNMENT_PATH

        if is_trusted_gui_caller(calling, alignment_path):
            if not self._internal_peer_ok(request):
                response = JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "LUCID_ERR_2004",
                            "message": "Forbidden",
                        }
                    },
                )
                await response(scope, receive, send)
                return

            corr = request.headers.get(HEADER_CORRELATION) or str(uuid.uuid4())
            ok, user_data, err_code = await resolve_trusted_gui_access(
                self._settings,
                authorization_header=auth_header,
                calling_service=calling.strip(),
                correlation_id=corr,
            )
            if not ok:
                status_code = 503 if err_code == "LUCID_ERR_5008" else 401
                if err_code == "LUCID_ERR_2004":
                    status_code = 403
                response = JSONResponse(
                    status_code=status_code,
                    content={
                        "error": {
                            "code": err_code or "LUCID_ERR_2001",
                            "message": "Access denied"
                            if status_code == 403
                            else (
                                "Service temporarily unavailable"
                                if status_code == 503
                                else "Authentication required"
                            ),
                        }
                    },
                )
                await response(scope, receive, send)
                return

            scope["state"] = scope.get("state", {})
            scope["state"]["user"] = user_data
            await self.app(scope, receive, send)
            return

        is_valid, user_data = await self._validate_token_local(token)
        if not is_valid:
            response = JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "LUCID_ERR_2001",
                        "message": "Invalid or expired token",
                    }
                },
            )
            await response(scope, receive, send)
            return

        if user_data:
            scope["state"] = scope.get("state", {})
            scope["state"]["user"] = user_data

        await self.app(scope, receive, send)

    def _internal_peer_ok(self, request: Request) -> bool:
        if not self._settings.GUI_TRUST_REQUIRE_INTERNAL_TOKEN:
            return True
        expected = self._settings.LUCID_INTERNAL_SERVICE_TOKEN
        if not expected:
            logger.warning("GUI_TRUST_REQUIRE_INTERNAL_TOKEN set but LUCID_INTERNAL_SERVICE_TOKEN empty")
            return False
        got = request.headers.get(HEADER_INTERNAL_TOKEN)
        return bool(got) and got == expected

    def _is_public_endpoint(self, path: str) -> bool:
        return any(path.startswith(public_path) for public_path in self.PUBLIC_PATHS)

    async def _validate_token_local(self, token: str) -> Tuple[bool, Optional[dict]]:
        try:
            from jose import JWTError, jwt

            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
            )
            user_data = {
                "user_id": payload.get("sub") or payload.get("user_id"),
                "email": payload.get("email"),
                "role": payload.get("role", "USER"),
                "source": "local-jwt",
            }
            if not user_data["user_id"]:
                return False, None
            return True, user_data
        except JWTError as e:
            logger.warning("JWT validation failed: %s", e)
            return False, None
        except Exception as e:
            logger.error("Token validation error: %s", e)
            return False, None
