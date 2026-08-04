"""Tests for policy DTOs and response models."""

from __future__ import annotations

import pytest
from greennode.agentbase_mcp_server.models import (
    AuthorizationDecisionDto,
    CreatePolicyDto,
    CreatePolicyGroupDto,
    PolicyGroupData,
    PolicyGroupListData,
    Statement,
)
from pydantic import ValidationError


def test_create_policy_group_requires_name():
    with pytest.raises(ValidationError):
        CreatePolicyGroupDto()


def test_create_policy_group_rejects_extra_fields():
    with pytest.raises(ValidationError):
        CreatePolicyGroupDto(name="g", bogus=True)


def test_statement_optional_fields():
    s = Statement(actions=["a:b"], effect="allow", resources=["res:*"])
    assert s.effect == "allow"


def test_create_policy_requires_name_and_statement():
    with pytest.raises(ValidationError):
        CreatePolicyDto()


def test_create_policy_accepts_full_body():
    CreatePolicyDto(
        name="p",
        statement=Statement(effect="allow", actions=["x:y"], resources=["r"]),
    )


def test_decision_dto_requires_action_policy_group_user():
    with pytest.raises(ValidationError):
        AuthorizationDecisionDto()


def test_decision_dto_user_type_enum():
    from greennode.agentbase_mcp_server.models import DecisionUser

    with pytest.raises(ValidationError):
        DecisionUser(id="u", type="bogus")


def test_all_dtos_forbid_extra():
    for dto, kwargs in [
        (CreatePolicyGroupDto, {"name": "g"}),
        (CreatePolicyDto, {"name": "p", "statement": Statement(effect="allow")}),
    ]:
        with pytest.raises(ValidationError):
            dto(**kwargs, unexpected=True)


def test_policy_group_data_from_api():
    m = PolicyGroupData.from_api({"id": "pg-1", "name": "g", "description": "d"})
    assert m.id == "pg-1" and m.name == "g"


def test_policy_group_list_data_default_empty():
    m = PolicyGroupListData()
    assert m.items == []
