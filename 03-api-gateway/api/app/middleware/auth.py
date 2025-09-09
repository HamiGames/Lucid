from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import os


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Simple API key middleware.
    Blocks requests if required API_KEY is set and the incoming request
    does not include a matching 'x-api-key' header.
    """

    async def dispatch(self, request, call_next):
        api_key_required = os.getenv("API_KEY")
        header_key = request.headers.get("x-api-key")

        if api_key_required and header_key != api_key_required:
            return JSONResponse(
                {"detail": "Unauthorized"}, status_code=401
            )

        return await call_next(request)
