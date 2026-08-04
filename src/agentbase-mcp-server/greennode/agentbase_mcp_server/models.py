"""Pydantic DTOs and response models for the Agentbase policy service.

All *Dto request bodies set extra="forbid" and mirror the wire field names
(camelCase). Field shapes come from registry.generated.json (policy.* ops).
Response models are plain BaseModel with from_api classmethods.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from typing import Any, Literal


# --- Nested models (shared by create/update policy DTOs) ---


class Statement(BaseModel):
    """A policy statement (actions/effect/resources + optional principal/condition)."""

    actions: list[str] = Field(default_factory=list, description="Allowed/denied actions")
    effect: str = Field(..., description="Effect, e.g. 'allow' or 'deny'")
    resources: list[str] = Field(default_factory=list, description="Resource selectors")
    principal: str | None = Field(None, description="Optional principal selector")
    condition: dict[str, Any] | None = Field(
        None, description="Optional condition map (operator -> value)"
    )


class DecisionUser(BaseModel):
    """End user being evaluated in a decision request."""

    id: str = Field(..., description="User id")
    type: Literal["iam", "jwt"] = Field(..., description='User type: "iam" or "jwt"')


class PolicyAction(BaseModel):
    """The JSON-RPC action being authorized in a decision request."""

    jsonrpc: str = Field(..., description="JSON-RPC version, e.g. '2.0'")
    method: str = Field(..., description="The MCP/JSON-RPC method being authorized")
    params: dict[str, Any] | None = Field(
        None, description="Optional {name, arguments} of the called tool"
    )
    id: Any = Field(None, description="Optional JSON-RPC request id")


# --- Request DTOs (extra="forbid") ---


class CreatePolicyGroupDto(BaseModel):
    """Body for POST /api/v1/policy-groups (create a policy group)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Policy group name")
    description: str | None = Field(None, description="Optional description")


class UpdatePolicyGroupDto(BaseModel):
    """Body for PUT /api/v1/policy-groups/{group_id} (partial update)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, description="New name (optional)")
    description: str | None = Field(None, description="New description (optional)")


class CreatePolicyDto(BaseModel):
    """Body for POST /api/v1/policy-groups/{group_id}/policies (create a policy)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Policy name")
    statement: Statement = Field(..., description="The policy statement")
    active: bool | None = Field(None, description="Whether the policy is active")
    description: str | None = Field(None, description="Optional description")


class UpdatePolicyDto(BaseModel):
    """Body for PUT .../policies/{policy_id} (partial update — all fields optional)."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(None, description="New name (optional)")
    statement: Statement | None = Field(None, description="New statement (optional)")
    active: bool | None = Field(None, description="Whether active (optional)")
    description: str | None = Field(None, description="New description (optional)")


class AuthorizationDecisionDto(BaseModel):
    """Body for POST /internal/.../decisions (POST-but-read: returns allow/deny, no state change)."""

    model_config = ConfigDict(extra="forbid")

    action: PolicyAction = Field(..., description="The action to evaluate")
    policyGroupId: str = Field(..., description="Policy group id to evaluate against")
    user: DecisionUser = Field(..., description="The end user being evaluated")
    context: dict[str, Any] | None = Field(None, description="Optional evaluation context")
    principal: dict[str, Any] | None = Field(None, description="Optional principal map")


# --- Response models (plain BaseModel, from_api) ---


class PolicyGroupData(BaseModel):
    """One policy group."""

    id: str = Field("", description="Policy group id")
    name: str = Field("", description="Policy group name")
    description: str = Field("", description="Policy group description")

    @classmethod
    def from_api(cls, data: dict) -> PolicyGroupData:
        """Build a PolicyGroupData from a raw API dict."""
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
        )


class PolicyGroupListData(BaseModel):
    """Wrapper for list_policy_groups output (structured output)."""

    items: list[PolicyGroupData] = Field(default_factory=list, description="Policy groups")
    total: int = Field(0, description="Total count reported by the API")

    @classmethod
    def from_api(cls, items: list[dict], total: int = 0) -> PolicyGroupListData:
        """Build a PolicyGroupListData from raw API items and a total count."""
        return cls(items=[PolicyGroupData.from_api(i) for i in items], total=total)


class PolicyData(BaseModel):
    """One policy."""

    id: str = Field("", description="Policy id")
    name: str = Field("", description="Policy name")
    active: bool = Field(False, description="Whether the policy is active")
    description: str = Field("", description="Policy description")
    statement: Statement | None = Field(None, description="The policy statement")

    @classmethod
    def from_api(cls, data: dict) -> PolicyData:
        """Build a PolicyData from a raw API dict."""
        stmt = data.get("statement")
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            active=data.get("active", False),
            description=data.get("description", ""),
            statement=Statement(**stmt) if isinstance(stmt, dict) else None,
        )


class PolicyListData(BaseModel):
    """Wrapper for list_policies output."""

    items: list[PolicyData] = Field(default_factory=list, description="Policies")
    total: int = Field(0, description="Total count reported by the API")

    @classmethod
    def from_api(cls, items: list[dict], total: int = 0) -> PolicyListData:
        """Build a PolicyListData from raw API items and a total count."""
        return cls(items=[PolicyData.from_api(i) for i in items], total=total)


class ConditionOperatorListData(BaseModel):
    """Wrapper for list_condition_operators output."""

    operators: list[str] = Field(default_factory=list, description="Supported condition operators")

    @classmethod
    def from_api(cls, data: Any) -> ConditionOperatorListData:
        """Build a ConditionOperatorListData from a raw API response (list or dict)."""
        if isinstance(data, list):
            return cls(operators=[str(o) for o in data])
        if isinstance(data, dict):
            ops = data.get("items") or data.get("operators") or data.get("data") or []
            return cls(operators=[str(o) for o in ops])
        return cls()


class AuthorizationDecisionResult(BaseModel):
    """Result of get_authorization_decision: allow/deny + reasons."""

    decision: str = Field("", description="Decision, e.g. 'allow' or 'deny'")
    matchedPolicies: list[dict[str, Any]] = Field(
        default_factory=list, description="Policies matched by the decision"
    )
    raw: dict[str, Any] | None = Field(None, description="Raw response (debug)")

    @classmethod
    def from_api(cls, data: dict) -> AuthorizationDecisionResult:
        """Build an AuthorizationDecisionResult from a raw API dict."""
        return cls(
            decision=data.get("decision", data.get("effect", "")),
            matchedPolicies=data.get("matchedPolicies") or data.get("matched_policies") or [],
            raw=data,
        )
