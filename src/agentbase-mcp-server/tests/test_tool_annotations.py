"""Assert ToolAnnotations and allow_write gating are correct."""

from __future__ import annotations

from greennode.agentbase_mcp_server.auth import PassthroughTokenManager
from greennode.agentbase_mcp_server.client import AgentbaseClient
from greennode.agentbase_mcp_server.config import load_config
from greennode.agentbase_mcp_server.discovery_cache import DiscoveryCache
from greennode.agentbase_mcp_server.policy_handler import PolicyHandler
from greennode.agentbase_mcp_server.server import create_server


def _server(allow_write):
    mcp = create_server(allow_write=allow_write)
    client = AgentbaseClient(load_config(env={}), PassthroughTokenManager())
    PolicyHandler(mcp, None, client, DiscoveryCache(), allow_write=allow_write)
    return mcp


def _annotations(mcp, name) -> tuple:
    tool = mcp._tool_manager._tools[name]
    a = tool.annotations
    return (a.readOnlyHint, a.destructiveHint)


def test_reads_are_readonly():
    mcp = _server(allow_write=False)
    for name in (
        "list_condition_operators",
        "list_policy_groups",
        "get_policy_group",
        "list_policies",
        "get_policy",
        "get_authorization_decision",
    ):
        ro, destr = _annotations(mcp, name)
        assert ro is True and destr is None, name


def test_writes_are_not_readonly_not_destructive():
    mcp = _server(allow_write=True)
    for name in ("create_policy_group", "update_policy_group", "create_policy", "update_policy"):
        ro, destr = _annotations(mcp, name)
        assert ro is False and destr is False, name


def test_deletes_are_destructive():
    mcp = _server(allow_write=True)
    for name in ("delete_policy_group", "delete_policy"):
        ro, destr = _annotations(mcp, name)
        assert ro is False and destr is True, name


def test_writes_absent_when_read_only():
    mcp = _server(allow_write=False)
    names = set(mcp._tool_manager._tools.keys())
    assert "create_policy_group" not in names
    assert "delete_policy" not in names


def test_decision_registered_read_only_mode():
    """get_authorization_decision is POST-but-read: registered even without allow_write."""
    mcp = _server(allow_write=False)
    assert "get_authorization_decision" in set(mcp._tool_manager._tools.keys())
