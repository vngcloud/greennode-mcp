"""Tests for registered tool input schemas via FastMCP introspection.

The existing handler tests call internal functions directly and bypass FastMCP
validation, so Literal / Field(ge,le) constraints are only observable on the
registered tool's inputSchema. These tests assert those constraints.
"""
from __future__ import annotations

import pytest
from mcp.server.fastmcp import FastMCP

from vks_mcp_server.auth import TokenManager
from vks_mcp_server.client import VksClient
from vks_mcp_server.config import load_config
from vks_mcp_server.cluster_handler import ClusterHandler
from vks_mcp_server.k8s_handler import K8sHandler
from vks_mcp_server.nodegroup_handler import NodeGroupHandler


@pytest.fixture
def config(sample_config):
    return load_config(sample_config)


@pytest.fixture
def client(config):
    return VksClient(config, TokenManager(config))


async def _schema_for(register, tool_name):
    """Register handler(s) on a fresh FastMCP and return a tool's inputSchema."""
    mcp = FastMCP("test")
    register(mcp)
    tools = await mcp.list_tools()
    return next(t for t in tools if t.name == tool_name).inputSchema


def _minimum(prop):
    """Extract the numeric 'minimum' whether top-level or inside anyOf (Optional)."""
    if "minimum" in prop:
        return prop["minimum"]
    for sub in prop.get("anyOf", []):
        if "minimum" in sub:
            return sub["minimum"]
    return None


@pytest.mark.asyncio
async def test_manage_k8s_resource_operation_is_enum(config, client):
    schema = await _schema_for(
        lambda mcp: K8sHandler(
            mcp, config, client, allow_write=True, allow_sensitive_data_access=True
        ),
        "manage_k8s_resource",
    )
    enum = schema["properties"]["operation"]["enum"]
    assert set(enum) == {"create", "replace", "patch", "delete", "read"}


@pytest.mark.asyncio
async def test_get_pod_logs_numeric_constraints(config, client):
    schema = await _schema_for(
        lambda mcp: K8sHandler(
            mcp, config, client, allow_write=True, allow_sensitive_data_access=True
        ),
        "get_pod_logs",
    )
    props = schema["properties"]
    assert props["tail_lines"]["minimum"] == 1
    assert props["limit_bytes"]["minimum"] == 1
    assert _minimum(props["since_seconds"]) == 0


@pytest.mark.asyncio
async def test_cluster_list_pagination_constraints(config, client):
    schema = await _schema_for(
        lambda mcp: ClusterHandler(mcp, config, client, allow_write=True),
        "cluster_list",
    )
    props = schema["properties"]
    assert _minimum(props["page"]) == 0
    assert _minimum(props["pageSize"]) == 1


@pytest.mark.asyncio
async def test_cluster_create_body_lists_valid_values(config, client):
    schema = await _schema_for(
        lambda mcp: ClusterHandler(mcp, config, client, allow_write=True),
        "cluster_create",
    )
    desc = schema["properties"]["body"]["description"]
    assert "RAPID" in desc and "STABLE" in desc
    assert "CILIUM_NATIVE_ROUTING" in desc
    assert "secondarySubnets" in desc
