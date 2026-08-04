"""HTTP passthrough middleware: gate + forward the caller's bearer token.

Every POST /mcp must carry Authorization: Bearer <token>; missing/empty -> 401
(passthrough-only — no service account to fall back to). The token is scoped
to the request via mcp_core.http.user_token_var, so every downstream Agentbase
call runs as that caller. Reset in finally so concurrent requests never leak.
"""

from __future__ import annotations

from greennode.mcp_core.http import user_token_var
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class PassthroughIdentityMiddleware(BaseHTTPMiddleware):
    """Require + forward the caller's IAM bearer token (passthrough only)."""

    async def dispatch(self, request: Request, call_next):
        """Gate on Authorization; seed user_token_var for the request scope."""
        if request.url.path == "/health":
            return await call_next(request)
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer ") or not auth[7:].strip():
            return Response(
                "Unauthorized: provide the caller's IAM bearer token in the "
                "Authorization header. This server runs passthrough-only and "
                "holds no service-account credentials.",
                status_code=401,
                headers={"WWW-Authenticate": "Bearer"},
            )
        ctx_token = user_token_var.set(auth[7:].strip())
        try:
            return await call_next(request)
        finally:
            user_token_var.reset(ctx_token)
