"""Tests for the passthrough token-manager stub and the client."""

from __future__ import annotations

import pytest
from greennode.agentbase_mcp_server.auth import PassthroughTokenManager
from greennode.agentbase_mcp_server.client import AgentbaseClient
from greennode.agentbase_mcp_server.config import load_config


def test_passthrough_token_manager_refuses_without_user_token():
    """get_token() raises — passthrough never mints; the user_token_var must be set."""
    tm = PassthroughTokenManager()
    with pytest.raises(RuntimeError, match="passthrough mode"):
        import asyncio

        asyncio.run(tm.get_token())


def test_passthrough_token_manager_has_expires_at_zero():
    tm = PassthroughTokenManager()
    assert tm._expires_at == 0


def test_client_uses_policy_default_service():
    cfg = load_config(env={})
    client = AgentbaseClient(cfg, PassthroughTokenManager())
    assert client._default_service == "policy"
