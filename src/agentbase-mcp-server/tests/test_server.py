"""Tests for create_server, /health, and tool registration."""

from __future__ import annotations

from greennode.agentbase_mcp_server.auth import PassthroughTokenManager
from greennode.agentbase_mcp_server.client import AgentbaseClient
from greennode.agentbase_mcp_server.config import load_config
from greennode.agentbase_mcp_server.discovery_cache import DiscoveryCache
from greennode.agentbase_mcp_server.policy_handler import PolicyHandler
from greennode.agentbase_mcp_server.server import create_server
from mcp.server.fastmcp import FastMCP


def _wire(allow_write=False):
    mcp = create_server(allow_write=allow_write)
    client = AgentbaseClient(load_config(env={}), PassthroughTokenManager())
    PolicyHandler(mcp, None, client, DiscoveryCache(), allow_write=allow_write)
    return mcp


def test_create_server_returns_fastmcp():
    assert isinstance(create_server(), FastMCP)


def test_read_only_server_registers_six_tools():
    mcp = _wire(allow_write=False)
    # 5 reads + 1 decision (always) = 6; writes gated off.
    tools = mcp._tool_manager._tools  # FastMCP internal tool registry
    names = set(tools.keys())
    for expected in [
        "list_condition_operators",
        "list_policy_groups",
        "get_policy_group",
        "list_policies",
        "get_policy",
        "get_authorization_decision",
    ]:
        assert expected in names, names
    # Writes absent.
    assert "create_policy_group" not in names


def test_write_server_registers_twelve_tools():
    mcp = _wire(allow_write=True)
    names = set(mcp._tool_manager._tools.keys())
    for expected in [
        "create_policy_group",
        "update_policy_group",
        "delete_policy_group",
        "create_policy",
        "update_policy",
        "delete_policy",
    ]:
        assert expected in names, names
    assert len(names) == 12, names


def test_health_endpoint():
    """The /health route is unauthenticated (open even with no bearer)."""
    from starlette.testclient import TestClient

    mcp = _wire(allow_write=False)
    app = mcp.streamable_http_app()
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
