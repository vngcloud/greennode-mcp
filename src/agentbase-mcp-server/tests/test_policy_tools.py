"""Tests for the policy service tools."""

from __future__ import annotations

import httpx
import pytest
import respx
from greennode.agentbase_mcp_server.discovery_cache import DiscoveryCache
from greennode.agentbase_mcp_server.models import (
    AuthorizationDecisionDto,
    ConditionOperatorListData,
    CreatePolicyDto,
    CreatePolicyGroupDto,
    DecisionUser,
    PolicyAction,
    PolicyGroupData,
    PolicyGroupListData,
    PolicyListData,
    Statement,
    UpdatePolicyGroupDto,
)
from greennode.agentbase_mcp_server.policy_handler import (
    _condition_operators_list,
    _policies_list,
    _policy_group_get,
    _policy_groups_list,
)


POLICY_BASE = "https://agentbase.api.vngcloud.vn/policy"


@respx.mock
async def test_list_condition_operators_cached(policy_client):
    respx.get(f"{POLICY_BASE}/api/v1/policies/condition-operators").mock(
        return_value=httpx.Response(200, json={"items": ["Equals", "NotEquals"]})
    )
    cache = DiscoveryCache()
    r1 = await _condition_operators_list(policy_client, cache, refresh=False)
    await _condition_operators_list(policy_client, cache, refresh=False)
    assert isinstance(r1, ConditionOperatorListData)
    assert r1.operators == ["Equals", "NotEquals"]
    # Second call is cached — only one upstream hit.
    assert len(respx.mock.calls) == 1


@respx.mock
async def test_list_condition_operators_refresh_bypasses_cache(policy_client):
    respx.get(f"{POLICY_BASE}/api/v1/policies/condition-operators").mock(
        return_value=httpx.Response(200, json={"items": ["Equals"]})
    )
    cache = DiscoveryCache()
    await _condition_operators_list(policy_client, cache, refresh=False)
    await _condition_operators_list(policy_client, cache, refresh=True)
    assert len(respx.mock.calls) == 2


@respx.mock
async def test_list_policy_groups_pages_and_forwards_bearer(policy_client):
    respx.get(f"{POLICY_BASE}/api/v1/policy-groups").mock(
        return_value=httpx.Response(
            200,
            json={"items": [{"id": "g1", "name": "a"}, {"id": "g2", "name": "b"}], "totalItem": 2},
        )
    )
    r = await _policy_groups_list(policy_client, DiscoveryCache(), params={})
    assert isinstance(r, PolicyGroupListData)
    assert [g.id for g in r.items] == ["g1", "g2"]
    # Core invariant: the caller's bearer was forwarded upstream.
    assert respx.mock.calls[0].request.headers["Authorization"] == "Bearer test-bearer"


@respx.mock
async def test_get_policy_group(policy_client):
    respx.get(f"{POLICY_BASE}/api/v1/policy-groups/g-1").mock(
        return_value=httpx.Response(200, json={"id": "g-1", "name": "n", "description": "d"})
    )
    r = await _policy_group_get(policy_client, group_id="g-1")
    assert isinstance(r, PolicyGroupData) and r.id == "g-1"


def test_get_policy_group_rejects_bad_id(policy_client):
    with pytest.raises(ValueError):
        import asyncio

        asyncio.run(_policy_group_get(policy_client, group_id="../escape"))


@respx.mock
async def test_list_policies(policy_client):
    respx.get(f"{POLICY_BASE}/api/v1/policy-groups/g-1/policies").mock(
        return_value=httpx.Response(
            200, json={"items": [{"id": "p1", "name": "x"}], "totalItem": 1}
        )
    )
    r = await _policies_list(policy_client, group_id="g-1", params={})
    assert isinstance(r, PolicyListData) and r.items[0].id == "p1"


@respx.mock
async def test_list_policies_forwards_name_filter(policy_client):
    route = respx.get(f"{POLICY_BASE}/api/v1/policy-groups/g-1/policies").mock(
        return_value=httpx.Response(200, json={"items": [], "totalItem": 0})
    )
    await _policies_list(policy_client, group_id="g-1", params={"name": "foo"})
    assert route.calls.last.request.url.params["name"] == "foo"


@respx.mock
async def test_create_policy_group_sends_body_and_forwards_bearer(policy_client):
    route = respx.post(f"{POLICY_BASE}/api/v1/policy-groups").mock(
        return_value=httpx.Response(201, json={"id": "g-new", "name": "ng"})
    )
    from greennode.agentbase_mcp_server.policy_handler import PolicyHandler
    from mcp.server.fastmcp import FastMCP

    h = PolicyHandler(FastMCP("t"), None, policy_client, DiscoveryCache(), allow_write=True)
    out = await h.create_policy_group(body=CreatePolicyGroupDto(name="ng", description="d"))
    assert "g-new" in out
    sent = route.calls.last.request
    assert sent.headers["Authorization"] == "Bearer test-bearer"
    import json

    assert json.loads(sent.content) == {"name": "ng", "description": "d"}


@respx.mock
async def test_update_policy_group_partial_body(policy_client):
    route = respx.put(f"{POLICY_BASE}/api/v1/policy-groups/g-1").mock(
        return_value=httpx.Response(200, json={"id": "g-1"})
    )
    from greennode.agentbase_mcp_server.policy_handler import PolicyHandler
    from mcp.server.fastmcp import FastMCP

    h = PolicyHandler(FastMCP("t"), None, policy_client, DiscoveryCache(), allow_write=True)
    await h.update_policy_group(group_id="g-1", body=UpdatePolicyGroupDto(description="new"))
    import json

    assert json.loads(route.calls.last.request.content) == {"description": "new"}


@respx.mock
async def test_delete_policy_group_uses_delete(policy_client):
    respx.delete(f"{POLICY_BASE}/api/v1/policy-groups/g-1").mock(return_value=httpx.Response(204))
    from greennode.agentbase_mcp_server.policy_handler import PolicyHandler
    from mcp.server.fastmcp import FastMCP

    h = PolicyHandler(FastMCP("t"), None, policy_client, DiscoveryCache(), allow_write=True)
    out = await h.delete_policy_group(group_id="g-1")
    assert "g-1" in out


@respx.mock
async def test_create_policy_sends_nested_statement(policy_client):
    route = respx.post(f"{POLICY_BASE}/api/v1/policy-groups/g-1/policies").mock(
        return_value=httpx.Response(201, json={"id": "p-new"})
    )
    from greennode.agentbase_mcp_server.policy_handler import PolicyHandler
    from mcp.server.fastmcp import FastMCP

    h = PolicyHandler(FastMCP("t"), None, policy_client, DiscoveryCache(), allow_write=True)
    await h.create_policy(
        group_id="g-1",
        body=CreatePolicyDto(
            name="p", statement=Statement(effect="allow", actions=["a:b"], resources=["r"])
        ),
    )
    import json

    sent = json.loads(route.calls.last.request.content)
    assert sent["name"] == "p"
    assert sent["statement"]["effect"] == "allow"
    assert sent["statement"]["actions"] == ["a:b"]


@respx.mock
async def test_get_authorization_decision_reads_post(policy_client):
    respx.post(f"{POLICY_BASE}/internal/api/v1/gateways/gw/targets/tgt/decisions").mock(
        return_value=httpx.Response(200, json={"decision": "allow"})
    )
    from greennode.agentbase_mcp_server.policy_handler import (
        PolicyHandler,
    )
    from mcp.server.fastmcp import FastMCP

    h = PolicyHandler(FastMCP("t"), None, policy_client, DiscoveryCache(), allow_write=False)
    dto = AuthorizationDecisionDto(
        action=PolicyAction(jsonrpc="2.0", method="tools/call"),
        policyGroupId="g-1",
        user=DecisionUser(id="u1", type="iam"),
    )
    r = await h.get_authorization_decision(gateway_name="gw", target_name="tgt", body=dto)
    assert r.decision == "allow"


def test_get_authorization_decision_rejects_bad_gateway_id(policy_client):
    import asyncio
    from greennode.agentbase_mcp_server.models import (
        AuthorizationDecisionDto,
        DecisionUser,
        PolicyAction,
    )
    from greennode.agentbase_mcp_server.policy_handler import _authorization_decision_get

    dto = AuthorizationDecisionDto(
        action=PolicyAction(jsonrpc="2.0", method="m"),
        policyGroupId="g",
        user=DecisionUser(id="u", type="iam"),
    )
    with pytest.raises(ValueError):
        asyncio.run(_authorization_decision_get(policy_client, "../x", "tgt", dto))
