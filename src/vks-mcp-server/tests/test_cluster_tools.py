"""Tests for cluster tools."""
from __future__ import annotations

import pytest
import respx
import httpx

from greennode.vks_mcp_server.config import load_config
from greennode.vks_mcp_server.auth import TokenManager
from greennode.vks_mcp_server.client import VksClient
from greennode.vks_mcp_server.cluster_handler import (
    _cluster_list,
    _cluster_delete_dryrun,
    _cluster_create_validate,
)

IAM_URL = "https://iamapis.vngcloud.vn/accounts-api/v1/auth/token"
VKS_BASE = "https://vks.api.vngcloud.vn"


def _mock_iam(mock: respx.MockRouter) -> None:
    mock.post(IAM_URL).mock(return_value=httpx.Response(
        200, json={"accessToken": "mocked-token", "expiresIn": 1800},
    ))


@pytest.fixture
def client(sample_config):
    config = load_config(sample_config)
    token_manager = TokenManager(config)
    return VksClient(config, token_manager)


# ---------------------------------------------------------------------------
# _cluster_list
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_cluster_list(client):
    """cluster_list calls GET /v1/clusters and formats the result."""
    _mock_iam(respx.mock)
    items = [{
        "name": "my-cluster", "uid": "uid-abc", "status": "ACTIVE",
        "version": "1.28", "nodeCount": 3, "createdAt": "2024-01-15T10:00:00Z",
    }]
    respx.get(f"{VKS_BASE}/v1/clusters").mock(
        return_value=httpx.Response(200, json={"items": items}),
    )
    result = await _cluster_list(client, {})
    assert len(result) == 1
    text = result[0].text
    assert "my-cluster" in text


@respx.mock
@pytest.mark.asyncio
async def test_cluster_list_with_pagination(client):
    """cluster_list passes page and pageSize as query params."""
    _mock_iam(respx.mock)
    respx.get(f"{VKS_BASE}/v1/clusters").mock(
        return_value=httpx.Response(200, json={"items": []}),
    )
    result = await _cluster_list(client, {"page": 2, "pageSize": 5})
    text = result[0].text
    assert "No clusters found" in text


# ---------------------------------------------------------------------------
# _cluster_delete_dryrun
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_cluster_delete_dryrun(client):
    """cluster_delete_dryrun fetches cluster + node-groups and warns user."""
    _mock_iam(respx.mock)
    cluster_id = "cid-xyz"
    cluster_data = {
        "uid": "cid-xyz", "name": "prod-cluster", "status": "ACTIVE",
        "version": "1.29", "nodeCount": 5,
    }
    node_groups = [
        {"uid": "ng-1", "name": "worker-ng", "nodeCount": 3},
        {"uid": "ng-2", "name": "gpu-ng", "nodeCount": 2},
    ]
    respx.get(f"{VKS_BASE}/v1/clusters/{cluster_id}").mock(
        return_value=httpx.Response(200, json=cluster_data),
    )
    respx.get(f"{VKS_BASE}/v1/clusters/{cluster_id}/node-groups").mock(
        return_value=httpx.Response(200, json={"items": node_groups}),
    )
    result = await _cluster_delete_dryrun(client, {"cluster_id": cluster_id})
    assert len(result) == 1
    text = result[0].text
    assert "YOU ARE ABOUT TO DELETE CLUSTER" in text


# ---------------------------------------------------------------------------
# _cluster_create_validate
# ---------------------------------------------------------------------------

_VALID_NODEGROUP = {
    "name": "worker-ng",
    "flavorId": "flav-001",
    "diskSize": 50,
    "diskType": "SSD",
    "securityGroups": ["sg-001"],
    "sshKeyId": "key-001",
    "upgradeConfig": {"strategy": "SURGE", "maxSurge": 1, "maxUnavailable": 1},
    "numNodes": 2,
    "enablePrivateNodes": True,
}

_VALID_BODY = {
    "name": "mycluster01",
    "vpcId": "vpc-001",
    "networkType": "CILIUM_OVERLAY",
    "version": "1.28",
    "releaseChannel": "STABLE",
    "cidr": "10.96.0.0/16",
    "enablePrivateCluster": False,
    "nodeGroups": [_VALID_NODEGROUP],
}


def test_cluster_create_validate_valid():
    """A fully valid body returns 'valid'."""
    result = _cluster_create_validate({"body": _VALID_BODY})
    assert len(result) == 1
    assert result[0].text == "valid"


def test_cluster_create_validate_bad_name():
    """Invalid cluster name returns an error mentioning 'name'."""
    body = {**_VALID_BODY, "name": "BAD_NAME!"}
    result = _cluster_create_validate({"body": body})
    text = result[0].text
    assert "name" in text.lower()
    assert text != "valid"


def test_cluster_create_validate_missing_fields():
    """Missing vpcId returns an error mentioning 'vpcId'."""
    body = {k: v for k, v in _VALID_BODY.items() if k != "vpcId"}
    result = _cluster_create_validate({"body": body})
    text = result[0].text
    assert "vpcId" in text
    assert text != "valid"


def test_cluster_create_validate_missing_network_type():
    """Missing networkType returns error."""
    body = {k: v for k, v in _VALID_BODY.items() if k != "networkType"}
    result = _cluster_create_validate({"body": body})
    text = result[0].text
    assert "networkType" in text


def test_cluster_create_validate_cilium_overlay_needs_cidr():
    """CILIUM_OVERLAY networkType without cidr returns an error."""
    body = {k: v for k, v in _VALID_BODY.items() if k != "cidr"}
    assert body["networkType"] == "CILIUM_OVERLAY"
    result = _cluster_create_validate({"body": body})
    text = result[0].text
    assert "cidr" in text


def test_cluster_create_validate_invalid_network_type():
    """An unknown networkType (e.g. legacy CALICO) is rejected."""
    body = {**_VALID_BODY, "networkType": "CALICO"}
    body.pop("cidr", None)
    result = _cluster_create_validate({"body": body})
    text = result[0].text
    assert "networkType" in text
    assert text != "valid"


def test_cluster_create_validate_missing_enable_private_cluster():
    """Missing enablePrivateCluster is reported."""
    body = {k: v for k, v in _VALID_BODY.items() if k != "enablePrivateCluster"}
    result = _cluster_create_validate({"body": body})
    text = result[0].text
    assert "enablePrivateCluster" in text


def test_cluster_create_validate_bad_disk_size():
    """diskSize out of range returns an error."""
    bad_ng = {**_VALID_NODEGROUP, "diskSize": 10}
    body = {**_VALID_BODY, "nodeGroups": [bad_ng]}
    result = _cluster_create_validate({"body": body})
    text = result[0].text
    assert "diskSize" in text


def test_cluster_create_validate_bad_num_nodes():
    """numNodes out of range returns an error."""
    bad_ng = {**_VALID_NODEGROUP, "numNodes": 15}
    body = {**_VALID_BODY, "nodeGroups": [bad_ng]}
    result = _cluster_create_validate({"body": body})
    text = result[0].text
    assert "numNodes" in text


def test_cluster_create_validate_bad_nodegroup_name():
    """Invalid node group name returns an error."""
    bad_ng = {**_VALID_NODEGROUP, "name": "BAD"}
    body = {**_VALID_BODY, "nodeGroups": [bad_ng]}
    result = _cluster_create_validate({"body": body})
    text = result[0].text
    assert "name" in text.lower()


def test_cluster_create_validate_cilium_native_routing_needs_secondary_subnets():
    """CILIUM_NATIVE_ROUTING without secondarySubnets returns an error."""
    body = {**_VALID_BODY, "networkType": "CILIUM_NATIVE_ROUTING", "nodeGroups": [_VALID_NODEGROUP]}
    body.pop("cidr", None)
    result = _cluster_create_validate({"body": body})
    text = result[0].text
    assert "secondarySubnets" in text
