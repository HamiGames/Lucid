# Path: 03-api-gateway/api/app/middleware/auth.py
# Very basic API key header check middleware (stub).
# Pattern follows FastAPI's middleware docs. :contentReference[oaicite:3]{index=3}

import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

API_KEY = os.getenv("API_KEY", "").strip()
API_KEY_HEADER = os.getenv("API_KEY_HEADER", "X-API-Key")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Allow health checks without auth
        if request.url.path.startswith("/health") or request.url.path.startswith(
            "/db/health"
        ):
            return await call_next(request)

        if API_KEY:
            supplied = request.headers.get(API_KEY_HEADER, "")
            if supplied != API_KEY:
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        # If no API_KEY set, pass-through (dev mode)
        return await call_next(request)
