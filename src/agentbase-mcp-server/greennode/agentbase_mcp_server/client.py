"""HTTP client for the Agentbase API (passthrough, built on greennode.mcp_core)."""

from __future__ import annotations

from greennode.agentbase_mcp_server.auth import PassthroughTokenManager
from greennode.agentbase_mcp_server.config import AgentbaseConfig
from greennode.mcp_core.http import BaseClient


class AgentbaseClient(BaseClient):
    """Async client for the Agentbase API.

    Inherits timeout (30s), 5xx/conn-error retry+backoff, error mapping, and
    401 handling from BaseClient. Auth is passthrough: the caller's bearer
    token is read from user_token_var per request; the token_manager passed
    here is the PassthroughTokenManager guard (never used on the happy path).
    """

    def __init__(self, config: AgentbaseConfig, token_manager: PassthroughTokenManager) -> None:
        super().__init__(config, token_manager, default_service="policy")
