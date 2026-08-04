"""Policy service handler for the Agentbase MCP server (12 tools, two-tier).

Module-level _<op> functions hold the logic (testable without FastMCP); the
PolicyHandler class registers thin delegators. Ops map to verb_noun tools
(see package CLAUDE.md playbook). Path IDs go through validate_id; writes
gated behind allow_write; list_condition_operators is cached.

Reference of record for op/param/body shapes:
registry.generated.json (policy.* operations) in the source repo.
"""

from __future__ import annotations

from greennode.agentbase_mcp_server.client import AgentbaseClient
from greennode.agentbase_mcp_server.discovery_cache import DiscoveryCache
from greennode.agentbase_mcp_server.models import (
    ConditionOperatorListData,
    PolicyData,
    PolicyGroupData,
    PolicyGroupListData,
    PolicyListData,
)
from greennode.agentbase_mcp_server.paging import fetch_all_agentbase_items
from greennode.agentbase_mcp_server.tool_annotations import READ
from greennode.mcp_core.validators import validate_id
from pydantic import Field
from typing import Any


# --- Module-level logic (read ops) ---


async def _condition_operators_list(
    client: AgentbaseClient, cache: DiscoveryCache, refresh: bool = False
) -> ConditionOperatorListData:
    """GET /api/v1/policies/condition-operators (cached static reference data)."""

    async def fetch() -> ConditionOperatorListData:
        data = await client.get("/api/v1/policies/condition-operators", params=None)
        return ConditionOperatorListData.from_api(data)

    return await cache.get_or_fetch("list_condition_operators", ("only",), fetch, refresh=refresh)


async def _policy_groups_list(
    client: AgentbaseClient, cache: DiscoveryCache, params: dict[str, Any] | None
) -> PolicyGroupListData:
    """GET /api/v1/policy-groups (pages 1-based; not cached — per-caller mutable)."""
    items = await fetch_all_agentbase_items(client, "/api/v1/policy-groups", params=params)
    total = len(items)
    return PolicyGroupListData.from_api(items, total=total)


async def _policy_group_get(client: AgentbaseClient, group_id: str) -> PolicyGroupData:
    """GET /api/v1/policy-groups/{group_id}."""
    validate_id(group_id, "group_id")
    data = await client.get(f"/api/v1/policy-groups/{group_id}", params=None)
    data = data or {}
    return PolicyGroupData.from_api(data)


async def _policies_list(
    client: AgentbaseClient, group_id: str, params: dict[str, Any] | None
) -> PolicyListData:
    """GET /api/v1/policy-groups/{group_id}/policies (pages 1-based; not cached)."""
    validate_id(group_id, "group_id")
    items = await fetch_all_agentbase_items(
        client, f"/api/v1/policy-groups/{group_id}/policies", params=params
    )
    total = len(items)
    return PolicyListData.from_api(items, total=total)


async def _policy_get(client: AgentbaseClient, group_id: str, policy_id: str) -> PolicyData:
    """GET /api/v1/policy-groups/{group_id}/policies/{policy_id}."""
    validate_id(group_id, "group_id")
    validate_id(policy_id, "policy_id")
    data = await client.get(f"/api/v1/policy-groups/{group_id}/policies/{policy_id}", params=None)
    data = data or {}
    return PolicyData.from_api(data)


class PolicyHandler:
    """Register and serve the 12 Agentbase policy tools."""

    def __init__(
        self,
        mcp,
        config,
        client: AgentbaseClient,
        cache: DiscoveryCache,
        allow_write: bool = False,
    ):
        self.mcp = mcp
        self.config = config
        self.client = client
        self.cache = cache
        self.allow_write = allow_write

        # Read tools (always registered).
        self.mcp.tool(name="list_condition_operators", annotations=READ)(
            self.list_condition_operators
        )
        self.mcp.tool(name="list_policy_groups", annotations=READ)(self.list_policy_groups)
        self.mcp.tool(name="get_policy_group", annotations=READ)(self.get_policy_group)
        self.mcp.tool(name="list_policies", annotations=READ)(self.list_policies)
        self.mcp.tool(name="get_policy", annotations=READ)(self.get_policy)

        # Write tools (only with --allow-write) — added in Task 8.
        # if self.allow_write:
        #     ...

    async def list_condition_operators(
        self,
        refresh: bool = Field(False, description="Bypass the cache and re-fetch from the API."),
    ) -> ConditionOperatorListData:
        """List supported policy condition operators (cached static reference data)."""
        return await _condition_operators_list(self.client, self.cache, refresh=refresh)

    async def list_policy_groups(
        self,
        name: str | None = Field(None, description="Optional name filter."),
    ) -> PolicyGroupListData:
        """List policy groups (paginated server-side; returns all matching items)."""
        params: dict[str, Any] = {}
        if name:
            params["name"] = name
        return await _policy_groups_list(self.client, self.cache, params=params)

    async def get_policy_group(
        self,
        group_id: str = Field(..., description="Policy group id."),
    ) -> PolicyGroupData:
        """Get a single policy group by id."""
        return await _policy_group_get(self.client, group_id=group_id)

    async def list_policies(
        self,
        group_id: str = Field(..., description="Policy group id containing the policies."),
        name: str | None = Field(None, description="Optional name filter."),
    ) -> PolicyListData:
        """List policies within a policy group (paginated server-side)."""
        params: dict[str, Any] = {}
        if name:
            params["name"] = name
        return await _policies_list(self.client, group_id=group_id, params=params)

    async def get_policy(
        self,
        group_id: str = Field(..., description="Policy group id."),
        policy_id: str = Field(..., description="Policy id."),
    ) -> PolicyData:
        """Get a single policy by id within a policy group."""
        return await _policy_get(self.client, group_id=group_id, policy_id=policy_id)
