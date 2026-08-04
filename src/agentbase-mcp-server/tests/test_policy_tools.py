"""Tests for the policy service tools."""

from __future__ import annotations

import httpx
import pytest
import respx
from greennode.agentbase_mcp_server.discovery_cache import DiscoveryCache
from greennode.agentbase_mcp_server.models import (
    ConditionOperatorListData,
    PolicyGroupData,
    PolicyGroupListData,
    PolicyListData,
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
