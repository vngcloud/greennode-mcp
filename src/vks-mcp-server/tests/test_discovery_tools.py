"""Tests for discovery tools."""

from __future__ import annotations

import httpx
import pytest
import respx
from greennode.vks_mcp_server.auth import TokenManager
from greennode.vks_mcp_server.client import VksClient
from greennode.vks_mcp_server.config import load_config
from greennode.vks_mcp_server.discovery_handler import (
    _flavor_list,
    _require_project_id,
    _secgroup_list,
    _sshkey_list,
    _subnet_list,
    _suggest_group,
    _vpc_list,
)


VSERVER_BASE = "https://hcm-3.api.vngcloud.vn/vserver/vserver-gateway"
IAM_URL = "https://iamapis.vngcloud.vn/accounts-api/v1/auth/token"
PID = "pro-test-0001"


def _mock_iam(mock):
    mock.post(IAM_URL).mock(
        return_value=httpx.Response(200, json={"accessToken": "tok", "expiresIn": 1800})
    )


@pytest.fixture
def config(sample_config):
    return load_config(sample_config)


@pytest.fixture
def client(config):
    return VksClient(config, TokenManager(config))


@respx.mock
@pytest.mark.asyncio
async def test_vpc_list(config, client):
    _mock_iam(respx.mock)
    respx.get(f"{VSERVER_BASE}/v2/{PID}/networks").mock(
        return_value=httpx.Response(
            200,
            json={
                "listData": [
                    {
                        "id": "net-1",
                        "displayName": "vpc-prod",
                        "cidr": "10.0.0.0/16",
                        "status": "ACTIVE",
                    }
                ],
                "totalItem": 1,
            },
        )
    )
    result = await _vpc_list(config, client)
    assert "vpc-prod" in result
    assert "net-1" in result
    assert "10.0.0.0/16" in result


@respx.mock
@pytest.mark.asyncio
async def test_vpc_list_empty(config, client):
    _mock_iam(respx.mock)
    respx.get(f"{VSERVER_BASE}/v2/{PID}/networks").mock(
        return_value=httpx.Response(200, json={"listData": []})
    )
    result = await _vpc_list(config, client)
    assert "No VPC" in result


@respx.mock
@pytest.mark.asyncio
async def test_subnet_list(config, client):
    _mock_iam(respx.mock)
    vpc_id = "net-1"
    respx.get(f"{VSERVER_BASE}/v2/{PID}/networks/{vpc_id}/subnets").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"uuid": "sub-1", "name": "subnet-a", "cidr": "10.0.1.0/24", "status": "ACTIVE"}
            ],
        )
    )
    result = await _subnet_list(config, client, vpc_id=vpc_id)
    assert "subnet-a" in result
    assert "sub-1" in result


@pytest.mark.asyncio
async def test_subnet_list_rejects_bad_vpc_id(config, client):
    with pytest.raises(ValueError):
        await _subnet_list(config, client, vpc_id="bad id/../x")


def test_suggest_group_classifies():
    assert _suggest_group({"cpu": 2, "memory": 4, "gpu": 1}) == "AI/GPU"
    assert _suggest_group({"cpu": 2, "memory": 4, "gpu": 0}) == "Dev/test"
    assert _suggest_group({"cpu": 8, "memory": 16, "gpu": 0}) == "Compute"
    assert _suggest_group({"cpu": 4, "memory": 32, "gpu": 0}) == "RAM cao"
    assert _suggest_group({"cpu": 4, "memory": 8, "gpu": 0}) == "Cân bằng"


@respx.mock
@pytest.mark.asyncio
async def test_flavor_list(config, client):
    _mock_iam(respx.mock)
    respx.get(f"{VSERVER_BASE}/v1/{PID}/flavors/customs/clusters").mock(
        return_value=httpx.Response(
            200,
            json=[
                {
                    "flavorId": "flv-1",
                    "name": "2c_4g",
                    "cpu": 2,
                    "memory": 4,
                    "gpu": 0,
                    "group": "standard",
                },
                {
                    "flavorId": "flv-2",
                    "name": "8c_16g",
                    "cpu": 8,
                    "memory": 16,
                    "gpu": 0,
                    "group": "standard",
                },
            ],
        )
    )
    result = await _flavor_list(config, client)
    assert "2c_4g" in result and "flv-1" in result
    assert "8c_16g" in result
    assert "Dev/test" in result
    assert "Compute" in result


@respx.mock
@pytest.mark.asyncio
async def test_flavor_list_filters_by_need(config, client):
    _mock_iam(respx.mock)
    respx.get(f"{VSERVER_BASE}/v1/{PID}/flavors/customs/clusters").mock(
        return_value=httpx.Response(
            200,
            json=[
                {"flavorId": "flv-1", "name": "2c_4g", "cpu": 2, "memory": 4, "gpu": 0},
                {"flavorId": "flv-2", "name": "8c_16g", "cpu": 8, "memory": 16, "gpu": 0},
            ],
        )
    )
    result = await _flavor_list(config, client, need="Compute")
    assert "8c_16g" in result
    assert "2c_4g" not in result


@respx.mock
@pytest.mark.asyncio
async def test_sshkey_list(config, client):
    _mock_iam(respx.mock)
    respx.get(f"{VSERVER_BASE}/v2/{PID}/sshKeys").mock(
        return_value=httpx.Response(
            200,
            json={"listData": [{"id": "ssh-1", "name": "my-key"}], "totalItem": 1},
        )
    )
    result = await _sshkey_list(config, client)
    assert "my-key" in result
    assert "ssh-1" in result


@respx.mock
@pytest.mark.asyncio
async def test_sshkey_list_empty(config, client):
    _mock_iam(respx.mock)
    respx.get(f"{VSERVER_BASE}/v2/{PID}/sshKeys").mock(
        return_value=httpx.Response(200, json={"listData": []})
    )
    result = await _sshkey_list(config, client)
    assert "No SSH key" in result


@respx.mock
@pytest.mark.asyncio
async def test_secgroup_list(config, client):
    _mock_iam(respx.mock)
    respx.get(f"{VSERVER_BASE}/v2/{PID}/secgroups").mock(
        return_value=httpx.Response(
            200,
            json={
                "listData": [
                    {
                        "id": "secg-1",
                        "name": "default",
                        "description": "default sg",
                        "status": "ACTIVE",
                    }
                ]
            },
        )
    )
    result = await _secgroup_list(config, client)
    assert "default" in result
    assert "secg-1" in result


@respx.mock
@pytest.mark.asyncio
async def test_require_project_id_uses_configured(config, client):
    """A configured project_id is returned without calling vServer."""
    config.project_id = "pro-test-0001"
    pid = await _require_project_id(config, client, region=None)
    assert pid == "pro-test-0001"


@respx.mock
@pytest.mark.asyncio
async def test_require_project_id_autodiscovers(config, client):
    """When project_id is unset, it is fetched from /v1/projects and cached."""
    config.project_id = None
    _mock_iam(respx.mock)
    route = respx.get(f"{VSERVER_BASE}/v1/projects").mock(
        return_value=httpx.Response(
            200, json={"projects": [{"projectId": "pro-disc-9999", "userId": "u1"}]}
        )
    )
    pid = await _require_project_id(config, client, region=None)
    assert pid == "pro-disc-9999"
    assert config.project_id == "pro-disc-9999"  # cached
    # second call must not hit the API again
    pid2 = await _require_project_id(config, client, region=None)
    assert pid2 == "pro-disc-9999"
    assert route.call_count == 1


@respx.mock
@pytest.mark.asyncio
async def test_require_project_id_no_project_errors(config, client):
    """An empty project list yields a clear error."""
    config.project_id = None
    _mock_iam(respx.mock)
    respx.get(f"{VSERVER_BASE}/v1/projects").mock(
        return_value=httpx.Response(200, json={"projects": []})
    )
    with pytest.raises(ValueError, match="project_id"):
        await _require_project_id(config, client, region=None)
