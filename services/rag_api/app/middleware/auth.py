from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from services.rag_api.app.services.auth_service import decode_access_token, extract_bearer_token


PUBLIC_ROUTES = {
    "/",
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/auth/login",
}


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in PUBLIC_ROUTES:
            return await call_next(request)

        token = extract_bearer_token(request.headers.get("Authorization"))
        if token:
            try:
                payload = decode_access_token(token)
            except Exception as exc:
                detail = getattr(exc, "detail", "Invalid session token")
                return JSONResponse(status_code=401, content={"detail": detail})
            request.state.user_id = payload["sub"]
            request.state.user_email = payload.get("email")
            request.state.user_name = payload.get("name")
            return await call_next(request)

        return JSONResponse(status_code=401, content={"detail": "Authentication required"})
