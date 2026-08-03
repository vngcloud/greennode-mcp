"""Passthrough auth: the server never mints or refreshes tokens.

BaseClient requires a token_manager, but in passthrough mode every upstream
call carries the CALLER's bearer token (set on mcp_core.http.user_token_var by
the HTTP middleware or the stdio seed in server.main). This stub satisfies
BaseClient's constructor and exists ONLY as a loud guard: if get_token() is
ever called, a code path forgot to set the user token. It is never reached on
the happy path.
"""

from __future__ import annotations


class PassthroughTokenManager:
    """No-op token manager for passthrough mode (guard, never a minter)."""

    _expires_at: float = 0

    async def get_token(self) -> str:
        """Raise: passthrough mode must never mint — the user token must be set per request."""
        raise RuntimeError(
            "passthrough mode: no inbound bearer token was set on this request "
            "(user_token_var is unset). Every upstream call must carry the caller's token."
        )
