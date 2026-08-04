"""Introspect FastMCP-generated inputSchema/outputSchema for correctness."""

from __future__ import annotations

from greennode.agentbase_mcp_server.auth import PassthroughTokenManager
from greennode.agentbase_mcp_server.client import AgentbaseClient
from greennode.agentbase_mcp_server.config import load_config
from greennode.agentbase_mcp_server.discovery_cache import DiscoveryCache
from greennode.agentbase_mcp_server.policy_handler import PolicyHandler
from greennode.agentbase_mcp_server.server import create_server


def _server(allow_write=True):
    mcp = create_server(allow_write=allow_write)
    client = AgentbaseClient(load_config(env={}), PassthroughTokenManager())
    PolicyHandler(mcp, None, client, DiscoveryCache(), allow_write=allow_write)
    return mcp


def test_list_tools_have_no_paging_params():
    mcp = _server()
    for name in ("list_policy_groups", "list_policies"):
        tool = mcp._tool_manager.get_tool(name)
        props = tool.parameters["properties"]
        assert "page" not in props, name
        assert "page_size" not in props, name
        assert "size" not in props, name


def test_decision_body_user_type_is_enum():
    mcp = _server()
    tool = mcp._tool_manager.get_tool("get_authorization_decision")
    # FastMCP inlines nested DTOs into a top-level $defs; body is a $ref.
    defs = tool.parameters["$defs"]
    assert defs["DecisionUser"]["properties"]["type"]["enum"] == ["iam", "jwt"]


def test_group_id_required_on_path_tools():
    mcp = _server()
    for name in ("get_policy_group", "list_policies", "delete_policy_group"):
        tool = mcp._tool_manager.get_tool(name)
        assert "group_id" in tool.parameters["required"], name


def test_write_tools_require_body():
    mcp = _server()
    for name in ("create_policy_group", "create_policy", "update_policy_group", "update_policy"):
        tool = mcp._tool_manager.get_tool(name)
        assert "body" in tool.parameters["required"], name
