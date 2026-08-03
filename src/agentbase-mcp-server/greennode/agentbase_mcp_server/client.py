"""HTTP client for the AGENTBASE API (built on greennode.mcp_core)."""

from __future__ import annotations

from greennode.agentbase_mcp_server.config import AgentbaseConfig
from greennode.mcp_core.auth import TokenManager
from greennode.mcp_core.http import BaseClient


class AgentbaseClient(BaseClient):
    """Async client for the AGENTBASE API (retry + token refresh from BaseClient)."""

    def __init__(self, config: AgentbaseConfig, token_manager: TokenManager) -> None:
        super().__init__(config, token_manager, default_service="agentbase")
