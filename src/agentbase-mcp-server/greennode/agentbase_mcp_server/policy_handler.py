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
    AuthorizationDecisionDto,
    AuthorizationDecisionResult,
    ConditionOperatorListData,
    CreatePolicyDto,
    CreatePolicyGroupDto,
    PolicyData,
    PolicyGroupData,
    PolicyGroupListData,
    PolicyListData,
    UpdatePolicyDto,
    UpdatePolicyGroupDto,
)
from greennode.agentbase_mcp_server.paging import fetch_all_agentbase_items
from greennode.agentbase_mcp_server.tool_annotations import DESTRUCTIVE, READ, WRITE
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


# --- Module-level logic (write + decision ops) ---


async def _policy_group_create(
    client: AgentbaseClient, body: CreatePolicyGroupDto
) -> PolicyGroupData:
    """POST /api/v1/policy-groups."""
    data = await client.post("/api/v1/policy-groups", json=body.model_dump(exclude_none=True))
    data = data or {}
    return PolicyGroupData.from_api(data)


async def _policy_group_update(
    client: AgentbaseClient, group_id: str, body: UpdatePolicyGroupDto
) -> PolicyGroupData:
    """PUT /api/v1/policy-groups/{group_id} (partial update)."""
    validate_id(group_id, "group_id")
    data = await client.put(
        f"/api/v1/policy-groups/{group_id}", json=body.model_dump(exclude_none=True)
    )
    data = data or {}
    return PolicyGroupData.from_api(data)


async def _policy_group_delete(client: AgentbaseClient, group_id: str) -> str:
    """DELETE /api/v1/policy-groups/{group_id}."""
    validate_id(group_id, "group_id")
    await client.delete(f"/api/v1/policy-groups/{group_id}")
    return f"Policy group {group_id} deleted."


async def _policy_create(
    client: AgentbaseClient, group_id: str, body: CreatePolicyDto
) -> PolicyData:
    """POST /api/v1/policy-groups/{group_id}/policies."""
    validate_id(group_id, "group_id")
    data = await client.post(
        f"/api/v1/policy-groups/{group_id}/policies",
        json=body.model_dump(exclude_none=True),
    )
    data = data or {}
    return PolicyData.from_api(data)


async def _policy_update(
    client: AgentbaseClient, group_id: str, policy_id: str, body: UpdatePolicyDto
) -> PolicyData:
    """PUT /api/v1/policy-groups/{group_id}/policies/{policy_id} (partial update)."""
    validate_id(group_id, "group_id")
    validate_id(policy_id, "policy_id")
    data = await client.put(
        f"/api/v1/policy-groups/{group_id}/policies/{policy_id}",
        json=body.model_dump(exclude_none=True),
    )
    data = data or {}
    return PolicyData.from_api(data)


async def _policy_delete(client: AgentbaseClient, group_id: str, policy_id: str) -> str:
    """DELETE /api/v1/policy-groups/{group_id}/policies/{policy_id}."""
    validate_id(group_id, "group_id")
    validate_id(policy_id, "policy_id")
    await client.delete(f"/api/v1/policy-groups/{group_id}/policies/{policy_id}")
    return f"Policy {policy_id} deleted."


async def _authorization_decision_get(
    client: AgentbaseClient,
    gateway_name: str,
    target_name: str,
    body: AuthorizationDecisionDto,
) -> AuthorizationDecisionResult:
    """POST /internal/api/v1/gateways/{gatewayName}/targets/{targetName}/decisions.

    POST-but-read: returns an allow/deny decision, mutates no state.
    """
    validate_id(gateway_name, "gateway_name")
    validate_id(target_name, "target_name")
    data = await client.post(
        f"/internal/api/v1/gateways/{gateway_name}/targets/{target_name}/decisions",
        json=body.model_dump(exclude_none=True),
    )
    data = data or {}
    return AuthorizationDecisionResult.from_api(data)


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

        # Write tools (only with --allow-write).
        if self.allow_write:
            self.mcp.tool(name="create_policy_group", annotations=WRITE)(self.create_policy_group)
            self.mcp.tool(name="update_policy_group", annotations=WRITE)(self.update_policy_group)
            self.mcp.tool(name="delete_policy_group", annotations=DESTRUCTIVE)(
                self.delete_policy_group
            )
            self.mcp.tool(name="create_policy", annotations=WRITE)(self.create_policy)
            self.mcp.tool(name="update_policy", annotations=WRITE)(self.update_policy)
            self.mcp.tool(name="delete_policy", annotations=DESTRUCTIVE)(self.delete_policy)

        # Decisions: POST-but-read — always registered, not gated.
        self.mcp.tool(name="get_authorization_decision", annotations=READ)(
            self.get_authorization_decision
        )

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

    async def create_policy_group(
        self,
        body: CreatePolicyGroupDto = Field(
            ...,
            description="CreatePolicyGroupDto: {name (required), description?}.",
        ),
    ) -> str:
        """Create a policy group.

        ## Requirements
        - Server must run with --allow-write.
        """
        result = await _policy_group_create(self.client, body)
        return f"Created policy group {result.id or result.name}."

    async def update_policy_group(
        self,
        group_id: str = Field(..., description="Policy group id to update."),
        body: UpdatePolicyGroupDto = Field(
            ...,
            description="Partial-update body: {name?, description?} — send only fields to change.",
        ),
    ) -> str:
        """Update a policy group (partial update).

        ## Requirements
        - Server must run with --allow-write.
        """
        result = await _policy_group_update(self.client, group_id=group_id, body=body)
        return f"Updated policy group {result.id or group_id}."

    async def delete_policy_group(
        self,
        group_id: str = Field(..., description="Policy group id to delete."),
    ) -> str:
        """Delete a policy group (destructive).

        ## Requirements
        - Server must run with --allow-write.
        """
        return await _policy_group_delete(self.client, group_id=group_id)

    async def create_policy(
        self,
        group_id: str = Field(..., description="Policy group id to create the policy in."),
        body: CreatePolicyDto = Field(
            ...,
            description="CreatePolicyDto: {name, statement{actions,effect,resources,principal?,condition?}, active?, description?}.",
        ),
    ) -> str:
        """Create a policy within a policy group.

        ## Requirements
        - Server must run with --allow-write.
        """
        result = await _policy_create(self.client, group_id=group_id, body=body)
        return f"Created policy {result.id or result.name}."

    async def update_policy(
        self,
        group_id: str = Field(..., description="Policy group id."),
        policy_id: str = Field(..., description="Policy id to update."),
        body: UpdatePolicyDto = Field(
            ...,
            description="Partial-update body — send only fields to change.",
        ),
    ) -> str:
        """Update a policy (partial update).

        ## Requirements
        - Server must run with --allow-write.
        """
        result = await _policy_update(
            self.client, group_id=group_id, policy_id=policy_id, body=body
        )
        return f"Updated policy {result.id or policy_id}."

    async def delete_policy(
        self,
        group_id: str = Field(..., description="Policy group id."),
        policy_id: str = Field(..., description="Policy id to delete."),
    ) -> str:
        """Delete a policy (destructive).

        ## Requirements
        - Server must run with --allow-write.
        """
        return await _policy_delete(self.client, group_id=group_id, policy_id=policy_id)

    async def get_authorization_decision(
        self,
        gateway_name: str = Field(..., description="Gateway name (path id)."),
        target_name: str = Field(..., description="Target name (path id)."),
        body: AuthorizationDecisionDto = Field(
            ...,
            description="AuthorizationDecisionDto: {action, policyGroupId, user{id,type}, context?, principal?}.",
        ),
    ) -> AuthorizationDecisionResult:
        """Evaluate an authorization request — returns allow/deny (POST-but-read, no state change)."""
        return await _authorization_decision_get(
            self.client, gateway_name=gateway_name, target_name=target_name, body=body
        )
