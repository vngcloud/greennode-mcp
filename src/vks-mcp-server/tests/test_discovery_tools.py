"""Tests for discovery tools."""

from __future__ import annotations

import httpx
import pytest
import respx
from greennode.vks_mcp_server.auth import TokenManager
from greennode.vks_mcp_server.client import VksClient
from greennode.vks_mcp_server.config import load_config
from greennode.vks_mcp_server.discovery_handler import (
    _subnet_list,
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
                    {"id": "net-1", "displayName": "vpc-prod", "cidr": "10.0.0.0/16", "status": "ACTIVE"}
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
