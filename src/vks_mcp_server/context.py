"""Global context for MCP tools -- set by server.py at startup."""
from __future__ import annotations

from vks_mcp_server.config import VksConfig
from vks_mcp_server.auth import TokenManager
from vks_mcp_server.client import VksClient

config: VksConfig | None = None
token_manager: TokenManager | None = None
client: VksClient | None = None
